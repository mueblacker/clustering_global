library(terra)
library(ggplot2)
library(tidyterra)
library(patchwork)
library(viridisLite)
library(scales)


#------------------------------------------------------------
# Read rasters
#------------------------------------------------------------
r1 <- rast("/data/mschuerz/clustering_global/world_v2/epto_raster_20260902/total_records_COG_fact.tif")
r1 <- rast("/data/mschuerz/clustering_global/world_v2/epto_raster_20260902/total_records_COG.tif")
r2 <- rast("/data/mschuerz/clustering_global/world_v2/epto_raster_20260902/spatial_coverage_COG.tif")
r3 <- rast("/data/mschuerz/clustering_global/world_v2/epto_raster_20260902/species_id_rate_COG.tif")


#------------------------------------------------------------
# Aggregate for plotting
# (adjust fact if necessary)
#------------------------------------------------------------

fact <- 10

r1 <- aggregate(r1, fact = fact, fun = "modal")
r2 <- aggregate(r2, fact = fact, fun = "modal")
r3 <- aggregate(r3, fact = fact, fun = "modal")



r1_cat <- classify(
  r1,
  rcl = matrix(
    c(
      -Inf, 100,       1,
      100,  1000,      2,
      1000, 10000,     3,
      10000, 100000,   4,
      100000, 1000000, 5,
      1000000, Inf,    6
    ),
    ncol = 3,
    byrow = TRUE
  )
)

r1_cat <- as.factor(r1_cat)

levels(r1_cat) <- data.frame(
  value = 1:6,
  label = labels_rec
)
writeRaster(r1_cat,"/data/mschuerz/clustering_global/world_v2/epto_raster_20260902/total_records_COG_fact.tif", gdal=c("COMPRESS=DEFLATE", "TFW=YES"), overwrite=TRUE)
#------------------------------------------------------------
# Breaks for total records
#------------------------------------------------------------

breaks_rec <- c(0, 100, 1000, 10000, 100000, 1000000, Inf)

groups <- c(1, 2, 3, 4, 5, 6)

labels_rec <- c(
  "<100",
  "100–1k",
  "1k–10k",
  "10k–100k",
  "100k–1M",
  ">1M"
)

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
# Total records
#------------------------------------------------------------



  
p1 <- ggplot() +
  geom_spatraster(data = r1, maxcell = 10000000) +
  #aes(fill = lyr.1) +

   scale_fill_manual(
    values = setNames(cividis(6), groups),
    labels = labels_rec,
    na.value = "white",
    name = "Total records"
  ) +

  coord_sf(
    xlim = c(-180, 180),
    ylim = c(-60, 90),
    expand = FALSE
  ) +

  #scale_x_continuous(breaks = seq(-180,180,60)) +
  #scale_y_continuous(breaks = seq(-60,90,30)) +

  labs(
    x = NULL,
    y = NULL
  ) +

  theme_map +
  theme(
    axis.title.y = element_blank(),
    axis.text.x = element_blank(),
    axis.ticks.x = element_blank()
  )

#------------------------------------------------------------
# Spatial coverage
#------------------------------------------------------------

p2 <- ggplot() +
  geom_spatraster(data = r2, maxcell = 10000000) +
  aes(fill = lyr.1) +

  scale_fill_viridis_c(
    option = "inferno",
    trans = "log10",
    breaks = c(0.0001, 0.001, 0.01, 0.1, 0.3),
    labels = function(x) paste0(x* 100, "%"),
    na.value = "white",
    name = "Spatial coverage (%)"
  ) +

  coord_sf(
    xlim = c(-180,180),
    ylim = c(-60,90),
    expand = FALSE
  ) +

  #scale_x_continuous(breaks = seq(-180,180,60)) +
  #scale_y_continuous(breaks = seq(-60,90,30)) +

  labs(
    x = NULL,
    y = "Latitude"
  ) +

  theme_map +
  theme(
    #axis.title.y = element_blank(),
    axis.text.x = element_blank(),
    axis.ticks.x = element_blank()
  )

#------------------------------------------------------------
# Species ID rate
#------------------------------------------------------------

p3 <- ggplot() +
  geom_spatraster(data = r3,  maxcell = 10000000) +
  aes(fill = lyr.1) +

  scale_fill_viridis_c(
    option = "plasma",
    limits = c(50,100),
    breaks = seq(50,100,10),
    labels = function(x) paste0(x,"%"),
    na.value = "white",
    name = "SLIR (%)"
  ) +

  coord_sf(
    xlim = c(-180,180),
    ylim = c(-60,90),
    expand = FALSE
  ) +

  #scale_x_continuous(breaks = seq(-180,180,60)) +
  #scale_y_continuous(breaks = seq(-60,90,30)) +

  labs(
    x = "Longitude",
    y = NULL
  ) +

  theme_map

#------------------------------------------------------------
# Layout
#------------------------------------------------------------

legend <- guide_area()

p1 <- p1 +
  labs(tag = "a")
 labs(tag = "a")

p2 <- p2 +
  labs(tag = "b")

p3 <- p3 +
  labs(tag = "c")


figure <-
  (p1 + p2 +
   p3 ) +
  plot_layout(
    ncol = 1,
    guides = "collect"
  ) 

figure

ggsave(
  "/data/mschuerz/clustering_global/world_v2/epto_data_quality_20260921.svg",
  figure,
  width = 7,
  height = 18,
  dpi = 600
)
