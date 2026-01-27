import os
import glob
import random
import numpy as np
import rasterio
from osgeo import gdal
from rasterio.enums import ColorInterp

# ---------------- CONFIG ----------------
input_dir = "/data/mschuerz/clustering_global/world/cluster_rasters"   # input TIFFs (can be network-mounted)
output_cog = "/data/mschuerz/clustering_global/world/world_clusters30_cog.tif"
tmp_vrt = "/data/mschuerz/clustering_global/world/merged.vrt"
compression = "ZSTD"  # Compression method for COG
block_size = 512
overview_levels = [2, 4, 8, 16, 32]
nodata_value = 0
# ----------------------------------------


# ---------------- Step 1: Collect input files ----------------
tif_files = sorted(glob.glob(os.path.join(input_dir, "*.tif")))
if not tif_files:
    raise RuntimeError("No .tif files found in input directory!")

# ---------------- Step 2: Build VRT (memory-efficient) ----------------
print("➡ Building VRT...")
vrt_options = gdal.BuildVRTOptions(
    resolution="average",
    separate=False,
    VRTNodata=nodata_value
)
gdal.BuildVRT(tmp_vrt, tif_files, options=vrt_options)

# ---------------- Step 3: Convert VRT to Cloud Optimized GeoTIFF (COG) with uint8 ----------------
print("➡ Creating Cloud Optimized GeoTIFF (uint8)...")

translate_options = gdal.TranslateOptions(
    format="COG",
    outputType=gdal.GDT_Byte,  # Convert to uint8 (1 byte per pixel)
    creationOptions=[
        f"COMPRESS={compression}",
        "BIGTIFF=IF_SAFER",  # For larger datasets
        # Removed PREDICTOR option as it's not necessary for uint8
    ],
    noData=nodata_value
)

gdal.Translate(
    destName=output_cog,
    srcDS=tmp_vrt,
    options=translate_options
)

# ---------------- Step 4: Add color table ----------------
print("➡ Adding color table...")

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

# ---------------- Step 5: Build overviews ----------------
print("➡ Building overviews...")
with rasterio.open(output_cog, "r+") as ds:
    ds.build_overviews(overview_levels, resampling=rasterio.enums.Resampling.nearest)

# Cleanup temporary VRT file
os.remove(tmp_vrt)

print(f"✅ Cloud Optimized GeoTIFF (uint8) created: {output_cog}")
