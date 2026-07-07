#!/usr/bin/env python3
"""
Calculate categorical raster proportions per continent.

Workflow:
1. Read categorical raster
2. Reproject raster to EPSG:54009 (World Mollweide)
3. Download/load Natural Earth Admin-0 countries
4. Dissolve countries into continents
5. Reproject continents to EPSG:54009
6. Rasterize continents to raster grid
7. Calculate category counts + proportions per continent

Outputs:
- reprojected raster
- dissolved continent shapefile
- continent raster
- CSV with counts
- CSV with proportions

Required packages:
pip install geopandas rasterio rasterstats numpy pandas shapely pyproj requests
"""

from pathlib import Path
import zipfile
import requests
import numpy as np
import pandas as pd
import geopandas as gpd

import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.features import rasterize

# -----------------------------------------------------------------------------
# USER SETTINGS
# -----------------------------------------------------------------------------

INPUT_RASTER = "/data/mschuerz/clustering_global/world_v2/world_clusters30.tif"

OUTPUT_DIR = Path("/data/mschuerz/clustering_global/world_v2/continent_statistic")
OUTPUT_DIR.mkdir(exist_ok=True)

TARGET_CRS = "ESRI:54009"  # World Mollweide

# Natural Earth countries
NE_URL = (
    "https://naciscdn.org/naturalearth/50m/cultural/"
    "ne_50m_admin_0_countries.zip"
)

# -----------------------------------------------------------------------------
# OUTPUT FILES
# -----------------------------------------------------------------------------

REPROJECTED_RASTER = OUTPUT_DIR / "raster_54009.tif"
COUNTRIES_ZIP = OUTPUT_DIR / "naturalearth_countries.zip"
COUNTRIES_DIR = OUTPUT_DIR / "naturalearth"

CONTINENTS_GPKG = OUTPUT_DIR / "continents_54009.gpkg"
CONTINENT_RASTER = OUTPUT_DIR / "continents_rasterized.tif"

COUNTS_CSV = OUTPUT_DIR / "continent_category_counts.csv"
PROPORTIONS_CSV = OUTPUT_DIR / "continent_category_proportions.csv"

# -----------------------------------------------------------------------------
# DOWNLOAD NATURAL EARTH
# -----------------------------------------------------------------------------

print("Downloading Natural Earth countries...")

r = requests.get(NE_URL)
r.raise_for_status()

with open(COUNTRIES_ZIP, "wb") as f:
    f.write(r.content)

COUNTRIES_DIR.mkdir(exist_ok=True)

with zipfile.ZipFile(COUNTRIES_ZIP, "r") as zip_ref:
    zip_ref.extractall(COUNTRIES_DIR)

# Find shapefile
shp_files = list(COUNTRIES_DIR.glob("*.shp"))
if not shp_files:
    raise FileNotFoundError("No shapefile found in Natural Earth archive.")

COUNTRIES_SHP = shp_files[0]

# -----------------------------------------------------------------------------
# LOAD + DISSOLVE CONTINENTS
# -----------------------------------------------------------------------------

print("Loading Natural Earth data...")

countries = gpd.read_file(COUNTRIES_SHP)

# Remove Antarctica if desired
countries = countries[countries["CONTINENT"] != "Antarctica"]

print("Dissolving countries into continents...")

# Dissolve countries into continents
continents = countries.dissolve(by="CONTINENT", as_index=False)

# Reproject
continents = continents.to_crs(TARGET_CRS)

# Keep only needed columns
continents = continents[["CONTINENT", "geometry"]].copy()

# Force standard Python string dtype
continents["CONTINENT"] = continents["CONTINENT"].astype(str)

# Rebuild GeoDataFrame completely
continents = gpd.GeoDataFrame(
    continents,
    geometry="geometry",
    crs=TARGET_CRS
)

# Save as GeoPackage (recommended)
#CONTINENTS_FILE = OUTPUT_DIR / "continents_54009.gpkg"

#continents.to_file(
#    CONTINENTS_FILE,
#    driver="GPKG"
#)

#print(f"Saved continents shapefile: {CONTINENTS_SHP}")

# -----------------------------------------------------------------------------
# REPROJECT RASTER
# -----------------------------------------------------------------------------

print("Reprojecting raster...")

with rasterio.open(INPUT_RASTER) as src:

    transform, width, height = calculate_default_transform(
        src.crs,
        TARGET_CRS,
        src.width,
        src.height,
        *src.bounds
    )

    kwargs = src.meta.copy()
    kwargs.update({
        "crs": TARGET_CRS,
        "transform": transform,
        "width": width,
        "height": height,
        "compress": "lzw"
    })

    with rasterio.open(REPROJECTED_RASTER, "w", **kwargs) as dst:

        for i in range(1, src.count + 1):
            reproject(
                source=rasterio.band(src, i),
                destination=rasterio.band(dst, i),
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=transform,
                dst_crs=TARGET_CRS,
                resampling=Resampling.nearest  # IMPORTANT for categorical rasters
            )

print(f"Saved reprojected raster: {REPROJECTED_RASTER}")

# -----------------------------------------------------------------------------
# RASTERIZE CONTINENTS
# -----------------------------------------------------------------------------

print("Rasterizing continents...")

with rasterio.open(REPROJECTED_RASTER) as src:

    raster_meta = src.meta.copy()

    # Assign integer IDs to continents
    continents["continent_id"] = range(1, len(continents) + 1)

    continent_lookup = dict(
        zip(continents["continent_id"], continents["CONTINENT"])
    )

    shapes = [
        (geom, value)
        for geom, value in zip(
            continents.geometry,
            continents["continent_id"]
        )
    ]

    continent_arr = rasterize(
        shapes=shapes,
        out_shape=(src.height, src.width),
        transform=src.transform,
        fill=0,
        dtype="uint8"
    )

    raster_meta.update({
        "count": 1,
        "dtype": "uint8",
        "nodata": 0
    })

    with rasterio.open(CONTINENT_RASTER, "w", **raster_meta) as dst:
        dst.write(continent_arr, 1)

print(f"Saved rasterized continents: {CONTINENT_RASTER}")

# -----------------------------------------------------------------------------
# CALCULATE CATEGORY PROPORTIONS
# -----------------------------------------------------------------------------

print("Calculating category statistics...")

with rasterio.open(REPROJECTED_RASTER) as cat_src, \
     rasterio.open(CONTINENT_RASTER) as cont_src:

    cat = cat_src.read(1)
    cont = cont_src.read(1)

    nodata = cat_src.nodata

    if nodata is not None:
        valid_mask = cat != nodata
    else:
        valid_mask = np.ones(cat.shape, dtype=bool)

    results = []

    for cont_id, cont_name in continent_lookup.items():

        mask = (cont == cont_id) & valid_mask

        values = cat[mask]

        unique, counts = np.unique(values, return_counts=True)

        total = counts.sum()

        for val, cnt in zip(unique, counts):

            prop = cnt / total if total > 0 else np.nan

            results.append({
                "continent": cont_name,
                "category": int(val),
                "count": int(cnt),
                "proportion": prop
            })

df = pd.DataFrame(results)

# Save counts
df[["continent", "category", "count"]].to_csv(
    COUNTS_CSV,
    index=False
)

# Save proportions
df[["continent", "category", "proportion"]].to_csv(
    PROPORTIONS_CSV,
    index=False
)

print("\nDONE")
print(f"Counts:       {COUNTS_CSV}")
print(f"Proportions:  {PROPORTIONS_CSV}")