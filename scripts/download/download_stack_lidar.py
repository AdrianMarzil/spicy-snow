import pickle
import shapely
from glob import glob
import os
from os.path import join, exists
import pandas as pd
import xarray as xr
import rioxarray as rxa

# Add main repo to path
import sys
from os.path import expanduser
sys.path.append(expanduser('../'))

from spicy_snow.retrieval import retrieve_snow_depth

from spicy_snow.download.snowex_lidar import download_dem, download_snow_depth,\
      download_veg_height, make_site_ds

lidar_dir = '/bsuhome/zacharykeskinen/scratch/lidar'
os.makedirs(lidar_dir, exist_ok = True)
download_snow_depth(lidar_dir)
download_veg_height(lidar_dir)
download_dem(lidar_dir)

sites = {'USCOCP': 'Cameron', 'USCOFR': 'Frasier', 'USIDBS': 'Banner', 
         'USIDDC': 'Dry_Creek', 'USIDMC': 'Mores', 'USUTLC': 'Little_Cottonwood'}

# sites = {'USCOFR': 'Frasier', 'USUTLC':'Little_Cottonwood'}

for site, site_name in sites.items():
    print(''.center(40, '-'))
    print(f'Starting {site_name}')

    lidar_ds_site = make_site_ds(site, lidar_dir = lidar_dir)

    lidar_ds_site = lidar_ds_site.where(lidar_ds_site < 1000).where(lidar_ds_site > -1000)

    area = shapely.geometry.box(*lidar_ds_site.rio.bounds())

    for date in lidar_ds_site.time:
        os.makedirs('/bsuhome/zacharykeskinen/scratch/SnowEx-Data/', exist_ok = True)
        out_nc = f'/bsuhome/zacharykeskinen/scratch/SnowEx-Data/{site_name}_{(date).dt.strftime("%Y-%m-%d").values}.nc'

        if exists(out_nc):
            print(f'Outfile {out_nc} exists already.')
            continue

        print(f'Starting {site_name} snow depth @ {date.values}')

        if date.dt.month > 4:
            continue

        lidar_ds = lidar_ds_site.sel(time = date)

        if date.dt.month < 8:
            date1 = pd.to_datetime(f'{int(date.dt.year - 1)}-08-01')
        else:
            date1 = pd.to_datetime(f'{int(date.dt.year)}-08-01')

        dates = (date1.strftime('%Y-%m-%d'), pd.to_datetime((date + pd.Timedelta('14 day')).values).strftime('%Y-%m-%d'))

        spicy_ds = retrieve_snow_depth(area = area, dates = dates, work_dir = '/bsuhome/zacharykeskinen/scratch/data/', job_name = f'spicy_{site}_{dates[1]}', existing_job_name = f'spicy_{site}_{dates[1]}')

        lidar_ds = lidar_ds.rio.reproject_match(spicy_ds)

        ds = xr.merge([spicy_ds, lidar_ds], combine_attrs = 'drop_conflicts')

        # ds = ds[['lidar-sd', 'lidar-vh', 'lidar-dem', 'snow_depth', 's1', 'wet_snow']]

        ds.attrs['site'] = site_name
        ds.attrs['site_abbrev'] = site
        ds.attrs['lidar-flight-time'] = str((date).dt.strftime("%Y-%m-%d").values)
        
        try:
            ds.to_netcdf(out_nc)
        except:
            print('Unable to create netcdf4 for {site_name}')
