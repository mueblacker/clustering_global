# =========================================================================
# Assign countries to Hydrography90m sub-catchments
#
# For each sub-catchment raster tile, this script overlays country boundaries
# and counts how many raster pixels of each sub-catchment fall within each
# country. Results are written as Parquet files partitioned by raster tile.
# =========================================================================

#!/usr/bin/env python3

# Modules ------------------------------------------------------------------

# Standard Python modules for file handling, regular expressions, and
# dictionary-based accumulation of pixel counts.
import os
import re
import glob
from collections import defaultdict

# Libraries for numerical arrays and tabular data.
import numpy as np
import pandas as pd

# Libraries for reading raster data and rasterizing vector geometries.
import rasterio
from rasterio.features import rasterize

# Libraries for reading and processing country boundary geometries.
import geopandas as gpd
from shapely.geometry import box

# Used to fill raster cells outside country polygons with the nearest country.
from scipy.ndimage import distance_transform_edt

# Libraries for writing output data in Parquet format.
import pyarrow as pa
import pyarrow.parquet as pq


# Define directories -------------------------------------------------------

# Directory containing Hydrography90m sub-catchment raster tiles.
RASTER_DIR = "/my_directory/data/hydrography90m_v.1.0/r.watershed/sub_catchment_tiles20d/"
# GeoPackage containing country boundaries.
COUNTRIES_SHP = "/my_directory/data/clustering_global/geoBoundariesCGAZ_ADM0_wgs84.gpkg"
# CSV file containing country-to-region and sub-region assignments.
REGIONS_CSV = "/my_directory/data/clustering_global/regions_20260603.csv"
# Directory where one Parquet output file per tile will be written.
OUTPUT_DIR = "/my_directory/data/clustering_global/sub_catchment_country_parquet"

# Settings ------------------------------------------------------------------
# Raster block size setting
# block sizes are obtained from each raster using `src.block_windows(1)`
# BLOCKSIZE = 1024

# Optional tile ID from which processing should begin.
# Set to `None` or an empty string to process all tiles from the beginning
START_TILE = "h12v02"

# Helper function ------------------------------------------------------------

def extract_tile_id(path):
    """Extract hXXvYY from filename"""
    # Search the path for a string such as "h12v02".
    m = re.search(r"(h\d{2}v\d{2})", path)
    # Return the matched tile ID, or "unknown" if no match is found.
    return m.group(1) if m else "unknown"

# Load countries ------------------------------------------------------------

# Load country boundaries once before processing raster tiles.
print("Loading countries...")

countries = gpd.read_file(COUNTRIES_SHP)

# Country geometries must use the same coordinate reference system as the
# raster tiles. This script expects geographic WGS84 coordinates.
if countries.crs is None:
    raise ValueError("Countries CRS is undefined!")

countries = countries.to_crs("EPSG:4326")


# Check for invalid polygon geometries and attempt to repair them.
# Invalid geometries can cause clipping and rasterization problems.
print("Checking geometry validity...")

invalid = ~countries.geometry.is_valid
n_invalid = invalid.sum()

print(f"Found {n_invalid} invalid geometries")

if n_invalid > 0:
    
    # First attempt to repair invalid geometries using GeoPandas/Shapely's
    # `make_valid()` method.
    countries.loc[invalid, "geometry"] = (
        countries.loc[invalid, "geometry"]
        .make_valid()
    )

    # Check again after geometry repair.
    invalid2 = ~countries.geometry.is_valid

    # If any invalid geometries remain, use a zero-width buffer as another
    # geometry-repair attempt.
    if invalid2.any():
        countries.loc[invalid2, "geometry"] = (
            countries.loc[invalid2, "geometry"]
            .buffer(0)
        )

    # Print the number of geometries that remain invalid after repair attempts.
    print(
        f"Remaining invalid geometries: "
        f"{(~countries.geometry.is_valid).sum()}"
    )

# Confirm that the country-boundary file contains required identifier fields.
required = {"shapeGroup", "shapeName"}
missing = required - set(countries.columns)

if missing:
    raise ValueError(f"Missing columns in countries: {missing}")

# Create a numeric country identifier used during rasterization.
# IDs start at 1 because 0 is reserved as the background/no-country value.
countries["country_id"] = np.arange(1, len(countries) + 1)


# Load the table linking country identifiers to UN regions and sub-regions.
print("Loading regions...")

regions = pd.read_csv(REGIONS_CSV)

# Confirm that the join key used to attach regional metadata is available.
if "shapeGroup" not in regions.columns:
    raise ValueError("regions.csv must contain shapeGroup column")


# Process each tile ------------------------------------------------------------

# Find and sort all GeoTIFF sub-catchment raster tiles.
tiles = sorted(glob.glob(os.path.join(RASTER_DIR, "*.tif")))

# If a start tile is specified, discard all earlier tiles and begin processing
# from the first tile matching `START_TILE`.
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

