# ============================================================
# Cluster-continent sampling summary
#
# Spatial unit: cluster_id + continent
#
# Calculates:
# - total occurrence records
# - species-level occurrence records
# - non-species-level occurrence records
# - species identification rate
#
# This table is intended as a supplementary assessment of
# geographic sampling coverage and taxonomic completeness.
#
# ============================================================


# Load libraries ----------------------------------------------

library(dplyr)
library(tidyr)
library(data.table)
library(arrow)


# Load occurrence data ----------------------------------------
epto <- fread("/mnt/shared//Global_EPTO_database_clean_species_cluster_id.csv")


tiles <- open_dataset(
  "/data/mschuerz/clustering_global/sub_catchment_continent_parquet",
  format = "parquet"
)

subcatchment_continent <- tiles %>%
  filter(subc_id %in% unique(epto$subcatchment_ID)) %>%
  select(subc_id, continent) %>%
  collect()

subcatchments <- fread(
  "/data/mschuerz/clustering_global/world_v2/cluster_size_count_20260714.csv"
)

# Join with sp data
epto <- epto %>%
  filter(!is.na(cluster_id)) %>%
  left_join(subcatchment_continent, by = c("subcatchment_ID" = "subc_id"))

sp_data <- epto %>%
    mutate(clean_species = ifelse(grepl("sp\\.", clean_species), "", clean_species),
            taxon = clean_species) 

total_subcatchments_long <- subcatchments %>%
  select(-total_subcatchments) %>%
  pivot_longer(
    cols = -cluster_id,
    names_to = "continent",
    values_to = "total_subcatchments"
  )

sampled_subcatchments <- sp_data %>%
  distinct(cluster_id, continent, subcatchment_ID) %>%
  count(cluster_id, continent, name = "sampled_subcatchments")

# Calculate sampling effort ----------------------------------

# Summarise occurrence records for each cluster within each
# continent.

cluster_continent_summary <- sp_data %>%
  group_by(cluster_id, continent) %>%
  summarise(

    # Records with species-level identification
    n_records = sum(clean_species != ""),

    # Records lacking species-level identification
    n_nosp_records = sum(clean_species == ""),

    # Total occurrence records
    n_total = n(),

    # Percentage lacking species identification
    perc_nosp = 100 * n_nosp_records / n_total,

    # Percentage identified to species level
    species_id_rate = 100 * n_records / n_total,

    .groups = "drop"
  ) %>%
  left_join(
    sampled_subcatchments,
    by = c("cluster_id", "continent")
  ) %>%
  left_join(
    total_subcatchments_long,
    by = c("cluster_id", "continent")
  ) %>%
  mutate(
    sampled_subcatchments = replace_na(sampled_subcatchments, 0),
    spatial_coverage =
      100 * sampled_subcatchments / total_subcatchments
  )

# Create final output table ----------------------------------

# Table ordered first by cluster_id and then by sampling effort.

stat_table_cluster_continent <- cluster_continent_summary %>%
  arrange(cluster_id,desc(n_total)) %>%
  select(cluster_id, continent, n_total, species_id_rate,  spatial_coverage) %>%
  rename(total_records = n_total)

# Save -------------------------------------------------------
fwrite(stat_table_cluster_continent,
  "/data/mschuerz/clustering_global/world_v2/cluster_continent_epto_sampling_effort_20260714.csv", 
  row.names = FALSE, col.names = TRUE
)
