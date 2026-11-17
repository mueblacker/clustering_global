# =========================================================================
# Global and detail maps of the freshwater habitat clusters
#
# Creates:
# - a global comparison map of L-FHC and P-FHC cluster classifications
# - detail maps for the Orinoco, Nile, and Amur regions
#
# Raster values represent categorical cluster IDs. Rasters are aggregated
# using the modal cluster value to improve plotting performance.
# =========================================================================


# Load libraries ----------------------------------------------------------


library(terra)
library(tidyterra)
library(ggplot2)
library(patchwork)
library(cowplot)
library(grid)
library(shadowtext)


# Define input and output files -------------------------------------------

# Global L-FHC cluster raster.
lfhc_file <- "/my_directory/data/clustering_global/l_fhc/lfhc_clusters30.tif"

# Global P-FHC cluster raster.
pfhc_file <- "/my_directory/data/clustering_global/p_fhc/pfhc_clusters20.tif"

# Output files for the global comparison figure.
global_svg_file <- "/my_directory/data/clustering_global/fhc_20260831_6.svg"
global_png_file <- "/my_directory/data/clustering_global/fhc_20260831_6.png"

# Output files for the regional-detail figure.
detail_svg_file <- "/my_directory/data/clustering_global/fhc_details_20260726_2.svg"
detail_png_file <- "/my_directory/data/clustering_global/fhc_details_202600831_1.png"


# Load rasters ------------------------------------------------------------

# Read the first layer from each categorical cluster raster.
lfhc <- rast(lfhc_file)[[1]]
pfhc <- rast(pfhc_file)[[1]]


# Aggregate rasters for plotting ------------------------------------------

# Aggregate raster cells to reduce plotting time.
# Increase this value if global plotting remains slow.
fact <- 20

# Use the modal category within each aggregated cell to preserve
# the dominant categorical cluster value.
lfhc_plot <- aggregate(
  lfhc,
  fact = fact,
  fun = "modal",
  na.rm = TRUE
)

pfhc_plot <- aggregate(
  pfhc,
  fact = fact,
  fun = "modal",
  na.rm = TRUE
)

# Convert the aggregated cluster rasters to categorical/factor rasters.
lfhc_plot <- as.factor(lfhc_plot)
pfhc_plot <- as.factor(pfhc_plot)


# Define cluster colours --------------------------------------------------

# Colours for the 30 L-FHC clusters.
lfhc_cols <- c(
  "1"  = "#66A61E",  # Natural vegetation and cropland
  "2"  = "#A6D854",  # Natural vegetation and cropland
  "3"  = "#DECCAA",  # Bare area
  "4"  = "#B8D95A",  # Grassland
  "5"  = "#88b7fc",  # Annual streamflow
  "6"  = "#006D2C",  # Evergreen broadleaf trees
  "7"  = "#C9B458",  # Sparse vegetation
  "8"  = "#238B45",  # Mixed-leaf trees
  "9"  = "#f7dc48",  # Irrigated cropland
  "10" = "#004F5A",  # Driest-month precipitation and evergreen vegetation
  "11" = "#EAF4F4",  # Snow and ice
  "12" = "#2d82d6",  # Stream power and flow accumulation
  "13" = "#2F8F83",  # Flooded freshwater trees
  "14" = "#f5a94c",  # Bare area and precipitation seasonality
  "15" = "#8B5A2B",  # Elevation
  "16" = "#00441B",  # Evergreen needleleaf trees
  "17" = "#8DAA5B",  # Shrubland
  "18" = "#FFC107",  # Rainfed cropland
  "19" = "#4DAF4A",  # Deciduous broadleaf trees
  "20" = "#A9C46C",  # Grassland
  "21" = "#8BC34A",  # Cropland and natural vegetation
  "22" = "#8C8C5A",  # Lichens and mosses
  "23" = "#22C7D6",  # Annual precipitation
  "24" = "#52B788",  # Flooded shrub/herb vegetation
  "25" = "#014485",  # Water bodies
  "26" = "#3f8afc",  # Flow accumulation
  "27" = "#512DA8",  # Stream gradient
  "28" = "#B5C97A",  # Mosaic cropland and natural vegetation
  "29" = "#1B5E20",  # Deciduous needleleaf trees
  "30" = "#689F38"   # Tree/shrub/herb vegetation
)

