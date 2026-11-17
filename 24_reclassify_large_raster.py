# =========================================================================
# Create cluster-level EPTO metric rasters
#
# This script transfers values from a cluster-statistics lookup table to a
# categorical cluster raster. One output raster is created for each selected
# EPTO metric, with every cluster cell assigned its corresponding metric value.
#
# Outputs are written first as tiled GeoTIFFs and then converted to
# Cloud-Optimized GeoTIFFs (COGs) with internal overviews.
# =========================================================================


# Load modules ------------------------------------------------------------

# Standard libraries for file handling and parallel processing.
import os
from concurrent.futures import ProcessPoolExecutor

# Libraries for tabular data and numerical arrays.
import pandas as pd
import numpy as np

# GDAL functions for raster input, output, and COG creation.
from osgeo import gdal


# Enable GDAL exceptions so raster errors are returned as Python exceptions.
gdal.UseExceptions()


# User settings -----------------------------------------------------------

# Categorical raster containing cluster IDs.
input_raster = "/my_directory/data/clustering_global/l_fhc/lfhc_clusters30.tif"

# CSV table containing one row per cluster and the EPTO metrics to map.
lookup_csv = "/my_directory/data/clustering_global/l_fhc/cluster30_epto_statistics_selected_20260828.csv"

# Directory where metric GeoTIFFs and Cloud-Optimized GeoTIFFs are written.
output_folder = "/my_directory/data/clustering_global/l_fhc/epto_raster_20260902"

# Metrics from the lookup table that will be converted to rasters.
columns = [
    "total_records",
    "spatial_coverage",
    "species_id_rate",
    "detected_richness",
    "completeness",
    "CWE",
    "restricted_taxa_n"
]

# Number of metrics processed simultaneously.
workers = 7


# Define output data types ------------------------------------------------

# Define the GDAL raster data type for each output metric.
# Integer types are used for count variables and Float32 for proportions,
# percentages, and continuous biodiversity metrics.
output_types = {

    "total_records": gdal.GDT_UInt32, # NoData value 0 is used

    "spatial_coverage": gdal.GDT_Float32, # NoData value -9999

    "species_id_rate": gdal.GDT_Float32, # NoData value -9999

    "detected_richness": gdal.GDT_UInt16, # NoData value 0 is used

    "completeness": gdal.GDT_Float32, # NoData value -9999

    "CWE": gdal.GDT_Float32, # NoData value -9999

    "restricted_taxa_n": gdal.GDT_UInt16 # NoData value 65535
}

# Define the NoData value used in each metric raster.
nodata_values = {
    "total_records": 0,
    "spatial_coverage": -9999.0,
    "species_id_rate": -9999.0,
    "detected_richness": 0,
    "completeness": -9999.0,
    "CWE": -9999.0,
    "restricted_taxa_n": 65535
}

# Define NumPy data types used to create in-memory lookup arrays.
numpy_types = {

    "total_records": np.uint32,
    "spatial_coverage": np.float32,
    "species_id_rate": np.float32,
    "detected_richness": np.uint16,
    "completeness": np.float32,
    "CWE": np.float32,
    "restricted_taxa_n": np.uint16

}


# Define GeoTIFF options --------------------------------------------------

# Creation options for intermediate tiled GeoTIFF files.
tiff_options = [
    "BIGTIFF=YES",
    "TILED=YES",
    "BLOCKXSIZE=512",
    "BLOCKYSIZE=512",
    "COMPRESS=ZSTD",
    "ZSTD_LEVEL=3"
]

# Creation options for final Cloud-Optimized GeoTIFF files.
cog_options = [
    "BIGTIFF=YES",
    "COMPRESS=ZSTD",
    "BLOCKSIZE=512",
    "OVERVIEWS=AUTO",
    "NUM_THREADS=ALL_CPUS"
]


# Read lookup table -------------------------------------------------------

# Read the table containing cluster-level EPTO metrics.
lut = pd.read_csv(lookup_csv)

# Use the first column as the cluster/class ID column.
class_col = lut.columns[0]

# Find the highest cluster ID to determine the required lookup-array size.
max_class = int(lut[class_col].max())

# Create an empty dictionary that will store one lookup array per metric.
lookup_tables = {}


# Create lookup arrays ----------------------------------------------------

