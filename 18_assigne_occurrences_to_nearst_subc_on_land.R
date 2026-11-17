# =========================================================================
# Assigne occurrences which are located in the sea to the nearest 
# sub-catchment on land.
#
# The script identifies occurrence records that do not intersect a cluster
# raster cell, finds the nearest land cell within a local search area, and
# uses that cell's cluster ID. It then updates the full occurrence dataset.
# =========================================================================


# Libraries ---------------------------------------------------------------
library(terra)
library(dplyr)
library(data.table)

# Read raster tiles --------------------------------------------------------

#Sub-catchments
r1 <- rast("/my_directory/data/hydrography90m_v.1.0/r.watershed/sub_catchment_tiles20d/sub_catchment_h08v06.tif")
r2 <- rast("/my_directory/data/hydrography90m_v.1.0/r.watershed/sub_catchment_tiles20d/sub_catchment_h10v06.tif")

# Cluster
r3 <- rast("/my_directory/data/clustering_global/l_fhc/cluster_rasters_HydroLAKES/clusters30_h08v06.tif")
r4 <- rast("/my_directory/data/clustering_global/l_fhc/cluster_rasters_HydroLAKES/clusters30_h10v06.tif")

# Merge 
# sub-catchment tiles 
r <- mosaic(r1, r2)
# cluster tiles
rc <- mosaic(r3, r4)

# Treat cells with a value of 0 as sea/no-data
r[r == 0] <- NA

# Read occurrences ----------------------------------------------------------

# Read the occurrence dataset containing longitude, latitude, occurrence IDs,
# and existing sub-catchment/cluster information
occ <- read.csv("/my_directory/data/epto_na_20260803.csv")

# Select occurrences and vectorize ------------------------------------------

# Restrict the occurrence dataset to records west of longitude 15 degrees.
# This likely limits processing to the geographic extent of the loaded tiles.
occ <- occ %>%
    filter(longitude < 15)

# Convert occurrence longitude/latitude coordinates into a terra vector object.
# The input coordinates are assumed to use WGS84 geographic coordinates.
pts <- vect(
  occ,
  geom = c("longitude","latitude"),
  crs = "EPSG:4326"
)

# Identify occurrences that fall outside valid cluster raster cells.
# These records are assumed to be located in the sea or otherwise outside land.
idx <- which(is.na(occ$cluster_id))


# Loop through occurrences without a directly extracted cluster ID.
for(i in idx){

  # Get the coordinates of the current occurrence point.
  xy <- crds(pts)[i, , drop = FALSE]

  # 0.1° buffer (~11 km); adjust if needed
  e <- ext(
    xy[1]-0.1,
    xy[1]+0.1,
    xy[2]-0.1,
    xy[2]+0.1
  )

  # Crop the cluster raster to the local search extent.
  rr <- crop(rc, e, snap = "out")

  # Find raster cells in the local crop that have a valid cluster value.
  land <- which(!is.na(values(rr)))

  # Skip this occurrence if no land cells were found in the search extent.
  if(length(land) == 0)
    next

  # Get coordinates of all valid nearby land cells.
  land.xy <- xyFromCell(rr, land)

  # Calculate squared Euclidean distance from the occurrence point to each
  # nearby valid land cell. Squared distances are sufficient for identifying
  # the closest cell, so taking square roots is unnecessary.
  d2 <- (land.xy[, 1] - xy[1])^2 +
        (land.xy[, 2] - xy[2])^2

  # Assign the cluster ID of the nearest valid land cell to the occurrence.
  occ$cluster_id[i] <- values(rr)[land[which.min(d2)]]
}



# Read the complete occurrence dataset that will be updated.
all_records <- fread("/my_directory/data/Global_EPTO_database_clean_species_subc_corr_cluster_id_20260803.csv")

# Define occurrence IDs that require manually assigned cluster IDs.
ids_to_change <- c(100000001, 100000003, 100000008, 100002010)

