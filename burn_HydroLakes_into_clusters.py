# Burn HydroLakes as NoData into the cluster raster files

# Load moduls -----------------------------------------------------
import os
import glob
from osgeo import gdal

# Intput ---------------------------------------------------------

input_dir = "/data/mschuerz/clustering_global/world_v2/cluster_rasters"
output_dir = "/data/mschuerz/clustering_global/world_v2/cluster_rasters_HydroLAKES"
merged_output = "/data/mschuerz/clustering_global/world_v2/world_clusters30.tif"

gdb_path = "/data/mschuerz/clustering_global/HydroLAKES_polys_v10.gdb"
layer_name = "HydroLAKES_polys_v10"

nodata_value = 0  

# Temporary files
tmp_vrt = os.path.join(output_dir, "temp.vrt")
tmp_merged = os.path.join(output_dir, "merged_uint8.tif")


# SETUP -----------------------------------------------------------
os.makedirs(output_dir, exist_ok=True)

gdal.UseExceptions()


# COLLECT INPUT FILES ---------------------------------------------
tif_files = sorted(glob.glob(os.path.join(input_dir, "*.tif")))
if not tif_files:
    raise RuntimeError("No .tif files found!")

print(f"Found {len(tif_files)} raster tiles")


# BUILD VRT (MERGE) -----------------------------------------------
print("Building VRT...")

vrt_options = gdal.BuildVRTOptions(
    resolution="highest",
    resampleAlg="nearest",
    separate=False,
    VRTNodata=nodata_value
)

gdal.BuildVRT(tmp_vrt, tif_files, options=vrt_options)

# CONVERT TO UINT8 ------------------------------------------
print("Converting merged raster to UInt8...")

gdal.Translate(
    tmp_merged,
    tmp_vrt,
    options=gdal.TranslateOptions(
        outputType=gdal.GDT_Byte,
        noData=nodata_value
    )
)


# LOAD VECTOR  ------------------------------------------------
print("Loading polygon layer from GDB...")

vector_ds = gdal.OpenEx(gdb_path, gdal.OF_VECTOR)
if vector_ds is None:
    raise RuntimeError("Could not open GDB")

layer = vector_ds.GetLayer(layer_name)
if layer is None:
    raise RuntimeError(f"Layer '{layer_name}' not found in GDB")


# MASK MERGED RASTER -------------------------------------------
print("Applying mask to merged raster...")

merged_ds = gdal.Open(tmp_merged, gdal.GA_Update)

gdal.RasterizeLayer(
    merged_ds,
    [1],  # assuming single-band raster
    layer,
    burn_values=[nodata_value]
)

merged_ds = None
print(f"Merged masked raster saved to: {merged_output}")

# Move final merged result
gdal.Translate(merged_output, tmp_merged)


# PROCESS EACH TILE ----------------------------------------------
print("Processing individual tiles...")

for tif in tif_files:
    filename = os.path.basename(tif)
    out_path = os.path.join(output_dir, filename)

    print(f"Processing {filename}...")

    # Convert to UInt8
    gdal.Translate(
        out_path,
        tif,
        options=gdal.TranslateOptions(
            outputType=gdal.GDT_Byte,
            noData=nodata_value
        )
    )

    # Apply mask
    tile_ds = gdal.Open(out_path, gdal.GA_Update)

    gdal.RasterizeLayer(
        tile_ds,
        [1],
        layer,
        burn_values=[nodata_value]
    )

    tile_ds = None

print("All tiles processed.")


# CLEANUP ----------------------------------------------------------
vector_ds = None

if os.path.exists(tmp_vrt):
    os.remove(tmp_vrt)

print("Done.")