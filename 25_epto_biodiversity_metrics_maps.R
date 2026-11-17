# =========================================================================
# Global maps of EPTO biodiversity metrics
#
# Creates maps showing:
# - observed species richness
# - inventory completeness based on the Chao2 estimator
# - corrected weighted endemism (CWE)
# - number of cluster-restricted taxa
#
# =========================================================================


# Load libraries ----------------------------------------------------------

library(terra)
library(tidyterra)
library(ggplot2)
library(patchwork)
library(viridisLite)
library(scales)


# Define input and output files -------------------------------------------

# Directory data folder
data_dir <- "/my_directory/data/clustering_global/l_fhc/epto_raster_20260902"

# Raster of detected/observed species richness per cluster.
richness_file <- file.path(
  data_dir,
  "detected_richness_COG.tif"
)

# Raster of inventory completeness: observed richness divided by Chao2
# estimated richness.
completeness_file <- file.path(
  data_dir,
  "completeness_COG.tif"
)

# Raster of corrected weighted endemism values.
cwe_file <- file.path(
  data_dir,
  "CWE_COG.tif"
)

# Raster of the number of taxa restricted to a single cluster.
restricted_taxa_file <- file.path(
  data_dir,
  "restricted_taxa_n_COG.tif"
)

# Output file for the multi-panel biodiversity figure.
output_file <- file.path(
  data_dir,
  "epto_biodiversity_20260922.svg"
  )

# Read rasters ------------------------------------------------------------

# Read detected species richness values.
r_richness <- rast(richness_file)

# Read Chao2-based inventory completeness values.
r_completeness <- rast(completeness_file)

# Read corrected weighted endemism values.
r_cwe <- rast(cwe_file)

# Read counts of restricted taxa.
r_restricted_taxa <- rast(restricted_taxa_file)


# Define common map theme -------------------------------------------------

# Create a common theme for all maps in the figure.
theme_map <- theme_bw() +
  theme(
    panel.grid = element_blank(),
    panel.border = element_rect(colour = "black"),
    legend.title = element_text(face = "bold", size = 10),
    legend.text = element_text(size = 9),
    legend.key.height = unit(0.6, "cm"),
    legend.box = "horizontal",
    legend.direction = "vertical",
    legend.position = "right",
    axis.title = element_text(size = 10),
    axis.text = element_text(size = 8),
    plot.tag = element_text(face = "bold", size = 14),
    plot.tag.position = c(0, 1)
  )


# Plot detected richness --------------------------------------------------

# Plot the observed number of species per cluster.
# A log10 colour scale is used because richness varies strongly among clusters.
p_richness <- ggplot() +
  geom_spatraster(
    data = r_richness,
    aes(fill = lyr.1),
    maxcell = 10000000
  ) +
  scale_fill_viridis_c(
    option = "viridis",
    trans = "log10",
    breaks = c(10, 30, 100, 300, 1000, 3000),
    labels = c("10", "30", "100", "300", "1,000", "3,000"),
    na.value = "white",
    name = "Detected richness"
  ) +
  coord_sf(
    xlim = c(-180, 180),
    ylim = c(-60, 90),
    expand = FALSE
  ) +
  labs(
    tag = "a",
    x = NULL,
    y = "Latitude"
  ) +
  theme_map +
  theme(
    axis.text.x = element_blank(),
    axis.ticks.x = element_blank()
  )


# Plot completeness -------------------------------------------------------

# Plot inventory completeness as observed richness divided by Chao2
# estimated richness. Values closer to 1 indicate more complete sampling.
p_completeness <- ggplot() +
  geom_spatraster(
    data = r_completeness,
    aes(fill = lyr.1),
    maxcell = 10000000
  ) +
  scale_fill_viridis_c(
    option = "viridis",
    limits = c(0.15, 0.88),
    breaks = c(0.2, 0.4, 0.6, 0.8),
    labels = function(x) paste0(x * 100, "%"),
    na.value = "white",
    name = "Completeness"
  ) +
  coord_sf(
    xlim = c(-180, 180),
    ylim = c(-60, 90),
    expand = FALSE
  ) +
  labs(
    tag = "b",
    x = NULL,
    y = NULL
  ) +
  theme_map +
  theme(
    axis.title.y = element_blank(),
    axis.text.x = element_blank(),
    axis.ticks.x = element_blank(),
    axis.text.y = element_blank(),
    axis.ticks.y = element_blank()
  )


# Plot corrected weighted endemism ----------------------------------------

# Plot Corrected Weighted Endemism (CWE).
# Higher values indicate communities with proportionally more range-restricted
# taxa, after accounting for differences in species richness.
p_cwe <- ggplot() +
  geom_spatraster(
    data = r_cwe,
    aes(fill = lyr.1),
    maxcell = 10000000
  ) +
  scale_fill_viridis_c(
    option = "viridis",
    limits = c(0.06, 0.33),
    breaks = c(0.05, 0.10, 0.15, 0.20, 0.25, 0.30),
    labels = function(x) sprintf("%.2f", x),
    na.value = "white",
    name = "CWE"
  ) +
  coord_sf(
    xlim = c(-180, 180),
    ylim = c(-60, 90),
    expand = FALSE
  ) +
  labs(
    tag = "c",
    x = "Longitude",
    y = "Latitude"
  ) +
  theme_map


# Plot restricted taxa ----------------------------------------------------

# Plot the number of taxa found in only one L-FHC.
# A log1p scale allows zero values while reducing the visual dominance of
# clusters with very large restricted-taxon counts.
p_restricted_taxa <- ggplot() +
  geom_spatraster(
    data = r_restricted_taxa,
    aes(fill = lyr.1),
    maxcell = 10000000
  ) +
  scale_fill_viridis_c(
    option = "viridis",
    trans = "log1p",
    breaks = c(0, 1, 5, 10, 25, 50, 100, 250, 500),
    labels = c("0", "1", "5", "10", "25", "50", "100", "250", "500"),
    na.value = "white",
    name = "Restricted taxa"
  ) +
  coord_sf(
    xlim = c(-180, 180),
    ylim = c(-60, 90),
    expand = FALSE
  ) +
  labs(
    tag = "d",
    x = "Longitude",
    y = NULL
  ) +
  theme_map +
  theme(
    axis.text.y = element_blank(),
    axis.ticks.y = element_blank()
  )


# Combine plots -----------------------------------------------------------

# Arrange the four biodiversity maps in a two-column layout.
# Legends are collected into a shared legend area.
figure <- (
  p_richness +
  p_completeness +
  p_cwe +
  p_restricted_taxa
) +
  plot_layout(
    ncol = 2,
    guides = "collect"
  )

# Display the final figure.
print(figure)


# Save figure -------------------------------------------------------------

# Save the biodiversity figure as an SVG file.
ggsave(
  filename = output_file,
  plot = figure,
  dpi = 600
)