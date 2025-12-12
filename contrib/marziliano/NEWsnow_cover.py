"""
Functions to download IMS snow-coverage images.

https://usicecenter.gov/Products/ImsHome
https://nsidc.org/data/user-resources/help-center/how-access-data-using-ftp-client-command-line-wget-or-python
"""

import os
import shutil
import time
import gzip
import urllib.request
from pathlib import Path
from tqdm import tqdm
import pandas as pd
import xarray as xr
import rioxarray as rxa

import logging
log = logging.getLogger(__name__)

# Keep existing imports in case other parts of the package expect them
from spicy_snow.utils.download import url_download  # noqa: F401


def _decompress_gz_streaming(infile: str | os.PathLike, tofile: str | os.PathLike,
                             chunk_size: int = 1024 * 1024, retries: int = 8) -> str:
    """
    Windows-friendly gzip decompression:
    - Streams instead of reading entire file into memory
    - Deletes existing output file first (avoids overwrite/lock issues)
    - Retries if Windows briefly locks the file (Defender/indexer/etc.)
    """
    infile_p = Path(infile)
    tofile_p = Path(tofile)

    tofile_p.parent.mkdir(parents=True, exist_ok=True)

    # If output already exists from a prior run, remove it first
    if tofile_p.exists():
        for _ in range(retries):
            try:
                tofile_p.unlink()
                break
            except PermissionError:
                time.sleep(1)
        else:
            raise PermissionError(f"Could not remove existing IMS output file: {tofile_p}")

    # Stream decompress with retries
    last_err = None
    for _ in range(retries):
        try:
            with gzip.open(infile_p, "rb") as inf, open(tofile_p, "wb") as ouf:
                while True:
                    chunk = inf.read(chunk_size)
                    if not chunk:
                        break
                    ouf.write(chunk)
            return str(tofile_p)
        except PermissionError as e:
            last_err = e
            time.sleep(1)

    raise PermissionError(f"Permission denied writing IMS output file: {tofile_p}") from last_err


def get_ims_day_data(year: str, doy: str, tmp_dir: str) -> xr.DataArray:
    """
    Download and decompress one day's worth of IMS data.

    Args:
        year: Year of the data you want (e.g., "2023" or 2023).
        doy: Calendar day of year in 'DDD' format. Range is 001 - 366.
        tmp_dir: Directory to store temporary downloads.
    """
    tmp_dir_p = Path(tmp_dir)
    tmp_dir_p.mkdir(parents=True, exist_ok=True)

    # If we haven't found a file that works add one more to day and try again
    local_fp = None
    while not local_fp:
        try:
            gz_name = f"ims{int(year)}{doy}_1km_v1.3.nc.gz"
            url = f"ftp://sidads.colorado.edu/pub/DATASETS/NOAA/G02156/netcdf/1km/{int(year)}/{gz_name}"
            gz_path = tmp_dir_p / gz_name

            # Download directly into tmp_dir (no chdir)
            local_fp, _ = urllib.request.urlretrieve(url, str(gz_path))
        except Exception:
            # Try next DOY if missing
            doy = f"{int(doy) + 1:03}"

    # Decompress .gz -> .nc (streaming + overwrite-safe)
    out_nc = str(Path(local_fp).with_suffix(""))  # removes the trailing ".gz"
    out_file = _decompress_gz_streaming(local_fp, out_nc)

    # Open as xarray DataArray
    ims = rxa.open_rasterio(out_file, decode_times=False)
    return ims


def download_snow_cover(dataset: xr.Dataset, tmp_dir: str = "./tmp", clean: bool = True) -> xr.Dataset:
    """
    Download IMS snow-cover images and add them to the dataset.

    Args:
        dataset: Full dataset to add IMS data to
        tmp_dir: filepath to save temporary downloads to [default: './tmp']
        clean: Remove temporary directory after download?

    Returns:
        Updated dataset with IMS DataArray merged in as 'ims'
    """
    # get list of days that we have Sentinel-1 data for
    days = [pd.to_datetime(d) for d in dataset.time.values]

    all_ims = []
    for day in tqdm(days, desc="Downloading IMS snow-cover"):
        ims = get_ims_day_data(str(day.year), f"{day.dayofyear:03}", tmp_dir=tmp_dir)

        # add timestamp info
        ims = ims.assign_coords(time=[day])

        # reproject and clip to match dataset
        ims = ims.rio.reproject_match(dataset["s1"])

        all_ims.append(ims)

    full_ims = xr.concat(all_ims, dim="time")
    dataset = xr.merge([dataset, full_ims.rename("ims")])

    if clean is True:
        # Best effort cleanup (Windows can sometimes keep handles briefly)
        try:
            shutil.rmtree(tmp_dir)
        except PermissionError:
            pass

    return dataset

# End of file
