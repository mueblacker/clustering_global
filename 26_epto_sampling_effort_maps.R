# =========================================================================
# Global maps of EPTO sampling representation and data quality
#
# Creates maps showing:
# - total occurrence records per cluster
# - spatial coverage of sub-catchments
# - species-level identification rate (SLIR)
#
# Raster values are aggregated before plotting to improve performance.
# =========================================================================


# Load libraries ----------------------------------------------------------

library(terra)
library(tidyterra)
library(ggplot2)
library(patchwork)
library(viridisLite)
library(scales)


# Define input and output files -------------------------------------------

# Define directory to data folder
data_dir <- "/my_directory/data/clustering_global/l_fhc/"

# Cluster-level total occurrence-record raster.
total_records_file <- paste0(
  data_dir,
  "epto_raster_20260902/total_records_COG.tif"
)

# Cluster-level spatial coverage raster.
spatial_coverage_file <- paste0(
  data_dir,
  "epto_raster_20260902/spatial_coverage_COG.tif"
)

# Cluster-level species-level identification-rate raster.
slir_file <- paste0(
  data_dir,
  "epto_raster_20260902/species_id_rate_COG.tif"
)

# Output figure file.
output_file <- paste0(
  data_dir,
  "epto_data_quality_20260921.svg"
)


# Read rasters ------------------------------------------------------------

# Read the total number of occurrence records per cluster.
r_total_records <- rast(total_records_file)

# Read the percentage of sampled sub-catchments per cluster.
r_spatial_coverage <- rast(spatial_coverage_file)

# Read the percentage of records identified at species level per cluster.
r_slir <- rast(slir_file)


# Aggregate rasters for plotting ------------------------------------------

# Aggregate raster cells to reduce rendering time.
# Increase this value if plotting remains slow.
fact <- 10

# Use the modal value because all three rasters represent cluster-level
# attributes repeated across categorical cluster cells.
r_total_records <- aggregate(
  r_total_records,
  fact = fact,
  fun = "modal",
  na.rm = TRUE
)

r_spatial_coverage <- aggregate(
  r_spatial_coverage,
  fact = fact,
  fun = "modal",
  na.rm = TRUE
)

r_slir <- aggregate(
  r_slir,
  fact = fact,
  fun = "modal",
  na.rm = TRUE
)


# Define total-record categories ------------------------------------------

# Define record-count intervals for the categorical total-records map.
breaks_records <- c(0, 100, 1000, 10000, 100000, 1000000, Inf)

# Numeric category values used after raster classification.
record_groups <- 1:6

# Labels displayed in the total-records legend.
labels_records <- c(
  "<100",
  "100–1k",
  "1k–10k",
  "10k–100k",
  "100k–1M",
  ">1M"
)

# Convert total occurrence records into six categories.
r_total_records_cat <- classify(
  r_total_records,
  rcl = matrix(
    c(
      -Inf,    100,       1,
      100,     1000,      2,
      1000,    10000,     3,
      10000,   100000,    4,
      100000,  1000000,   5,
      1000000, Inf,       6
    ),
    ncol = 3,
    byrow = TRUE
  )
)

# Convert the classified raster to a factor raster for discrete plotting.
r_total_records_cat <- as.factor(r_total_records_cat)

# Attach category labels to the factor levels.
levels(r_total_records_cat) <- data.frame(
  value = record_groups,
  label = labels_records
)

# Optionally save the aggregated and classified total-records raster.
writeRaster(
  r_total_records_cat,
  "/my_directory/data/clustering_global/l_fhc/epto_raster_20260902/total_records_COG_fact.tif",
  gdal = c("COMPRESS=DEFLATE", "TFW=YES"),
  overwrite = TRUE
)


# Define common map theme -------------------------------------------------

# Create a shared theme for all maps in the figure.
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


# Plot total occurrence records -------------------------------------------

# Plot categorical total occurrence records per cluster.
p_total_records <- ggplot() +
  geom_spatraster(
    data = r_total_records_cat,
    maxcell = 10000000
  ) +
  scale_fill_manual(
    values = setNames(cividis(6), record_groups),
    labels = labels_records,
    na.value = "white",
    name = "Total records"
  ) +
  coord_sf(
    xlim = c(-180, 180),
    ylim = c(-60, 90),
    expand = FALSE
  ) +
  labs(
    tag = "a",
    x = NULL,
    y = NULL
  ) +
  theme_map +
  theme(
    axis.title.y = element_blank(),
    axis.text.x = element_blank(),
    axis.ticks.x = element_blank()
  )


# Plot spatial coverage ---------------------------------------------------

# Plot the percentage of sub-catchments sampled in each cluster.
#
# A log10 scale is used because spatial coverage values vary strongly
# across clusters. Values are assumed to be proportions from 0 to 1.
p_spatial_coverage <- ggplot() +
  geom_spatraster(
    data = r_spatial_coverage,
    aes(fill = lyr.1),
    maxcell = 10000000
  ) +
  scale_fill_viridis_c(
    option = "inferno",
    trans = "log10",
    breaks = c(0.0001, 0.001, 0.01, 0.1, 0.3),
    labels = function(x) paste0(x * 100, "%"),
    na.value = "white",
    name = "Spatial coverage (%)"
  ) +
  coord_sf(
    xlim = c(-180, 180),
    ylim = c(-60, 90),
    expand = FALSE
  ) +
  labs(
    tag = "b",
    x = NULL,
    y = "Latitude"
  ) +
  theme_map +
  theme(
    axis.text.x = element_blank(),
    axis.ticks.x = element_blank()
  )


# Plot species-level identification rate ----------------------------------

# Plot the percentage of records identified to species level.
p_slir <- ggplot() +
  geom_spatraster(
    data = r_slir,
    aes(fill = lyr.1),
    maxcell = 10000000
  ) +
  scale_fill_viridis_c(
    option = "plasma",
    limits = c(50, 100),
    breaks = seq(50, 100, 10),
    labels = function(x) paste0(x, "%"),
    na.value = "white",
    name = "SLIR (%)"
  ) +
  coord_sf(
    xlim = c(-180, 180),
    ylim = c(-60, 90),
    expand = FALSE
  ) +
  labs(
    tag = "c",
    x = "Longitude",
    y = NULL
  ) +
  theme_map


# Combine plots -----------------------------------------------------------

# Arrange the three maps vertically and collect their legends.
figure <- (
  p_total_records +
  p_spatial_coverage +
  p_slir
) +
  plot_layout(
    ncol = 1,
    guides = "collect"
  )

# Display the combined figure.
print(figure)


# Save figure -------------------------------------------------------------

# Save the final figure as an SVG file.
ggsave(
  filename = output_file,
  plot = figure,
  width = 7,
  height = 18,
  dpi = 600
)