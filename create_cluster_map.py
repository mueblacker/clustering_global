import rasterio
from rasterio.enums import Resampling
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

cog_path = "/data/mschuerz/clustering_global/world_v2/world_clusters30_cog_v2.tif"

with rasterio.open(cog_path) as src:
    scale_factor = 8  # adjust for performance

    # Read downsampled class IDs
    data = src.read(
        1,
        out_shape=(
            src.height // scale_factor,
            src.width // scale_factor
        ),
        resampling=Resampling.nearest
    )

    # Read embedded colormap
    cmap = src.colormap(1)

# --- Convert colormap (0–255 → 0–1) ---
cmap_norm = {
    k: tuple(v_i / 255 for v_i in v)
    for k, v in cmap.items()
}

# --- Create RGBA image from class IDs ---
height, width = data.shape
rgba = np.zeros((height, width, 4))

for class_id, color in cmap_norm.items():
    rgba[data == class_id] = color

# --- Plot ---
fig, ax = plt.subplots(figsize=(14, 7))
ax.imshow(rgba)
ax.set_title("Global Map")
ax.axis("off")

# --- Legend (from colormap!) ---
legend_elements = []

for class_id in sorted(cmap_norm.keys()):
    if class_id == 0:
        continue  # skip nodata

    legend_elements.append(
        Patch(
            facecolor=cmap_norm[class_id],
            edgecolor="black",
            label=str(class_id)
        )
    )

ax.legend(
    handles=legend_elements,
    title="cluster ID",
    loc="lower center",
    bbox_to_anchor=(0.5, -0.25),
    ncol=10,
    frameon=False
)

# --- Save ---
plt.savefig(
    "/data/mschuerz/clustering_global/world_v2/world_cluster_30_map.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close()