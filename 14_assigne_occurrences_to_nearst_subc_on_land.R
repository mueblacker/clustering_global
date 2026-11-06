library(terra)
library(dplyr)
library(data.table)

# Read raster tiles

#Sub-catchments
r1 <- rast("/mnt/shared/hydrography90m_v.1.0_online/hydrography90m_v.1.0/r.watershed/sub_catchment_tiles20d/sub_catchment_h08v06.tif")
r2 <- rast("/mnt/shared/hydrography90m_v.1.0_online/hydrography90m_v.1.0/r.watershed/sub_catchment_tiles20d/sub_catchment_h10v06.tif")

# Cluster
r3 <- rast("/data/mschuerz/clustering_global/world_v2/cluster_rasters_HydroLAKES/clusters30_h08v06.tif")
r4 <- rast("/data/mschuerz/clustering_global/world_v2/cluster_rasters_HydroLAKES/clusters30_h10v06.tif")

# Merge
r <- mosaic(r1, r2)
rc <- mosaic(r3, r4)

# sea = 0
r[r == 0] <- NA

occ <- read.csv("/mnt/shared/mschuerz/epto_na_20260803.csv")

occ <- occ %>%
    filter(longitude < 15)

pts <- vect(
  occ,
  geom = c("longitude","latitude"),
  crs = "EPSG:4326"
)

# initial extraction
occ$subc_id <- terra::extract(r, pts)[,2]

# Only process points in the sea
idx <- which(is.na(occ$subc_id))

for(i in idx){

  xy <- crds(pts)[i,,drop=FALSE]

  # 0.1° buffer (~11 km); adjust if needed
  e <- ext(
    xy[1]-0.1,
    xy[1]+0.1,
    xy[2]-0.1,
    xy[2]+0.1
  )

  rr <- crop(r, e, snap="out")

  land <- which(!is.na(values(rr)))

  if(length(land)==0)
    next

  land.xy <- xyFromCell(rr, land)

  d2 <- (land.xy[,1]-xy[1])^2 +
        (land.xy[,2]-xy[2])^2

  occ$subc_id[i] <- values(rr)[land[which.min(d2)]]
}

# initial extraction
occ$cluster_id <- extract(rc, pts)[,2]

# Only process points in the sea
idx <- which(is.na(occ$cluster_id))

for(i in idx){

  xy <- crds(pts)[i,,drop=FALSE]

  # 0.1° buffer (~11 km); adjust if needed
  e <- ext(
    xy[1]-0.1,
    xy[1]+0.1,
    xy[2]-0.1,
    xy[2]+0.1
  )

  rr <- crop(rc, e, snap="out")

  land <- which(!is.na(values(rr)))

  if(length(land)==0)
    next

  land.xy <- xyFromCell(rr, land)

  d2 <- (land.xy[,1]-xy[1])^2 +
        (land.xy[,2]-xy[2])^2

  occ$cluster_id[i] <- values(rr)[land[which.min(d2)]]
}




all_records <- fread("/mnt/shared/mschuerz/Global_EPTO_database_clean_species_subc_corr_cluster_id_20260803.csv")

ids_to_change <- c(100000001, 100000003, 100000008, 100002010)

all_records <- all_records %>%
  mutate(cluster_id = if_else(
    occurrence_ID %in% ids_to_change,
    25,
    cluster_id
  ))



corrected <- occ

# Subcatchment id
idx <- match(all_records$occurrence_ID,
             corrected$occurrence_ID)

missing <- all_records$subcatchment_ID == 0

all_records$subcatchment_ID[missing] <-
    corrected$subc_id[idx[missing]]

# Cluster id
idx <- match(all_records$occurrence_ID,
             corrected$occurrence_ID)

missing <- is.na(all_records$cluster_id)

all_records$cluster_id[missing] <-
    corrected$cluster_id[idx[missing]]


fwrite(all_records,
         "/mnt/shared/mschuerz/Global_EPTO_database_clean_species_corrected_20260803.csv",
          row.names = FALSE)

all_ids <- c(corrected$occurrence_ID, 100000001, 100000003, 100000008, 100002010)

corr <- all_records %>%
  filter(occurrence_ID %in% all_ids)

region <- fread("/mnt/shared/mschuerz/Global_EPTO_database_clean_species_cluster_id_sub_region.csv")

africa_ids <- c(100000001, 100000003, 100000008, 100002010)
cuba_ids <- corrected$occurrence_ID

all <- region %>%
   add_row(corr) %>%
   mutate(continent = ifelse(occurrence_ID %in% cuba_ids, "South America", continent),
          continent = ifelse(occurrence_ID %in% africa_ids, "Africa", continent),
          sub_region_name = ifelse(occurrence_ID %in% cuba_ids, "Latin America and the Caribbean", sub_region_name),
          sub_region_name =ifelse(occurrence_ID %in% africa_ids, "Sub-Saharan Africa", sub_region_name))

fwrite(all,
         "/mnt/shared/mschuerz/Global_EPTO_database_clean_species_cluster_id_corr_continent_20260728.csv",
          row.names = FALSE)
