# Script to reclassify the sub-catchment ID raster layer
# according to the cluster IDs

# Load packages
import rasterio
import numpy as np
from pathlib import Path
from multiprocessing import Pool, cpu_count

# Settings --------------------------------------------

# Define directories
subc_dir = Path("/data/mschuerz/sub_catchment_tiles")
rules_dir = Path("/data/mschuerz/clustering_global/world/cluster_tables")
output_dir = Path("/data/mschuerz/clustering_global/world/cluster_rasters")
output_dir.mkdir(parents=True, exist_ok=True)

# Fixed prefixes
RASTER_PREFIX = "sub_catchment"
RULE_PREFIX = "clusters30"
OUTPUT_PREFIX = "clusters30"

# Define columns in the rule file (0-based)
OLD_VALUE = 2
NEW_VALUE = 3

# Output settings
DEFAULT_VALUE = 0
OUTPUT_DTYPE = np.uint8
MAX_WORKERS = 15 # max(4, cpu_count() - 35)


# Core functions -------------------------------------

# Function to load rules from the look up table (.txt)
def load_rules(rule_file):
    mapping = {}
    with open(rule_file) as f:
        next(f)  # skip header
        for line in f:
            if not line.strip():
                continue
            parts = line.split()
            mapping[int(parts[OLD_VALUE])] = int(parts[NEW_VALUE])
    return mapping

# Function to reclassify the raster file
def reclassify_one(args):
    raster_path, rule_path, out_path = args
    try:
        print(f"Processing {raster_path.name}")
        mapping = load_rules(rule_path)

        with rasterio.open(raster_path) as src:
            profile = src.profile.copy()
            profile.update(
                dtype=OUTPUT_DTYPE,
                count=1,
                nodata=DEFAULT_VALUE,
                compress="deflate"
            )

            with rasterio.open(out_path, "w", **profile) as dst:
                for _, window in src.block_windows(1):
                    data = src.read(1, window=window)
                    nodata_mask = data == src.nodata if src.nodata is not None else None

                    unique_vals, inverse = np.unique(data, return_inverse=True)
                    mapped = np.array([mapping.get(int(v), DEFAULT_VALUE) for v in unique_vals], dtype=OUTPUT_DTYPE)
                    out = mapped[inverse].reshape(data.shape)

                    if nodata_mask is not None:
                        out[nodata_mask] = DEFAULT_VALUE

                    dst.write(out, 1, window=window)
        return out_path.name
    except Exception as e:
        print(f"Error processing {raster_path.name}: {e}")
        return None

# Build job list -----------------------------------------

def build_jobs():
    # Only .tif raster files
    rasters = sorted(
        f for f in subc_dir.glob(f"{RASTER_PREFIX}_*.tif")
        if f.is_file() and f.suffix.lower() == ".tif"
    )

    jobs = []
    for r in rasters:
        tile_id = r.stem[len(RASTER_PREFIX)+1:]
        rule_file = rules_dir / f"{RULE_PREFIX}_{tile_id}.txt"
        if not rule_file.exists():
            print(f"⚠ Missing rule file for {r.name} (expected {rule_file.name})")
            continue

        out_file = output_dir / f"{OUTPUT_PREFIX}_{tile_id}.tif"
        jobs.append((r, rule_file, out_file))

    print(f"Found {len(jobs)} raster-rule pairs")
    return jobs



# Main - execute functions -----------------------------

if __name__ == "__main__":
    jobs = build_jobs()

    if not jobs:
        print("No valid raster-rule pairs found. Exiting.")
        exit(1)

    print(f"Using {MAX_WORKERS} parallel workers")

    from tqdm import tqdm  # optional for progress bar
    with Pool(processes=MAX_WORKERS, maxtasksperchild=1) as pool:
    # chunksize=1 ensures one raster per CPU at a time
         for result in tqdm(pool.imap_unordered(reclassify_one, jobs, chunksize=1), total=len(jobs)):
            if result:
                print(f"Finished {result}")

    print("All rasters processed")


# Test mode: only first raster-rule pair --------------

# jobs = build_jobs()

# raster_path, rule_path, out_path = jobs[0]
# reclassify_one((raster_path, rule_path, out_path))