# Create the output directory if it does not already exist.
os.makedirs(OUTPUT_DIR, exist_ok=True)


# Process each raster tile separately.
for tile_path in tiles:

    # Extract the tile name, for example "h12v02".
    tile_id = extract_tile_id(tile_path)
    
    print(f"\nProcessing tile {tile_id}")

    # Open the raster tile. The file is automatically closed after this block.
    with rasterio.open(tile_path) as src:

        # Store the raster geospatial transform, needed to rasterize country
        # polygons onto the same grid as the sub-catchment raster.
        transform = src.transform

        # ------------------------------------------------
        # CLIP COUNTRIES TO TILE
        # ------------------------------------------------

        # Get the geographic extent of the current raster tile.
        bounds = src.bounds

        # Create a rectangular polygon representing the tile extent.
        bbox_geom = box(bounds.left, bounds.bottom, bounds.right, bounds.top)

        # Keep only country geometries that intersect the current tile.
        countries_tile = gpd.clip(countries, bbox_geom)

        # Skip the tile if no country boundaries overlap it.
        if len(countries_tile) == 0:
            print("No countries in tile")
            continue

        # ------------------------------------------------
        # RASTERIZE COUNTRIES
        # ------------------------------------------------

        # Convert clipped country polygons to a raster aligned with the
        # sub-catchment raster.
        #
        # Each country polygon is assigned its numeric `country_id`.
        # Cells outside country polygons initially receive a value of 0.
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

        # Identify raster cells that were not assigned to a country.
        # This can occur in ocean areas, boundary gaps, or minor geometry gaps.
        mask = country_raster == 0

        if np.any(mask):
            
            # For every unassigned cell, find the indices of the nearest
            # assigned country cell.
            _, inds = distance_transform_edt(
                mask,
                return_distances=True,
                return_indices=True
            )

            # Fill unassigned cells with the country ID of the nearest
            # country-assigned raster cell.
            country_raster = country_raster[inds[0], inds[1]]

        # ------------------------------------------------
        # ACCUMULATE PIXEL COUNTS
        # ------------------------------------------------

        # Create a dictionary for counting pixels by:
        # (sub-catchment ID, country ID).
        accum = defaultdict(int)

        # Process the raster in its internal block/windows rather than loading
        # the complete sub-catchment raster band into memory at once.
        for _, window in src.block_windows(1):

            # Read sub-catchment IDs for the current raster block.
            subc = src.read(1, window=window)

            # Extract matching country IDs from the rasterized country array.
            crow = country_raster[
                window.row_off:window.row_off + window.height,
                window.col_off:window.col_off + window.width
            ]

            # Keep only valid sub-catchment cells.
            # Values of 0 or below are treated as background/no-data.
            valid = subc > 0

            if not np.any(valid):
                continue

            # Create pairs of sub-catchment IDs and country IDs for valid cells.
            pairs = np.column_stack([
                subc[valid].astype(np.int64),
                crow[valid].astype(np.int32)
            ])

            # Count unique sub-catchment/country combinations in this block.
            unique, counts = np.unique(pairs, axis=0, return_counts=True)

            # Add block-level counts to the total count dictionary for the tile.
            for (sid, cid), cnt in zip(unique, counts):
                accum[(sid, cid)] += int(cnt)

        # ------------------------------------------------
        # BUILD TABLE
        # ------------------------------------------------

        # Skip the tile if no valid sub-catchment/country pixel combinations
        # were found.
        if not accum:
            continue

        # Convert accumulated counts into a Pandas DataFrame.
        # Each row represents the number of pixels of one sub-catchment
        # associated with one country in this tile.
        df = pd.DataFrame(
            [(sid, cid, cnt) for (sid, cid), cnt in accum.items()],
            columns=["subc_id", "country_id", "pixel_count"]
        )

        # Add country identifiers and names to each sub-catchment/country pair.
        df = df.merge(
            countries_tile[["country_id", "shapeGroup", "shapeName"]],
            on="country_id",
            how="left"
        )

        # Add regional and sub-regional metadata using the country shape group.
        df = df.merge(
            regions,
            on="shapeGroup",
            how="left"
        )

        # Store the raster tile ID for traceability.
        df["tile"] = tile_id

        # ------------------------------------------------
        # WRITE PARQUET (partitioned by tile)
        # ------------------------------------------------

        # Define the output filename for this tile.
        out_path = os.path.join(
            OUTPUT_DIR,
            f"{tile_id}.parquet"
        )

        # Convert the Pandas DataFrame to an Arrow table.
        table = pa.Table.from_pandas(df)

        # Write the tile-level table to Parquet using Snappy compression.
        pq.write_table(
            table,
            out_path,
            compression="snappy"
        )

        print(f"Wrote {len(df)} rows -> {out_path}")


# Print a completion message after all selected tiles have been processed.
print("\nDone.")