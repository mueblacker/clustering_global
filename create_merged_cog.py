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

input_dir = "/data/mschuerz/clustering_global/world_v2/cluster_rasters"
output_cog = "/data/mschuerz/clustering_global/world_v2/world_clusters30_cog_v2.tif"

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
  
    1: (255, 0, 0, 255),       # red
    2: (0, 255, 0, 255),       # green
    3: (255, 255, 0, 255),     # yellow
    4: (255, 0, 128, 255),     # pink
    5: (255, 0, 255, 255),     # magenta
    6: (0, 255, 255, 255),     # cyan

    7: (128, 0, 0, 255),       # maroon
    8: (0, 128, 0, 255),       # dark green
    9: (0, 0, 128, 255),       # navy
    10: (128, 128, 0, 255),    # olive
    11: (214, 234, 240),       # ice blue
    12: (0, 128, 128, 255),    # teal

    13: (192, 64, 0, 255),     # orange-brown
    14: (255, 128, 0, 255),    # orange
    15: (0, 64, 192, 255),     # strong blue

    16: (192, 0, 64, 255),     # pink-red
    17: (64, 0, 192, 255),     # violet
    18: (0, 192, 64, 255),     # green-cyan

    19: (128, 0, 128, 255),    # purple
    20: (128, 255, 0, 255),    # yellow-green
    21: (0, 128, 255, 255),    # sky blue

    22: (128, 128, 255, 255),  # light blue
    23: (128, 0, 255, 255),    # purple-blue
    24: (0, 255, 128, 255),    # aqua-green

    25: (64, 64, 64, 255),     # dark gray
    26: (128, 255, 128, 255),  # light green
    27: (255, 128, 255, 255),  # light magenta

    28: (255, 255, 128, 255),  # light yellow
    29: (64, 192, 0, 255),     # lime green
    30: (0, 0, 255, 255),      # blue
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
