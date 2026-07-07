#!/usr/bin/env python3

import os
import re
import glob
import numpy as np
import pandas as pd
import rasterio
import geopandas as gpd
from shapely.geometry import box

from scipy.ndimage import distance_transform_edt
from rasterio.features import rasterize
from collections import defaultdict

import pyarrow as pa
import pyarrow.parquet as pq


# ---------------------------------------------------
# CONFIG
# ---------------------------------------------------

RASTER_DIR = "/mnt/shared/hydrography90m_v.1.0_online/hydrography90m_v.1.0/r.watershed/sub_catchment_tiles20d/"
#RASTER_DIR = "/data/mschuerz/clustering_global/test"
COUNTRIES_SHP = "/data/mschuerz/clustering_global/geoBoundariesCGAZ_ADM0_wgs84.gpkg"
REGIONS_CSV = "/data/mschuerz/clustering_global/regions_20260603.csv"
OUTPUT_DIR = "/data/mschuerz/clustering_global/sub_catchment_country_parquet"

BLOCKSIZE = 1024

START_TILE = "h12v02"

# ---------------------------------------------------
# HELPERS
# ---------------------------------------------------

def extract_tile_id(path):
    """Extract hXXvYY from filename"""
    m = re.search(r"(h\d{2}v\d{2})", path)
    return m.group(1) if m else "unknown"


# ---------------------------------------------------
# LOAD STATIC TABLES
# ---------------------------------------------------

print("Loading countries...")

countries = gpd.read_file(COUNTRIES_SHP)

if countries.crs is None:
    raise ValueError("Countries CRS is undefined!")

countries = countries.to_crs("EPSG:4326")

# Fix invalid geometries
print("Checking geometry validity...")

invalid = ~countries.geometry.is_valid
n_invalid = invalid.sum()

print(f"Found {n_invalid} invalid geometries")

if n_invalid > 0:
    countries.loc[invalid, "geometry"] = (
        countries.loc[invalid, "geometry"]
        .make_valid()
    )

    # optional second pass
    invalid2 = ~countries.geometry.is_valid

    if invalid2.any():
        countries.loc[invalid2, "geometry"] = (
            countries.loc[invalid2, "geometry"]
            .buffer(0)
        )

    print(
        f"Remaining invalid geometries: "
        f"{(~countries.geometry.is_valid).sum()}"
    )

# ensure required columns exist
required = {"shapeGroup", "shapeName"}
missing = required - set(countries.columns)
if missing:
    raise ValueError(f"Missing columns in countries: {missing}")

countries["country_id"] = np.arange(1, len(countries) + 1)


print("Loading regions...")

regions = pd.read_csv(REGIONS_CSV)

if "shapeGroup" not in regions.columns:
    raise ValueError("regions.csv must contain shapeGroup column")


# ---------------------------------------------------
# PROCESS EACH TILE
# ---------------------------------------------------

tiles = sorted(glob.glob(os.path.join(RASTER_DIR, "*.tif")))

if START_TILE:
    found = False
    filtered = []

    for t in tiles:
        tid = extract_tile_id(t)

        if tid == START_TILE:
            found = True

        if found:
            filtered.append(t)

    tiles = filtered

os.makedirs(OUTPUT_DIR, exist_ok=True)


for tile_path in tiles:

    tile_id = extract_tile_id(tile_path)
    print(f"\nProcessing tile {tile_id}")

    with rasterio.open(tile_path) as src:

        transform = src.transform

        # ------------------------------------------------
        # CLIP COUNTRIES TO TILE
        # ------------------------------------------------

        bounds = src.bounds

        bbox_geom = box(bounds.left, bounds.bottom, bounds.right, bounds.top)

        countries_tile = gpd.clip(countries, bbox_geom)

        if len(countries_tile) == 0:
            print("No countries in tile")
            continue

        # ------------------------------------------------
        # RASTERIZE COUNTRIES
        # ------------------------------------------------

        country_raster = rasterize(
            ((geom, cid) for geom, cid in zip(
                countries_tile.geometry,
                countries_tile.country_id
            )),
            out_shape=(src.height, src.width),
            transform=transform,
            fill=0,
            dtype=np.int32
        )

        # ------------------------------------------------
        # FILL COASTLINE GAPS (nearest country)
        # ------------------------------------------------

        mask = country_raster == 0

        if np.any(mask):
            _, inds = distance_transform_edt(
                mask,
                return_distances=True,
                return_indices=True
            )

            country_raster = country_raster[inds[0], inds[1]]

        # ------------------------------------------------
        # ACCUMULATE PIXEL COUNTS
        # ------------------------------------------------

        accum = defaultdict(int)

        for _, window in src.block_windows(1):

            subc = src.read(1, window=window)
            crow = country_raster[
                window.row_off:window.row_off + window.height,
                window.col_off:window.col_off + window.width
            ]

            valid = subc > 0

            if not np.any(valid):
                continue

            pairs = np.column_stack([
                subc[valid].astype(np.int64),
                crow[valid].astype(np.int32)
            ])

            unique, counts = np.unique(pairs, axis=0, return_counts=True)

            for (sid, cid), cnt in zip(unique, counts):
                accum[(sid, cid)] += int(cnt)

        # ------------------------------------------------
        # BUILD TABLE
        # ------------------------------------------------

        if not accum:
            continue

        df = pd.DataFrame(
            [(sid, cid, cnt) for (sid, cid), cnt in accum.items()],
            columns=["subc_id", "country_id", "pixel_count"]
        )

        # attach country metadata
        df = df.merge(
            countries_tile[["country_id", "shapeGroup", "shapeName"]],
            on="country_id",
            how="left"
        )

        # attach region metadata
        df = df.merge(
            regions,
            on="shapeGroup",
            how="left"
        )

        # add tile id
        df["tile"] = tile_id

        # ------------------------------------------------
        # WRITE PARQUET (partitioned by tile)
        # ------------------------------------------------

        out_path = os.path.join(
            OUTPUT_DIR,
            f"{tile_id}.parquet"
        )

        table = pa.Table.from_pandas(df)

        pq.write_table(
            table,
            out_path,
            compression="snappy"
        )

        print(f"Wrote {len(df)} rows -> {out_path}")


print("\nDone.")
