"""
Functions to download PROBA-V forest-cover-fraction images for specific geometries
"""
import os
from os.path import exists
import rioxarray as rxa
import xarray as xr
import logging
log = logging.getLogger(__name__)

from spicy_snow.utils.download import url_download

def download_fcf(dataset: xr.Dataset, out_fp: str) -> xr.Dataset:
    """
    Download PROBA-V forest-cover-fraction images (with caching).

    If out_fp already exists, reuse it instead of downloading again.
    """
    log.debug("Downloading Forest Cover")

    # URL from Lievens et al. 2021 paper
    fcf_url = "https://zenodo.org/record/3939050/files/PROBAV_LC100_global_v3.0.1_2019-nrt_Tree-CoverFraction-layer_EPSG-4326.tif"

    # Ensure parent directory exists
    os.makedirs(os.path.dirname(out_fp) or ".", exist_ok=True)

    # ✅ Cache: reuse existing file if present
    if exists(out_fp) and os.path.getsize(out_fp) > 0:
        log.info(f"FCF already exists; reusing cached file: {out_fp}")
    else:
        log.info(f"Downloading FCF to: {out_fp}")
        url_download(fcf_url, out_fp)

    # open as dataArray
    fcf = rxa.open_rasterio(out_fp)

    # reproject FCF and clip to match dataset
    log.debug(f"Clipping FCF to {dataset['s1'].rio.bounds()}")
    fcf = fcf.rio.clip_box(*dataset["s1"].rio.bounds())
    fcf = fcf.rio.reproject_match(dataset["s1"])
    fcf = fcf.squeeze("band")

    # normalize if needed
    if fcf.max() >= 1:
        log.debug("fcf max > 1 so dividing by 100")
        fcf = fcf / 100
        log.debug(f"New fcf max is {fcf.max()} and min is {fcf.min()}")

    assert fcf.max() <= 1, "Forest cover fraction must be bounded 0-1"
    assert fcf.min() >= 0, "Forest cover fraction must be bounded 0-1"

    log.debug(f"FCF min: {fcf.min()}")
    log.debug(f"FCF max: {fcf.max()}")
    log.debug(f"FCF mean: {fcf.mean()}")

    # merge FCF and name it 'fcf' as a data variable
    dataset = xr.merge([dataset, fcf.rename("fcf")])

    return dataset

# End of file