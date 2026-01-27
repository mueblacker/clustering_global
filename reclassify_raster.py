# Script to reclassify a raster using rasterio

# Load packages --------------------------------------------------
import rasterio
import numpy as np


# Settings -----------------------------------------------------

# Define directories
input_raster = "/mnt/shared/hydrography90m_v.1.0_online/hydrography90m_v.1.0/r.watershed/sub_catchment_tiles20d/sub_catchment_h30v00.tif"
output_raster = "/mnt/mschuerz/mschuerz/data/clustering_global/world/output_reclass.tif"
rules_file = "/mnt/mschuerz/mschuerz/data/clustering_global/world/cluster_tables/clusters30_h30v00.txt"

# Define rule columns
OLD_VALUE = 2  
NEW_VALUE = 3  

# Define output settings
DEFAULT_VALUE = 0
OUTPUT_DTYPE = np.uint8  # < 50 classes

# Read lookup table --------------------------------------------
print("Loading rules...")

mapping = {}

with open(rules_file, "r") as f:
    header = next(f)  # skip header line
    for line_num, line in enumerate(f, start=2):
        if not line.strip():
            continue

        parts = line.split()
        try:
            old_val = int(parts[OLD_VALUE])
            new_val = int(parts[NEW_VALUE])
            mapping[old_val] = new_val
        except (IndexError, ValueError):
            raise ValueError(f"Invalid rule at line {line_num}: {line}")

print(f"Loaded {len(mapping):,} rules")

# Reclassify raster ----------------------------------------------
with rasterio.open(input_raster) as src:
    profile = src.profile.copy()

    profile.update(
        dtype=OUTPUT_DTYPE,
        count=1,
        nodata=DEFAULT_VALUE,
        compress="deflate"
    )

    with rasterio.open(output_raster, "w", **profile) as dst:
        for _, window in src.block_windows(1):
            data = src.read(1, window=window)

            nodata_mask = (
                data == src.nodata if src.nodata is not None else None
            )

            unique_vals, inverse = np.unique(data, return_inverse=True)

            mapped = np.empty(len(unique_vals), dtype=OUTPUT_DTYPE)
            for i, val in enumerate(unique_vals):
                mapped[i] = mapping.get(int(val), DEFAULT_VALUE)

            out = mapped[inverse].reshape(data.shape)

            if nodata_mask is not None:
                out[nodata_mask] = DEFAULT_VALUE

            dst.write(out, 1, window=window)

print("Reclassification complete")
