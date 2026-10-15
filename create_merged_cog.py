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
import colorsys

gdal.UseExceptions()

# Settings -------------------------------------------------------

input_dir = "/data/mschuerz/clustering_global/world_v2/cluster_rasters_HydroLAKES/"
output_cog = "/data/mschuerz/clustering_global/world_v2/lfhc_30k_20260921.tif"

tmp_vrt = "/data/mschuerz/tmp_merged.vrt"
tmp_tif = "/data/mschuerz/tmp_uint8.tif"

compression = "ZSTD"
block_size = 512
nodata_value = 0

# ----------------------------------------------------------------

#def consistent_color(val):
#    rnd = random.Random(int(val))
#    return (rnd.randint(0, 255),
#            rnd.randint(0, 255),
#            rnd.randint(0, 255),
#            255)

#def consistent_color(val, n=30):
#    h = (val % n) / n
#    r, g, b = colorsys.hsv_to_rgb(h, 0.7, 0.9)
#    return (int(r*255), int(g*255), int(b*255), 255)

COLORS = {
    1:  (102, 166,  30, 255),   # Natural vegetation & cropland
    2:  (166, 216,  84, 255),   # Natural vegetation & cropland
    3:  (222, 204, 170, 255),   # Bare area
    4:  (184, 217,  90, 255),   # Grassland
    5:  (136, 183, 252, 255),   # Annual streamflow
    6:  (  0, 109,  44, 255),   # Tree broadleaf evergreen
    7:  (201, 180,  88, 255),   # Sparse vegetation
    8:  ( 35, 139,  69, 255),   # Tree mixed leaf
    9:  (247, 220,  72, 255),   # Cropland irrigated
    10: (  0,  79,  90, 255),   # Precipitation driest month + evergreen
    11: (234, 244, 244, 255),   # Snow and ice
    12: ( 45, 130, 214, 255),   # Stream power & flow accumulation
    13: ( 47, 143, 131, 255),   # Tree flooded freshwater
    14: (245, 169,  76, 255),   # Bare area + precipitation seasonality
    15: (139,  90,  43, 255),   # Elevation
    16: (  0,  68,  27, 255),   # Tree needle evergreen
    17: (141, 170,  91, 255),   # Shrubland - muted green
    18: (255, 193,   7, 255),   # Cropland rainfed
    19: ( 77, 175,  74, 255),   # Tree broadleaf deciduous
    20: (169, 196, 108, 255),   # Grassland
    21: (139, 195,  74, 255),   # Cropland + natural vegetation
    22: (140, 140,  90, 255),   # Lichens & mosses
    23: ( 34, 199, 214, 255),   # Annual precipitation
    24: ( 82, 183, 136, 255),   # Shrub/herb flooded
    25: (  1,  68, 133, 255),   # Water bodies
    26: ( 63, 138, 252, 255),   # Flow accumulation
    27: ( 81,  45, 168, 255),   # Stream gradient
    28: (181, 201, 122, 255),   # Mosaic crop + natural vegetation
    29: ( 27,  94,  32, 255),   # Tree needle deciduous
    30: (104, 159,  56, 255),   # Tree/shrub/herb
}



def consistent_color(class_id):
    return COLORS.get(class_id, (0, 0, 0, 255))  # fallback = black

# Collect input files
tif_files = sorted(glob.glob(os.path.join(input_dir, "*.tif")))
if not tif_files:
    raise RuntimeError("No .tif files found!")

print(f"Found {len(tif_files)} raster tiles")


# Build VRT -------------------------------------------------------

print("Building VRT...")

vrt_options = gdal.BuildVRTOptions(
    resolution="highest",
    resampleAlg="nearest",
    separate=False,
    VRTNodata=nodata_value
)

gdal.BuildVRT(tmp_vrt, tif_files, options=vrt_options)


# Convert VRT to uint8 (temporary GeoTIFF) -------------------------

print("Converting to uint8...")

gdal.Translate(
    tmp_tif,
    tmp_vrt,
    options=gdal.TranslateOptions(
        outputType=gdal.GDT_Byte,
        noData=nodata_value
    )
)


# Add color table ---------------------------------------------------

print("Adding color table...")

colormap = {}


# Build full uint8 colormap
for val in range(256):
    if val == nodata_value:
        colormap[val] = (0, 0, 0, 0)  # transparent nodata
    elif 1 <= val <= 30:
        colormap[val] = COLORS[val]
    else:
        colormap[val] = (0, 0, 0, 0)  # everything else transparent


with rasterio.open(tmp_tif, "r+") as ds:
    for _, window in ds.block_windows(1):
        data = ds.read(1, window=window)

        data[(data < 1) | (data > 30)] = nodata_value

        ds.write(data, 1, window=window)


    ds.write_colormap(1, colormap)
    ds.colorinterp = [ColorInterp.palette]
    ds.nodata = nodata_value
    ds.write_colormap(1, colormap)
    ds.colorinterp = [ColorInterp.palette]
    ds.nodata = nodata_value

# Convert to final Cloud Optimized GeoTIFF ---------------------------

print("Creating Cloud Optimized GeoTIFF...")

gdal.Translate(
    output_cog,
    tmp_tif,
    options=gdal.TranslateOptions(
        format="COG",
        creationOptions=[
            f"COMPRESS={compression}",
            f"BLOCKSIZE={block_size}",
            "BIGTIFF=IF_SAFER",
            "OVERVIEWS=IGNORE_EXISTING",
            "RESAMPLING=NEAREST"
        ]
    )
)

# Cleanup
os.remove(tmp_vrt)
os.remove(tmp_tif)

print(f"Cloud Optimized GeoTIFF created: {output_cog}")