# Colours for the 20 P-FHC clusters.
pfhc_cols <- c(
  "1"  = "#458596",  # Precipitation regime
  "2"  = "#c73489",  # Channel morphometry and gradient
  "3"  = "#455A64",  # Distance to outlet
  "4"  = "#5d9dfc",  # Hydrological flow and connectivity
  "5"  = "#eb3c1e",  # Temperature regime
  "6"  = "#1a9cb8",  # Precipitation regime
  "7"  = "#512DA8",  # Channel morphometry and gradient
  "8"  = "#f55c42",  # Temperature regime
  "9"  = "#871501",  # Temperature regime
  "10" = "#0D47A1",  # Hydrological flow and connectivity
  "11" = "#1263e0",  # Hydrological flow and connectivity
  "12" = "#88b7fc",  # Hydrological flow and connectivity
  "13" = "#fc8672",  # Temperature regime
  "14" = "#22C7D6",  # Precipitation regime
  "15" = "#004F5A",  # Precipitation regime
  "16" = "#048787",  # Precipitation regime
  "17" = "#8B5A2B",  # Elevation
  "18" = "#9f27ba",  # Channel morphometry and gradient
  "19" = "#3f8afc",  # Hydrological flow and connectivity
  "20" = "#90A4AE"   # Distance to outlet
)


# Define map extents ------------------------------------------------------

# Create a square spatial extent around a specified bounding box.
# Square extents make the regional panels visually comparable.
square_extent <- function(xmin, ymin, xmax, ymax) {
  
  width <- xmax - xmin
  height <- ymax - ymin
  
  if (width > height) {
    difference <- (width - height) / 2
    ymin <- ymin - difference
    ymax <- ymax + difference
  } else {
    difference <- (height - width) / 2
    xmin <- xmin - difference
    xmax <- xmax + difference
  }
  
  ext(xmin, xmax, ymin, ymax)
}

# Define square extents for the three regional examples.
ext_orinoco <- square_extent(
  xmin = -73.86,
  ymin = 2.33,
  xmax = -64.95,
  ymax = 10.76
)

ext_nile <- square_extent(
  xmin = 30.601,
  ymin = 26.178,
  xmax = 32.099,
  ymax = 27.433
)

ext_amur <- square_extent(
  xmin = 134.155,
  ymin = 48.04,
  xmax = 137.155,
  ymax = 50.629
)

# Create bounding boxes and labels for the global overview maps.
boxes <- data.frame(
  xmin = c(xmin(ext_orinoco), xmin(ext_nile), xmin(ext_amur)),
  xmax = c(xmax(ext_orinoco), xmax(ext_nile), xmax(ext_amur)),
  ymin = c(ymin(ext_orinoco), ymin(ext_nile), ymin(ext_amur)),
  ymax = c(ymax(ext_orinoco), ymax(ext_nile), ymax(ext_amur)),
  label = c("1", "2", "3")
)


# Create global overview maps ---------------------------------------------

# Plot the global L-FHC raster and mark the three regional detail areas.
p_lfhc_global <- ggplot() +
  geom_spatraster(data = lfhc_plot, maxcell = 1000000) +
  geom_rect(
    data = boxes,
    aes(xmin = xmin, xmax = xmax, ymin = ymin, ymax = ymax),
    inherit.aes = FALSE,
    fill = NA,
    colour = "red3",
    linewidth = 1
  ) +
  geom_shadowtext(
    data = boxes,
    aes(
      x = xmax + 0.8,
      y = ymax,
      label = label
    ),
    colour = "red3",
    bg.colour = "white",
    bg.r = 0.15,
    fontface = "bold",
    size = 4,
    hjust = 0,
    vjust = 0.5
  ) +
  scale_fill_manual(
    values = lfhc_cols,
    limits = names(lfhc_cols),
    drop = FALSE,
    na.value = "transparent",
    name = "Cluster ID"
  ) +
  coord_sf(expand = FALSE) +
  labs(
    title = "a) L-FHCs",
    x = "Longitude",
    y = "Latitude"
  ) +
  theme_bw(base_size = 11) +
  theme(
    panel.grid = element_blank(),
    plot.title = element_text(
      face = "bold",
      margin = margin(b = 1)
    ),
    legend.position = "bottom",
    legend.box = "horizontal"
  ) +
  guides(
    fill = guide_legend(
      ncol = 10,
      byrow = TRUE
    )
  )