# Create a direct class-ID-to-metric-value lookup array for each metric.
# Array index positions represent cluster IDs, enabling efficient assignment
# of metric values to raster cells using `lookup[data]`.
for col in columns:

    arr = np.zeros(
        max_class + 1,
        dtype=numpy_types[col]
    )

    # Fill the lookup array with metric values from the statistics table.
    for _, row in lut.iterrows():

        arr[
            int(row[class_col])
        ] = row[col]

    # Store the completed lookup array for this metric.
    lookup_tables[col] = arr


# Process one metric ------------------------------------------------------

def process(column):
    """
    Create an EPTO metric raster for one lookup-table column.

    The input cluster raster is processed in blocks. Cluster IDs in each
    block are replaced by the corresponding values from the metric lookup
    array. The output is then converted to a Cloud-Optimized GeoTIFF.
    """

    print("Starting:", column)

    # Open the cluster-ID raster for reading.
    src = gdal.Open(
        input_raster,
        gdal.GA_ReadOnly
    )

    # Read the first raster band, which contains cluster IDs.
    band = src.GetRasterBand(1)

    # Read the source NoData value and select the target NoData value.
    src_nodata = band.GetNoDataValue()
    dst_nodata = nodata_values[column]

    # Create the output directory if it does not already exist.
    os.makedirs(
        output_folder,
        exist_ok=True
    )

    # Define paths for the intermediate GeoTIFF and final COG.
    temp_output = os.path.join(
        output_folder,
        f"{column}_optimized.tif"
    )

    cog_output = os.path.join(
        output_folder,
        f"{column}_COG.tif"
    )

    # Create a GDAL GeoTIFF driver for the intermediate raster.
    driver = gdal.GetDriverByName(
        "GTiff"
    )

    # Create an output raster with the same dimensions as the cluster raster.
    dst = driver.Create(
        temp_output,
        src.RasterXSize,
        src.RasterYSize,
        1,
        output_types[column],
        options=tiff_options
    )

    # Copy geographic reference information from the input raster.
    dst.SetGeoTransform(
        src.GetGeoTransform()
    )

    dst.SetProjection(
        src.GetProjection()
    )

    # Access the output raster band and define its NoData value.
    outband = dst.GetRasterBand(1)

    outband.SetNoDataValue(dst_nodata)

    # Retrieve the lookup array for the metric currently being processed.
    lookup = lookup_tables[column]

    # Process the raster in 512 x 512 cell blocks to limit memory use.
    block = 512

    for y in range(
        0,
        src.RasterYSize,
        block
    ):

        # Adjust block height at the lower raster edge if necessary.
        rows = min(
            block,
            src.RasterYSize-y
        )

        for x in range(
            0,
            src.RasterXSize,
            block
        ):

            # Adjust block width at the right raster edge if necessary.
            cols = min(
                block,
                src.RasterXSize-x
            )

            # Read cluster IDs for the current raster block.
            data = band.ReadAsArray(
                x,
                y,
                cols,
                rows
            )

            # Identify NoData cells in the source cluster raster.
            mask = (data == src_nodata)

            # Replace cluster IDs with the corresponding metric values.
            result = lookup[data].copy()

            # Restore NoData cells using the selected metric-specific value.
            result[mask] = dst_nodata

            # Write the converted metric values to the output raster.
            outband.WriteArray(
                result,
                x,
                y
            )

    # Flush all pending data to disk and close the source/output datasets.
    dst.FlushCache()

    dst = None
    src = None

    print("Creating COG:", column)

    # Reopen the intermediate raster to build internal overviews.
    # Nearest-neighbour resampling is appropriate for cluster-level metrics.
    tmp_ds = gdal.Open(temp_output, gdal.GA_Update)

    # Build overviews at several lower resolutions for efficient display.
    tmp_ds.BuildOverviews("NEAREST", [2, 4, 8, 16, 32])

    # Close the file and flush overviews to disk.
    tmp_ds = None

    # Convert the intermediate GeoTIFF to a Cloud-Optimized GeoTIFF.
    gdal.Translate(
        cog_output,
        temp_output,
        format="COG",
        creationOptions=cog_options
    )

    print("Finished:", column)


# Run processing in parallel ----------------------------------------------

# Only execute parallel processing when the script is run directly.
if __name__ == "__main__":

    # Process multiple output metrics simultaneously.
    with ProcessPoolExecutor(
        max_workers=workers
    ) as executor:

        executor.map(
            process,
            columns
        )

    print("ALL DONE")