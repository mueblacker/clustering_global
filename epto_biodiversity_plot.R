library(terra)
library(ggplot2)
library(tidyterra)
library(patchwork)
library(viridisLite)
library(scales)


#------------------------------------------------------------
# Read rasters
#------------------------------------------------------------
r1 <- rast("/data/mschuerz/clustering_global/world_v2/epto_raster_20260902/detected_richness_COG.tif")
r2 <- rast("/data/mschuerz/clustering_global/world_v2/epto_raster_20260902/completeness_COG.tif")
r3 <- rast("/data/mschuerz/clustering_global/world_v2/epto_raster_20260902/CWE_COG.tif")
r4 <- rast("/data/mschuerz/clustering_global/world_v2/epto_raster_20260902/restricted_taxa_n_COG.tif")


#------------------------------------------------------------
# Common theme
#------------------------------------------------------------

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


#------------------------------------------------------------
# Richness
#------------------------------------------------------------

p1 <- ggplot() +
  geom_spatraster(data = r1, maxcell = 10000000) +
  aes(fill = lyr.1) +

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
    x = NULL,
    y = "Latitude",
  ) +

  theme_map +
  theme(
    axis.text.x = element_blank(),
    axis.ticks.x = element_blank()
  )


#------------------------------------------------------------
# Completeness
#------------------------------------------------------------

p2 <- ggplot() +
  geom_spatraster(data = r2, maxcell = 10000000) +
  aes(fill = lyr.1) +

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
    x = NULL,
    y = NULL,
  ) +

  theme_map +
  theme(
    axis.title.y = element_blank(),
    axis.text.x = element_blank(),
    axis.ticks.x = element_blank(),
    axis.text.y = element_blank(),
    axis.ticks.y = element_blank()
  )


#------------------------------------------------------------
# CWE
#------------------------------------------------------------

p3 <- ggplot() +
  geom_spatraster(data = r3, maxcell = 10000000) +
  aes(fill = lyr.1) +

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
    x = "Longitude",
    y = "Latitude" ,
  ) +

  theme_map


#------------------------------------------------------------
# Restricted taxa
#------------------------------------------------------------

p4 <- ggplot() +
  geom_spatraster(data = r4, maxcell = 10000000) +
  aes(fill = lyr.1) +

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
    x = "Longitude",
    y = NULL,
  ) +

  theme_map +
  theme(
    axis.text.y = element_blank(),
    axis.ticks.y = element_blank()
  )


#------------------------------------------------------------
# Layout
#------------------------------------------------------------

figure <-
  (p1 + p2 +
   p3 + p4) +
  plot_layout(
    ncol = 2,
    guides = "collect"

  )

figure

ggsave(
  "/data/mschuerz/clustering_global/world_v2/epto_biodiversity_20260922.svg",
  figure,
  dpi = 600
)