# Plot the global P-FHC raster and mark the same regional detail areas.
p_pfhc_global <- ggplot() +
  geom_spatraster(data = pfhc_plot, maxcell = 1000000) +
  geom_rect(
    data = boxes,
    aes(xmin = xmin, xmax = xmax, ymin = ymin, ymax = ymax),
    inherit.aes = FALSE,
    fill = NA,
    colour = "red3",
    linewidth = 1
  ) +
  geom_shadowtext(
    data = boxes,
    aes(
      x = xmax + 0.8,
      y = ymax,
      label = label
    ),
    colour = "red3",
    bg.colour = "white",
    bg.r = 0.15,
    fontface = "bold",
    size = 4,
    hjust = 0,
    vjust = 0.5
  ) +
  scale_fill_manual(
    values = pfhc_cols,
    limits = names(pfhc_cols),
    drop = FALSE,
    na.value = "transparent",
    name = "Cluster ID"
  ) +
  coord_sf(expand = FALSE) +
  labs(
    title = "b) P-FHCs",
    x = "Longitude",
    y = "Latitude"
  ) +
  theme_bw(base_size = 11) +
  theme(
    panel.grid = element_blank(),
    plot.title = element_text(
      face = "bold",
      margin = margin(b = 1)
    ),
    legend.position = "bottom",
    legend.box = "horizontal"
  ) +
  guides(
    fill = guide_legend(
      ncol = 10,
      byrow = TRUE
    )
  )

# Combine the two global maps vertically.
global_plot <- p_lfhc_global /
  p_pfhc_global +
  plot_layout(heights = c(1, 1))

# Display the global comparison figure.
print(global_plot)


# Save global overview figure ---------------------------------------------

# Save the global figure in SVG and PNG formats using A4 portrait dimensions.
ggsave(
  filename = global_svg_file,
  plot = global_plot,
  width = 8.27,
  height = 11.69,
  units = "in",
  dpi = 300
)

ggsave(
  filename = global_png_file,
  plot = global_plot,
  width = 8.27,
  height = 11.69,
  units = "in",
  dpi = 300
)


# Create regional detail maps ---------------------------------------------

# Crop the L-FHC raster to each regional extent.
lc_orinoco <- crop(lfhc_plot, ext_orinoco)
lc_nile <- crop(lfhc_plot, ext_nile)
lc_amur <- crop(lfhc_plot, ext_amur)

# Crop the P-FHC raster to each regional extent.
dr_orinoco <- crop(pfhc_plot, ext_orinoco)
dr_nile <- crop(pfhc_plot, ext_nile)
dr_amur <- crop(pfhc_plot, ext_amur)


# Define regional plotting functions --------------------------------------

# Create a regional L-FHC cluster map without a legend.
plot_lfhc_detail <- function(raster, title = NULL) {
  
  ggplot() +
    geom_spatraster(data = raster, maxcell = 1000000) +
    scale_fill_manual(
      values = lfhc_cols,
      drop = TRUE,
      na.value = "transparent",
      name = "Cluster ID"
    ) +
    coord_sf(expand = FALSE) +
    labs(title = title, x = NULL, y = NULL) +
    theme_bw(base_size = 11) +
    theme(
      panel.grid = element_blank(),
      axis.text = element_blank(),
      axis.ticks = element_blank(),
      plot.title = element_text(
        face = "bold",
        hjust = 0.5
      ),
      legend.position = "none"
    )
}

# Create a regional P-FHC cluster map without a legend.
plot_pfhc_detail <- function(raster, title = NULL) {
  
  ggplot() +
    geom_spatraster(data = raster, maxcell = 1000000) +
    scale_fill_manual(
      values = pfhc_cols,
      drop = TRUE,
      na.value = "transparent",
      name = "Cluster ID"
    ) +
    coord_sf(expand = FALSE) +
    labs(title = title, x = NULL, y = NULL) +
    theme_bw(base_size = 11) +
    theme(
      panel.grid = element_blank(),
      axis.text = element_blank(),
      axis.ticks = element_blank(),
      plot.title = element_text(
        face = "bold",
        hjust = 0.5
      ),
      legend.position = "none"
    )
}


