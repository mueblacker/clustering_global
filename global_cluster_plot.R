###############################################################
## Plot two categorical GeoTIFFs
###############################################################

library(terra)
library(tidyterra)
library(ggplot2)
library(patchwork)
library(cowplot)
library(grid)
library(shadowtext)

###############################################################
## Files
###############################################################

landcover_file <- "/data/mschuerz/clustering_global/world_v2/world_clusters30.tif"
driver_file    <- "/data/mschuerz/clustering_global/world_wo_lc/world_wo_lc_clusters20.tif"

###############################################################
## Read rasters
###############################################################

landcover <- rast(landcover_file)[[1]]
drivers   <- rast(driver_file)[[1]]

###############################################################
## Aggregate rasters for plotting
## Increase fact (e.g. 10 or 20) if plotting is still slow.
###############################################################

fact <- 20

landcover_plot <- aggregate(
  landcover,
  fact = fact,
  fun = "modal",
  na.rm = TRUE
)

drivers_plot <- aggregate(
  drivers,
  fact = fact,
  fun = "modal",
  na.rm = TRUE
)

###############################################################
## Convert to factors
###############################################################

landcover_plot <- as.factor(landcover)
drivers_plot   <- as.factor(drivers)

###############################################################
## Colors
###############################################################
landcover_cols <- c(
  "1"  = "#66A61E",  # Natural vegetation & cropland 
  "2"  = "#A6D854",  # Natural vegetation & cropland 
  "3"  = "#DECCAA",  # Bare area 
  "4"  = "#B8D95A",  # Grassland 
  "5"  = "#88b7fc",  # Annual streamflow 
  "6"  = "#006D2C",  # Tree broadleaf evergreen 
  "7"  = "#C9B458",  # Sparse vegetation 
  "8"  = "#238B45",  # Tree mixed leaf 
  "9"  = "#f7dc48",  # Cropland irrigated 
  "10" = "#004F5A",  # Precipitation driest month + evergreen -
  "11" = "#EAF4F4",  # Snow and ice 
  "12" = "#2d82d6",  # Stream power & flow accumulation 
  "13" = "#2F8F83",  # Tree flooded freshwater 
  "14" = "#f5a94c",  # Bare area + precipitation seasonality 
  "15" = "#8B5A2B",  # Elevation 
  "16" = "#00441B",  # Tree needle evergreen 
  "17" = "#8DAA5B",  # Shrubland - muted green
  "18" = "#FFC107",  # Cropland rainfed 
  "19" = "#4DAF4A",  # Tree broadleaf deciduous 
  "20" = "#A9C46C",  # Grassland 
  "21" = "#8BC34A",  # Cropland + natural vegetation 
  "22" = "#8C8C5A",  # Lichens & mosses 
  "23" = "#22C7D6",  # Annual precipitation 
  "24" = "#52B788",  # Shrub/herb flooded 
  "25" = "#014485",  # Water bodies 
  "26" = "#3f8afc",  # Flow accumulation 
  "27" = "#512DA8",  # Stream gradient 
  "28" = "#B5C97A",  # Mosaic crop + natural vegetation 
  "29" = "#1B5E20",  # Tree needle deciduous 
  "30" = "#689F38"   # Tree/shrub/herb 
)



driver_cols <- c(
  "1"  = "#458596", # Precipitation Regime 
  "2"  = "#c73489",  # Channel Morphometry & Gradient 
  "3"  = "#455A64",  # Distance to outlet
  "4"  = "#5d9dfc",  # Hydrological Flow & Connectivity 
  "5"  = "#eb3c1e",  # Temperature Regime 
  "6"  = "#1a9cb8",  # Precipitation Regime 
  "7"  = "#512DA8",  # Channel Morphometry & Gradient - purple
  "8"  = "#f55c42",  # Temperature Regime 
  "9"  = "#871501",   # Temperature Regime 
  "10" = "#0D47A1",  # Hydrological Flow & Connectivity 
  "11" = "#1263e0",  # Hydrological Flow & Connectivity 
  "12" = "#88b7fc",  # Hydrological Flow & Connectivity 
  "13" = "#fc8672",  # Temperature Regime 
  "14" = "#22C7D6", # Precipitation Regime 
  "15" = "#004F5A",  # Precipitation Regime 
  "16" = "#048787",  # Precipitation Regime 
  "17" = "#8B5A2B",  # Elevation 
  "18" = "#9f27ba",  # Channel Morphometry & Gradient 
  "19" = "#3f8afc",  # Hydrological Flow & Connectivity 
  "20" = "#90A4AE"   # Distance to outlet 
)

