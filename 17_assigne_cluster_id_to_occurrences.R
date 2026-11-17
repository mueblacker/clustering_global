# =========================================================================
# Assigne cluster ID to EPTO occurrences
# =========================================================================


# Load libraries ---------------------------------------------------------

library(dplyr)
library(tidyr)
library(data.table)
library(arrow)
library(sf)


# Load occurrence data ---------------------------------------------------

# Read the cleaned EPTO occurrence dataset.
# This dataset is expected to contain occurrence IDs, sub-catchment IDs,
# longitude/latitude coordinates, and other occurrence attributes.
epto <- fread(
  "/mnt/shared/mschuerz/Global_EPTO_database_clean_species_subc_corr_20260803.csv"
)


# Open the Parquet dataset containing sub-catchment cluster assignments.
cluster <- open_dataset(
  "/data/mschuerz/clustering_global/world_v2/cluster30_parquet/",
  format = "parquet"
)

# Select cluster assignments only for sub-catchments that occur in the EPTO data.
#
# - Filter to relevant sub-catchment IDs.
# - Keep sub-catchment ID and cluster ID columns.
# - Collect the filtered data from the Arrow dataset into R memory.
subc_cluster <- cluster %>%
  filter(subc_id %in% unique(epto$subcatchment_ID)) %>%
  select(subc_id, cluster_id) %>%
  collect()

# Join cluster IDs to the occurrence dataset using the sub-catchment identifier.
# Occurrences without a matching cluster assignment are retained because this
# is a left join.
join_epto_cluster <- left_join(
  epto,
  subc_cluster,
  by = join_by(subcatchment_ID == subc_id)
)

# Apply a manual correction for occurrence 107302491:
# - assign sub-catchment ID 41723638
# - assign cluster ID 6
join_epto_cluster <- join_epto_cluster %>%
  mutate(
    subcatchment_ID = ifelse(
      occurrence_ID == 107302491,
      41723638,
      subcatchment_ID
    ),
    cluster_id = ifelse(
      occurrence_ID == 107302491,
      6,
      cluster_id
    )
  )


# Save the occurrence dataset with joined cluster IDs.
fwrite(
  join_epto_cluster,
  "/my_directory/data/Global_EPTO_database_clean_species_subc_corr_cluster_id_20260803.csv"
)

# Extract occurrence records that still have no assigned cluster ID.
# These records can be reviewed and corrected separately.
na <- join_epto_cluster %>%
  filter(is.na(cluster_id))

# Save records without cluster assignments as a CSV file.
fwrite( na, "/my_directory/data/epto_na_20260803.csv")


# Convert records without cluster assignments to a spatial point layer.
# Longitude and latitude are used as point coordinates in WGS84 (EPSG:4326).
sf_na <- na %>%
  st_as_sf(coords = c("longitude", "latitude"), crs = 4326)

# Write the unassigned occurrence points to a GeoPackage for spatial inspection.
write_sf(sf_na, "/my_directory/data/epto_na_20260803.gpkg")
