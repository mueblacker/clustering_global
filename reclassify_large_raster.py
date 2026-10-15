import os
import pandas as pd
import numpy as np
from osgeo import gdal
from concurrent.futures import ProcessPoolExecutor


gdal.UseExceptions()

# =====================================================
# USER SETTINGS
# =====================================================

input_raster = "/data/mschuerz/clustering_global/world_v2/world_clusters30.tif"

lookup_csv = "/data/mschuerz/clustering_global/world_v2/cluster30_epto_statistics_selected_20260828.csv"

output_folder = "/data/mschuerz/clustering_global/world_v2/epto_raster_20260902"

columns = [
    "total_records",
    "spatial_coverage",
    "species_id_rate",
    "detected_richness",
    "completeness",
    "CWE",
    "restricted_taxa_n"
]

workers = 7


# =====================================================
# OUTPUT TYPES
# =====================================================

output_types = {

    "total_records": gdal.GDT_UInt32, #NoData 0 is fine

    "spatial_coverage": gdal.GDT_Float32, #NoData -9999

    "species_id_rate": gdal.GDT_Float32, #NoData -9999

    "detected_richness": gdal.GDT_UInt16, #NoData 0 is fine

    "completeness": gdal.GDT_Float32, #NoData -9999

    "CWE": gdal.GDT_Float32, #NoData -9999

    "restricted_taxa_n": gdal.GDT_UInt16 #NotData 65535
}

nodata_values = {
    "total_records": 0,
    "spatial_coverage": -9999.0,
    "species_id_rate": -9999.0,
    "detected_richness": 0,
    "completeness": -9999.0,
    "CWE": -9999.0,
    "restricted_taxa_n": 65535
}


numpy_types = {

    "total_records": np.uint32,
    "spatial_coverage": np.float32,
    "species_id_rate": np.float32,
    "detected_richness": np.uint16,
    "completeness": np.float32,
    "CWE": np.float32,
    "restricted_taxa_n": np.uint16

}


# =====================================================
# TIFF OPTIONS
# =====================================================

tiff_options = [
    "BIGTIFF=YES",
    "TILED=YES",
    "BLOCKXSIZE=512",
    "BLOCKYSIZE=512",
    "COMPRESS=ZSTD",
    "ZSTD_LEVEL=3"
]


cog_options = [
    "BIGTIFF=YES",
    "COMPRESS=ZSTD",
    "BLOCKSIZE=512",
    "OVERVIEWS=AUTO",
    "NUM_THREADS=ALL_CPUS"
]


# =====================================================
# READ LOOKUP TABLE
# =====================================================

lut = pd.read_csv(lookup_csv)

class_col = lut.columns[0]

max_class = int(lut[class_col].max())


lookup_tables = {}


for col in columns:

    arr = np.zeros(
        max_class + 1,
        dtype=numpy_types[col]
    )


    for _, row in lut.iterrows():

        arr[
            int(row[class_col])
        ] = row[col]


    lookup_tables[col] = arr



# =====================================================
# PROCESS ONE CLASSIFICATION
# =====================================================

def process(column):

    print("Starting:", column)


    src = gdal.Open(
        input_raster,
        gdal.GA_ReadOnly
    )


    band = src.GetRasterBand(1)

    src_nodata = band.GetNoDataValue()
    dst_nodata = nodata_values[column]


    os.makedirs(
        output_folder,
        exist_ok=True
    )


    temp_output = os.path.join(
        output_folder,
        f"{column}_optimized.tif"
    )


    cog_output = os.path.join(
        output_folder,
        f"{column}_COG.tif"
    )


    driver = gdal.GetDriverByName(
        "GTiff"
    )


    dst = driver.Create(
        temp_output,
        src.RasterXSize,
        src.RasterYSize,
        1,
        output_types[column],
        options=tiff_options
    )


    dst.SetGeoTransform(
        src.GetGeoTransform()
    )


    dst.SetProjection(
        src.GetProjection()
    )


    outband = dst.GetRasterBand(1)


    outband.SetNoDataValue(dst_nodata)



    lookup = lookup_tables[column]


    block = 512


    for y in range(
        0,
        src.RasterYSize,
        block
    ):

        rows = min(
            block,
            src.RasterYSize-y
        )


        for x in range(
            0,
            src.RasterXSize,
            block
        ):

            cols = min(
                block,
                src.RasterXSize-x
            )

            


            data = band.ReadAsArray(
                x,
                y,
                cols,
                rows
            )

            # Remember which pixels are NoData
            mask = (data == src_nodata)

            # Lookup values
            result = lookup[data].copy()

            # Restore NoData pixels
            result[mask] = dst_nodata

            outband.WriteArray(
                result,
                x,
                y
            )



    dst.FlushCache()

    dst = None
    src = None



    print("Creating COG:", column)

    # Re-open temp file to build overviews explicitly
    tmp_ds = gdal.Open(temp_output, gdal.GA_Update)
    # Build internal overviews (2x, 4x, 8x, 16x, 32x downsampling)
    tmp_ds.BuildOverviews("NEAREST", [2, 4, 8, 16, 32])
    tmp_ds = None # Close and flush to disk 

    gdal.Translate(
        cog_output,
        temp_output,
        format="COG",
        creationOptions=cog_options
    )


    print("Finished:", column)



# =====================================================
# RUN PARALLEL
# =====================================================

if __name__ == "__main__":

    with ProcessPoolExecutor(
        max_workers=workers
    ) as executor:

        executor.map(
            process,
            columns
        )


    print("ALL DONE")
