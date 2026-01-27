# Script to create a merged Cloud optimized GeoTiff
# with random colors

# Load packages --------------------------------------------------

import os
import glob
import random
import numpy as np
import rasterio
from rasterio.merge import merge
from rasterio.enums import Resampling
from rasterio.shutil import copy as rio_copy


# Settings ---------------------------------------------------------

# Define directories
input_dir = "/data/mschuerz/clustering_global/south_america_wo_flo1k/cluster_rasters"    
output_cog = "/data/mschuerz/clustering_global/south_america_wo_flo1k/south_america_clusters24_cog.tif" 
tmp_tif = "/data/mschuerz/clustering_global/south_america_wo_flo1k/tmp_merged.tif"

# Output settings
compression = "ZSTD"                     # lossless compression
overview_levels = [2, 4, 8, 16, 32]      # overview downsampling factors
nodata_value = 0                         # set nodata
block_size = 512                         # tile size for COG

# Define random colors
def random_color():
    """Generate a random RGBA color"""
    return (
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255),
        255
    )

# Read, merge and convert raster files -------------------------------

# Find all .tif files in input_dir
tif_files = sorted(glob.glob(os.path.join(input_dir, "*.tif")))
if not tif_files:
    raise RuntimeError("No .tif files found in input directory!")

# Open all datasets
datasets = [rasterio.open(fp) for fp in tif_files]

# Merge rasters
mosaic, transform = merge(datasets, nodata=nodata_value)

# Update metadata from the first file
meta = datasets[0].meta.copy()
meta.update({
    "driver": "GTiff",
    "height": mosaic.shape[1],
    "width": mosaic.shape[2],
    "transform": transform,
    "count": 1,
    "nodata": nodata_value,
    "tiled": True,
    "blockxsize": block_size,
    "blockysize": block_size,
    "compress": compression,
    "predictor": 1,  # for categorical data
    "BIGTIFF": "IF_SAFER"
})

tmp_tif = "tmp_merged.tif"

# Write the merged raster to a temporary file
with rasterio.open(tmp_tif, "w", **meta) as dst:
    dst.write(mosaic[0], 1)

    # Color Table 
    unique_classes = np.unique(mosaic)
    unique_classes = [int(c) for c in unique_classes if c != nodata_value]

    # Assign random colors to each class
    colormap = {val: random_color() for val in unique_classes}
    colormap[nodata_value] = (0, 0, 0, 0)  # transparent nodata

    dst.write_colormap(1, colormap)

    # Overviews
    dst.build_overviews(overview_levels, Resampling.nearest)
    dst.update_tags(ns="rio_overview", resampling="nearest")

# Convert to Cloud Optimized GeoTIFF
rio_copy(
    tmp_tif,
    output_cog,
    driver="COG",
    compress=compression,
    overview_resampling="nearest",
    blocksize=block_size
)

# Cleanup temporary file
os.remove(tmp_tif)

# Close input datasets
for ds in datasets:
    ds.close()

print(f"Cloud Optimized GeoTIFF created: {output_cog}")