###############################################################
## Function: create square extent
###############################################################

square_extent <- function(xmin, ymin, xmax, ymax){
  
  w <- xmax - xmin
  h <- ymax - ymin
  
  if(w > h){
    d <- (w - h)/2
    ymin <- ymin - d
    ymax <- ymax + d
  } else {
    d <- (h - w)/2
    xmin <- xmin - d
    xmax <- xmax + d
  }
  
  ext(xmin, xmax, ymin, ymax)
}

###############################################################
## Define regions
###############################################################

ext1 <- square_extent(
  xmin = -73.86,
  ymin = 2.33,
  xmax = -64.95,
  ymax = 10.76
)

ext2 <- square_extent(
  xmin = 30.601,
  ymin = 26.178,
  xmax = 32.099,
  ymax = 27.433
)

ext3 <- square_extent(
  xmin = 134.155,
  ymin = 48.04,
  xmax = 137.155,
  ymax = 50.629
)


###############################################################
## Bounding boxes for overview maps
###############################################################

boxes <- data.frame(
  xmin = c(xmin(ext1), xmin(ext2), xmin(ext3)),
  xmax = c(xmax(ext1), xmax(ext2), xmax(ext3)),
  ymin = c(ymin(ext1), ymin(ext2), ymin(ext3)),
  ymax = c(ymax(ext1), ymax(ext2), ymax(ext3)),
  label = c("1", "2", "3")
)


###############################################################
## Plot land cover
###############################################################

boxes$label_x <- boxes$xmax + 1.5      # adjust depending on map scale
boxes$label_y <- boxes$ymax



p1 <- ggplot() +
  geom_spatraster(data = landcover_plot, maxcell = 1000000) +
  geom_rect(
    data = boxes,
    aes(xmin = xmin, xmax = xmax,
        ymin = ymin, ymax = ymax),
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
    values = landcover_cols,
    limits = names(landcover_cols),
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
    plot.title = element_text(face = "bold",
    margin = margin(b = 1)),
    legend.position = "bottom",
    legend.box = "horizontal"
  ) +
  guides(fill = guide_legend(
    ncol = 10,
    byrow = TRUE
  ))

###############################################################
## Plot drivers
###############################################################

p2 <- ggplot() +
  geom_spatraster(data = drivers_plot, maxcell = 1000000) +
  geom_rect(
    data = boxes,
    aes(xmin = xmin, xmax = xmax,
        ymin = ymin, ymax = ymax),
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
    values = driver_cols,
    limits = names(driver_cols),
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
    plot.title = element_text(face = "bold",
    margin = margin(b = 1)),
    legend.position = "bottom",
    legend.box = "horizontal"
  ) +
  guides(fill = guide_legend(
    ncol = 10,
    byrow = TRUE
  ))

###############################################################
## Combine
###############################################################

final_plot <-
  p1 /
  p2 +
  plot_layout(heights = c(1, 1))

###############################################################
## Display
###############################################################

print(final_plot)

###############################################################
## Save as A4
###############################################################

ggsave(
  filename = "/data/mschuerz/clustering_global/fhc_20260831_6.svg",
  plot = final_plot,
  width = 8.27,
  height = 11.69,
  units = "in",
  dpi = 300
)

ggsave(
  filename = "/data/mschuerz/clustering_global/fhc_20260831_6.png",
  plot = final_plot,
  width = 8.27,
  height = 11.69,
  units = "in",
  dpi = 300
)

###############################################################
## SECOND FIGURE - Three regional details
###############################################################

###############################################################
## Crop rasters
###############################################################

