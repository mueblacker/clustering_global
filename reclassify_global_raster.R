library(hydrographr)
library(dplyr)
library(data.table)


epto_stat <- fread("/data/mschuerz/clustering_global/world_v2/cluster30_epto_statistics_20260714.csv")

dr <- epto_stat %>%
    select(cluster_id, detected_richness) 


# Define input and output raster layer
subc_raster <- "/data/mschuerz/clustering_global/world_v2/world_clusters30.tif"

recl_raster <- "/data/mschuerz/clustering_global/world_v2/detected_richness_20260715.tif"


# Reclassification of the raster file -------------------------------------


# Reclassify the stream network to obtain the Strahler stream order raster
reclass_raster(data = dr,
               rast_val = "cluster_id",
               new_val = "detected_richness",
               raster_layer = subc_raster,
               recl_layer = recl_raster,
               quiet = FALSE)