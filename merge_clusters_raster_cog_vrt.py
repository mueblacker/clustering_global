# Script to generate a Cloud optimized GeoTiff
# Merge and create a VRT

# Load packages --------------------------------------------------

import os
import glob
import random
import numpy as np
import rasterio
from osgeo import gdal
from rasterio.enums import ColorInterp

# Settings -------------------------------------------------------

# Define directories
input_dir = "/data/mschuerz/clustering_global/world_v2/cluster_rasters"   
output_cog = "/data/mschuerz/clustering_global/world_v2/world_clusters30_cog.tif"
tmp_vrt = "/data/mschuerz/clustering_global/world_v2/merged.vrt"

# Define output settings 
compression = "ZSTD" 
block_size = 512
overview_levels = [2, 4, 8, 16, 32]
nodata_value = 0


# Collect input files ----------------------------------------------
tif_files = sorted(glob.glob(os.path.join(input_dir, "*.tif")))
if not tif_files:
    raise RuntimeError("No .tif files found in input directory!")

# Build VRT --------------------------------------------------------

print("Building VRT...")

vrt_options = gdal.BuildVRTOptions(
    resolution="average",
    separate=False,
    VRTNodata=nodata_value
)
gdal.BuildVRT(tmp_vrt, tif_files, options=vrt_options)

# Convert VRT to Cloud Optimized GeoTIFF (COG) with uint8 ----------

print("Creating Cloud Optimized GeoTIFF (uint8)...")

translate_options = gdal.TranslateOptions(
    format="COG",
    outputType=gdal.GDT_Byte,  # Convert to uint8 
    creationOptions=[
        f"COMPRESS={compression}",
        "BIGTIFF=IF_SAFER",  # For larger datasets
    ],
    noData=nodata_value
)

gdal.Translate(
    destName=output_cog,
    srcDS=tmp_vrt,
    options=translate_options
)

# Add color table ----------------------------------------------------

print("Adding color table...")

def consistent_color(val):
    # Generate consistent random RGB color for each unique value
    rnd = random.Random(val)
    return (rnd.randint(0, 255), rnd.randint(0, 255), rnd.randint(0, 255), 255)

# Open the output COG and add a color table
with rasterio.open(output_cog, "r+") as ds:
    band = ds.read(1)
    
    # Find unique values in the merged raster (ignore nodata)
    unique_values = np.unique(band)
    unique_values = unique_values[unique_values != nodata_value]  # Exclude nodata value
    
    # Create color table (mapping unique values to random RGB colors)
    ct = rasterio.enums.ColorTable()
    for val in unique_values:  # Create a color for each unique value
        ct[val] = consistent_color(val)
    ct[nodata_value] = (0, 0, 0, 0)  # Transparent nodata
    
    # Set the color table
    ds.set_colormap(1, ct)
    ds.nodata = nodata_value
    ds.colorinterp = [ColorInterp.paletted]

#  Build overviews ---------------------------------------------------

print("Building overviews...")

with rasterio.open(output_cog, "r+") as ds:
    ds.build_overviews(overview_levels, resampling=rasterio.enums.Resampling.nearest)

# Cleanup temporary VRT file
os.remove(tmp_vrt)

print(f"Cloud Optimized GeoTIFF created: {output_cog}")