# Assign cluster 25 to the manually identified occurrence records.
all_records <- all_records %>%
  mutate(cluster_id = if_else(
    occurrence_ID %in% ids_to_change,
    25,
    cluster_id
  ))


# Store the corrected occurrence table in a separate object.
# This table contains nearest-land cluster assignments for records that were
# originally located outside valid raster cells.
corrected <- occ


# Subcatchment id -----------------------------------------------------------

# Match occurrence IDs in the full dataset to occurrence IDs in the corrected
# subset. The result gives the row position in `corrected` for each full record.
idx <- match(
  all_records$occurrence_ID,
  corrected$occurrence_ID
)

# Identify records whose sub-catchment ID is currently 0.
# These are assumed to need a corrected nearest-land sub-catchment assignment.
missing <- all_records$subcatchment_ID == 0

# Replace missing/zero sub-catchment IDs with sub-catchment IDs from the
# corrected occurrence dataset.
all_records$subcatchment_ID[missing] <-
    corrected$subc_id[idx[missing]]


# Cluster id ----------------------------------------------------------------

# Match occurrence IDs again to retrieve corrected cluster IDs.
idx <- match(
  all_records$occurrence_ID,
  corrected$occurrence_ID
)

# Identify records that do not yet have a cluster ID.
missing <- is.na(all_records$cluster_id)

# Fill missing cluster IDs with nearest-land cluster IDs from `corrected`.
all_records$cluster_id[missing] <-
    corrected$cluster_id[idx[missing]]


# Save the updated occurrence data containing corrected sub-catchment and
# cluster assignments.
fwrite(
  all_records,
  "/my_directory/data/Global_EPTO_database_clean_species_corrected_20260803.csv",
  row.names = FALSE
)


# Create a vector containing all corrected occurrence IDs, including the
# manually updated records.
all_ids <- c(
  corrected$occurrence_ID,
  100000001,
  100000003,
  100000008,
  100002010
)

# Keep only corrected and manually updated records from the full dataset.
corr <- all_records %>%
  filter(occurrence_ID %in% all_ids)


# Read the occurrence dataset containing existing continent and sub-region
# assignments.
region <- fread(
  "/my_directory/data/Global_EPTO_database_clean_species_cluster_id_sub_region.csv"
)

# Define IDs for manually assigned Africa occurrences.
africa_ids <- c(100000001, 100000003, 100000008, 100002010)

# Treat all raster-corrected occurrence IDs as Cuba/South America records.
cuba_ids <- corrected$occurrence_ID


# Add corrected occurrence records to the regional dataset and update continent
# and UN sub-region assignments for the corrected records.
all <- region %>%
  
   # Append the corrected records to the existing regional dataset.
   add_row(corr) %>%
   
   # Assign regional classifications to the manually defined record groups.
   mutate(
     
     # Assign raster-corrected/Cuba records to South America.
     continent = ifelse(
       occurrence_ID %in% cuba_ids,
       "South America",
       continent
     ),
     
     # Assign manually listed records to Africa.
     continent = ifelse(
       occurrence_ID %in% africa_ids,
       "Africa",
       continent
     ),
     
     # Assign the Latin America and Caribbean sub-region to Cuba records.
     sub_region_name = ifelse(
       occurrence_ID %in% cuba_ids,
       "Latin America and the Caribbean",
       sub_region_name
     ),
     
     # Assign the Sub-Saharan Africa sub-region to African records.
     sub_region_name = ifelse(
       occurrence_ID %in% africa_ids,
       "Sub-Saharan Africa",
       sub_region_name
     )
   )


# Save the final occurrence dataset with corrected spatial, cluster, continent,
# and sub-region assignments.
fwrite(
  all,
  "/my_directory/data/Global_EPTO_database_clean_species_cluster_id_corr_continent_20260728.csv",
  row.names = FALSE
)