# Build regional map panels -----------------------------------------------

# L-FHC maps for the Orinoco, Nile, and Amur regions.
p_lc_orinoco <- plot_lfhc_detail(lc_orinoco, "1 - Orinoco")
p_lc_nile <- plot_lfhc_detail(lc_nile, "2 - Nile")
p_lc_amur <- plot_lfhc_detail(lc_amur, "3 - Amur")

# P-FHC maps for the Orinoco, Nile, and Amur regions.
p_dr_orinoco <- plot_pfhc_detail(dr_orinoco, "1 - Orinoco")
p_dr_nile <- plot_pfhc_detail(dr_nile, "2 - Nile")
p_dr_amur <- plot_pfhc_detail(dr_amur, "3 - Amur")


# Create legends ----------------------------------------------------------

# Merge the L-FHC regional rasters to create a legend containing categories
# represented across the three regional panels.
lc_legend_raster <- merge(sprc(lc_orinoco, lc_nile, lc_amur))

# Merge the P-FHC regional rasters for the equivalent legend.
dr_legend_raster <- merge(sprc(dr_orinoco, dr_nile, dr_amur))

# Create and extract the L-FHC legend as a separate graphical object.
lc_legend <- ggplot() +
  geom_spatraster(data = lc_legend_raster) +
  scale_fill_manual(
    values = lfhc_cols,
    drop = TRUE,
    na.translate = FALSE,
    na.value = "transparent",
    name = "Cluster ID"
  ) +
  theme_void() +
  theme(
    legend.position = "bottom",
    legend.title = element_text(face = "bold"),
    legend.key.width = unit(0.45, "cm")
  ) +
  guides(
    fill = guide_legend(
      nrow = 2,
      byrow = TRUE
    )
  )

lc_legend <- cowplot::get_legend(lc_legend)

# Create and extract the P-FHC legend as a separate graphical object.
dr_legend <- ggplot() +
  geom_spatraster(data = dr_legend_raster) +
  scale_fill_manual(
    values = pfhc_cols,
    drop = TRUE,
    na.translate = FALSE,
    na.value = "transparent",
    name = "Cluster ID"
  ) +
  theme_void() +
  theme(
    legend.position = "bottom",
    legend.title = element_text(face = "bold"),
    legend.key.width = unit(0.45, "cm")
  ) +
  guides(
    fill = guide_legend(
      nrow = 2,
      byrow = TRUE
    )
  )

dr_legend <- cowplot::get_legend(dr_legend)


# Create section titles ---------------------------------------------------

# Create left-aligned titles for the L-FHC and P-FHC detail-map sections.
lc_title <- wrap_elements(
  grid::textGrob(
    "L-FHCs",
    x = 0,
    hjust = 0,
    gp = gpar(fontsize = 14, fontface = "bold")
  )
)

dr_title <- wrap_elements(
  grid::textGrob(
    "P-FHCs",
    x = 0,
    hjust = 0,
    gp = gpar(fontsize = 14, fontface = "bold")
  )
)


# Combine regional detail figure ------------------------------------------

# Arrange the regional L-FHC and P-FHC panels with their corresponding
# legends and section titles.
detail_plot <- lc_title /
  (p_lc_orinoco | p_lc_nile | p_lc_amur) /
  wrap_elements(lc_legend) /
  dr_title /
  (p_dr_orinoco | p_dr_nile | p_dr_amur) /
  wrap_elements(dr_legend) +
  plot_layout(
    heights = c(0.07, 1, 0.18, 0.07, 1, 0.18)
  )

# Display the regional detail figure.
print(detail_plot)


# Save regional detail figure ---------------------------------------------

# Save the regional figure in SVG and PNG formats.
ggsave(
  filename = detail_svg_file,
  plot = detail_plot,
  width = 11,
  height = 7.5,
  units = "in",
  dpi = 300
)

ggsave(
  filename = detail_png_file,
  plot = detail_plot,
  width = 11,
  height = 7.5,
  units = "in",
  dpi = 300
)