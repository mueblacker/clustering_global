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

epto <- fread(
  "/mnt/shared/mschuerz/Global_EPTO_database_clean_species_cluster_id_sub_region.csv"
)

sp_data <- epto %>%
    filter(!is.na(cluster_id))

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
  )


# Create final output table ----------------------------------

# Table ordered first by cluster_id and then by sampling effort.

stat_table_cluster_continent <- cluster_continent_summary %>%
  arrange(cluster_id,desc(n_total)) %>%
  select(cluster_id, continent, n_total, n_records, species_id_rate)

# Save -------------------------------------------------------
fwrite(stat_table_cluster_continent,
  "/mnt/shared/mschuerz/cluster_continent_epto_sampling_effort_20260707.csv", 
  row.names = FALSE, col.names = TRUE
)
