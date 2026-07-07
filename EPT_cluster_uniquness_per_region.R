
# Libraries --------------------------------------------------

library(dplyr)
library(tidyr)
library(data.table)
library(arrow)


# Load data --------------------------------------------------

epto <- fread("/mnt/shared/mschuerz/Global_EPTO_database_clean_species_cluster_id.csv")

tiles <- open_dataset(
  "/data/mschuerz/clustering_global/sub_catchment_country_parquet",
  format = "parquet"
)

subcatchment_continent <- tiles %>%
  select(subc_id, sub_region_name, pixel_count) %>%
  filter(subc_id %in% unique(epto$subcatchment_ID)) %>%
  collect()

#Determine dominant continent

subcatchment_continent <- subcatchment_continent %>%
  group_by(subc_id, sub_region_name) %>%
  summarise(pixel_count = sum(pixel_count), .groups = "drop") %>%
  group_by(subc_id) %>%
  slice_max(pixel_count, n = 1, with_ties = FALSE) %>%
  ungroup()



# Join with sp data
epto <- epto %>%
  left_join(
    subcatchment_continent,
    by = c("subcatchment_ID" = "subc_id")
  )

# Select taxon -----------------------------------------------

sp_data <- epto %>%
  mutate(taxon = genus) %>%
  filter(!order == "Odonata") %>%
  na.omit() 

# Sampling effort --------------------------------------------

records <- sp_data %>%
    group_by(cluster_id, sub_region_name) %>%
    mutate(n = 1) %>%
    summarise(n_records = sum(n))


# Aggregate occurrences to cluster level ---------------------

cluster_taxa <- sp_data %>%
  distinct(cluster_id, sub_region_name, taxon)

cluster_matrix <- cluster_taxa %>%
  mutate(
    presence = 1,
    cluster_region = paste(cluster_id, sub_region_name, sep = "_")
  ) %>%
  pivot_wider(
    id_cols = c(cluster_region, cluster_id, sub_region_name),
    names_from = taxon,
    values_from = presence,
    values_fill = 0
  )

cluster_info <- cluster_matrix %>%
  select(cluster_region, cluster_id, sub_region_name)

comm <- cluster_matrix %>%
  select(-cluster_region, -cluster_id, -sub_region_name)

comm <- as.data.frame(comm)
rownames(comm) <- cluster_info$cluster_region

richness <- rowSums(comm)

taxon_occupancy <- colSums(comm)

weights <- 1 / taxon_occupancy

WE <- apply(comm, 1, function(x) sum(weights[x == 1]))

CWE <- WE / richness

restricted_taxa <- names(taxon_occupancy[taxon_occupancy <= 2])

restricted_counts <- apply(
  comm[, restricted_taxa, drop = FALSE],
  1,
  sum
)

restricted_prop <- restricted_counts / richness

cluster_summary <- cluster_info %>%
  mutate(
    richness = richness,
    WE = WE,
    CWE = CWE,
    restricted_taxa_n = restricted_counts,
    restricted_taxa_prop = restricted_prop
  ) %>%
  arrange(desc(CWE)) %>%
  left_join(., records, by = c("cluster_id", "sub_region_name"))


cluster_summary <- cluster_summary %>%
  mutate(
    richness_per_effort = richness/ n_records,
    WE_per_effort = WE / n_records
  )