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

input_dir = "/data/mschuerz/clustering_global/world_wo_lc/cluster20_rasters_HydroLAKES/"
output_cog = "/data/mschuerz/clustering_global/world_wo_lc/pfhc_20k_20260921.tif"

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
    1:  ( 69, 133, 150, 255),   # Precipitation Regime
    2:  (199,  52, 137, 255),   # Channel Morphometry & Gradient
    3:  ( 69,  90, 100, 255),   # Distance to outlet
    4:  ( 93, 157, 252, 255),   # Hydrological Flow & Connectivity
    5:  (235,  60,  30, 255),   # Temperature Regime
    6:  ( 26, 156, 184, 255),   # Precipitation Regime
    7:  ( 81,  45, 168, 255),   # Channel Morphometry & Gradient - purple
    8:  (245,  92,  66, 255),   # Temperature Regime
    9:  (135,  21,   1, 255),   # Temperature Regime
    10: ( 13,  71, 161, 255),   # Hydrological Flow & Connectivity
    11: ( 18,  99, 224, 255),   # Hydrological Flow & Connectivity
    12: (136, 183, 252, 255),   # Hydrological Flow & Connectivity
    13: (252, 134, 114, 255),   # Temperature Regime
    14: ( 34, 199, 214, 255),   # Precipitation Regime
    15: (  0,  79,  90, 255),   # Precipitation Regime
    16: (  4, 135, 135, 255),   # Precipitation Regime
    17: (139,  90,  43, 255),   # Elevation
    18: (159,  39, 186, 255),   # Channel Morphometry & Gradient
    19: ( 63, 138, 252, 255),   # Hydrological Flow & Connectivity
    20: (144, 164, 174, 255),   # Distance to outlet
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
    elif 1 <= val <= 20:
        colormap[val] = COLORS[val]
    else:
        colormap[val] = (0, 0, 0, 0)  # everything else transparent


with rasterio.open(tmp_tif, "r+") as ds:
    for _, window in ds.block_windows(1):
        data = ds.read(1, window=window)

        data[(data < 1) | (data > 20)] = nodata_value

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
