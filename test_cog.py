import os
import glob
import random
from osgeo import gdal

gdal.UseExceptions()

# ---------------- SETTINGS ---------------- #


input_dir = "/data/mschuerz/clustering_global/world_wo_lc/cluster_rasters/clusters75"
output_cog = "/data/mschuerz/clustering_global/world_wo_lc/world_wo_lc_clusters75_cog.tif"

tmp_vrt = "/data/mschuerz/tmp_merged.vrt"
tmp_pal = "/data/mschuerz/tmp_paletted.tif"

compression = "ZSTD"
zstd_level = "6"          # good speed/size balance
block_size = 512
nodata_value = 0
num_threads = "15"

# ------------------------------------------ #

# Performance tuning
gdal.SetConfigOption("GDAL_NUM_THREADS", num_threads)
gdal.SetConfigOption("GDAL_CACHEMAX", "4096")  # 4GB cache


def consistent_color(val):
    rnd = random.Random(int(val))
    return (
        rnd.randint(0, 255),
        rnd.randint(0, 255),
        rnd.randint(0, 255),
        255
    )


# -------------------------------------------------------
# 1️⃣ Collect tiles
# -------------------------------------------------------

tif_files = sorted(glob.glob(os.path.join(input_dir, "*.tif")))
if not tif_files:
    raise RuntimeError("No .tif files found!")

print(f"Found {len(tif_files)} raster tiles")


# -------------------------------------------------------
# 2️⃣ Build VRT (virtual mosaic)
# -------------------------------------------------------

print("Building VRT...")

vrt_options = gdal.BuildVRTOptions(
    resolution="highest",
    resampleAlg="nearest",
    separate=False,
    VRTNodata=nodata_value
)

gdal.BuildVRT(tmp_vrt, tif_files, options=vrt_options)


# -------------------------------------------------------
# 3️⃣ Translate VRT → temporary paletted GeoTIFF
#    (NOT COG yet — embed color table here)
# -------------------------------------------------------

print("Creating temporary paletted GeoTIFF...")

gdal.Translate(
    tmp_pal,
    tmp_vrt,
    options=gdal.TranslateOptions(
        format="GTiff",
        outputType=gdal.GDT_Byte,
        noData=nodata_value,
        creationOptions=[
            "TILED=YES",
            f"BLOCKXSIZE={block_size}",
            f"BLOCKYSIZE={block_size}",
            f"COMPRESS={compression}",
            f"ZSTD_LEVEL={zstd_level}",
            "BIGTIFF=IF_SAFER"
        ]
    )
)

# Add full 0–255 color table WITHOUT reading raster
print("Embedding color table...")

ds = gdal.Open(tmp_pal, gdal.GA_Update)
band = ds.GetRasterBand(1)

ct = gdal.ColorTable()

for val in range(256):
    if val == nodata_value:
        ct.SetColorEntry(val, (0, 0, 0, 0))  # transparent nodata
    else:
        ct.SetColorEntry(val, consistent_color(val))

band.SetRasterColorTable(ct)
band.SetRasterColorInterpretation(gdal.GCI_PaletteIndex)
band.SetNoDataValue(nodata_value)

ds = None  # flush


# -------------------------------------------------------
# 4️⃣ Convert paletted TIFF → Final COG
#    (single clean write, builds overviews internally)
# -------------------------------------------------------

print("Creating final Cloud Optimized GeoTIFF...")

gdal.Translate(
    output_cog,
    tmp_pal,
    options=gdal.TranslateOptions(
        format="COG",
        creationOptions=[
            f"COMPRESS={compression}",
            f"BLOCKSIZE={block_size}",
            f"LEVEL={zstd_level}",
            "BIGTIFF=IF_SAFER",
            "RESAMPLING=NEAREST",
            "OVERVIEWS=IGNORE_EXISTING"
        ]
    )
)

# Cleanup
os.remove(tmp_vrt)
os.remove(tmp_pal)

print(f"✅ Cloud Optimized GeoTIFF created: {output_cog}")