lc1 <- crop(landcover_plot, ext1)
lc2 <- crop(landcover_plot, ext2)
lc3 <- crop(landcover_plot, ext3)

dr1 <- crop(drivers_plot, ext1)
dr2 <- crop(drivers_plot, ext2)
dr3 <- crop(drivers_plot, ext3)

###############################################################
## Plot function
###############################################################

plot_lc <- function(r, title=NULL){
  
  ggplot() +
    geom_spatraster(data=r,  maxcell = 1000000) +
    scale_fill_manual(
      values = landcover_cols,
      drop = TRUE,
      na.value="transparent",
      name="ID"
    ) +
    coord_sf(expand=FALSE) +
    labs(title=title,x=NULL,y=NULL) +
    theme_bw(base_size=11) +
    theme(
      panel.grid=element_blank(),
      axis.text=element_blank(),
      axis.ticks=element_blank(),
      plot.title=element_text(face="bold",hjust=0.5),
      legend.position = "none"
    )
}

plot_driver <- function(r,title=NULL){
  
  ggplot() +
    geom_spatraster(data=r,  maxcell = 1000000) +
    scale_fill_manual(
      values = driver_cols,
      drop = TRUE,
      na.value="transparent",
      name="ID"
    ) +
    coord_sf(expand=FALSE) +
    labs(title=title,x=NULL,y=NULL) +
    theme_bw(base_size=11) +
    theme(
      panel.grid=element_blank(),
      axis.text=element_blank(),
      axis.ticks=element_blank(),
      plot.title=element_text(face="bold",hjust=0.5),
      legend.position = "none"
    )
}

###############################################################
## Build panels
###############################################################

p_lc1 <- plot_lc(lc1,"1 - Orinoco")
p_lc2 <- plot_lc(lc2,"2 - Nile")
p_lc3 <- plot_lc(lc3,"3 - Amur")



p_dr1 <- plot_driver(dr1,"1 - Orinoco")
p_dr2 <- plot_driver(dr2,"2 - Nile")
p_dr3 <- plot_driver(dr3,"3 - Amur")



###############################################################
## Collect legends
###############################################################

lc_legend <- merge(sprc(lc1, lc2, lc3))
dr_legend <- merge(sprc(dr1, dr2, dr3))


lc_leg <-
  ggplot() +
  geom_spatraster(data = lc_legend) +
  scale_fill_manual(
    values = landcover_cols,
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
  guides(fill = guide_legend(
    nrow = 2,
    byrow = TRUE
  ))

lc_leg <- cowplot::get_legend(lc_leg)

dr_leg <-
  ggplot() +
  geom_spatraster(data = dr_legend) +
  scale_fill_manual(
    values = driver_cols,
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
  guides(fill = guide_legend(
    nrow = 2,
    byrow = TRUE
  ))
dr_leg <- cowplot::get_legend(dr_leg)

# Title
lc_title <- wrap_elements(
  grid::textGrob(
    "L-FHCs",
    x = 0,                # left aligned
    hjust = 0,
    gp = gpar(fontsize = 14, fontface = "bold")
  )
)

driver_title <- wrap_elements(
  grid::textGrob(
    "P-FHCs",
    x = 0,
    hjust = 0,
    gp = gpar(fontsize = 14, fontface = "bold")
  )
)

###############################################################
## Combine
###############################################################
detail_plot <-
  lc_title /
  (p_lc1 | p_lc2 | p_lc3) /
  wrap_elements(lc_leg) /
  driver_title /
  (p_dr1 | p_dr2 | p_dr3) /
  wrap_elements(dr_leg) +
  plot_layout(
    heights = c(0.07, 1, 0.18, 0.07, 1, 0.18)
  )

###############################################################
## Display
###############################################################

print(detail_plot)

###############################################################
## Save
###############################################################

ggsave(
  filename ="~/phd/figures/fhc_details_20260726_2.svg",
  detail_plot,
  width = 11,
  height = 7.5,
  units = "in",
  dpi = 300
)

ggsave(
  filename ="/data/mschuerz/clustering_global/fhc_details_202600831_1.png",
  detail_plot,
  width = 11,
  height = 7.5,
  units = "in",
  dpi = 300
)
