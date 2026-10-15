# Cluster-level EPTO analysis
#
# Spatial unit: cluster_id
#
# Calculates:
# - sampling effort
# - observed species richness
# - weighted endemism (WE)
# - corrected weighted endemism (CWE)
# - restricted taxa metrics
# - effort-normalised diversity metrics
# - residuals from richness/WE ~ sampling effort
#


# Load libraries ----------------------------------------------

library(dplyr)
library(tidyr)
library(data.table)
library(arrow)


# Load occurrence data ----------------------------------------

epto <- fread(
  "/mnt/shared/mschuerz/Global_EPTO_database_corrected_continent_20260804.csv"
)

sp_data <- epto %>%
    filter(!is.na(cluster_id)) %>%
    # Species-level name used for the community matrix
     mutate(clean_species = ifelse(grepl("sp\\.", clean_species), "", clean_species),
            clean_species = ifelse(grepl("^[^_]+_[^_,]+,_[0-9]{4}$", species), "", clean_species),
            taxon = clean_species)

     


# Load cluster size --------------------------------------------
subcatchments <- fread(
  "/data/mschuerz/clustering_global/world_v2/cluster_size_count_20260714.csv"
)


# Calculate sampling effort ----------------------------------

# Summarise the number of total records and the proportion
# that could not be identified to species level.

records_cluster <- sp_data %>%
  group_by(cluster_id) %>%
  summarise(

    # Records with species-level identification
    n_records = sum(clean_species != ""),

    # Records without species-level identification
    n_nosp_records = sum(clean_species == ""),

    # Total occurrence records
    n_total = n(),

    # Percentage without species identification
    # perc_nosp = 100 * n_nosp_records / n_total,

    # Percentage identified to species level
    species_id_rate = 100 * n_records / n_total,

    .groups = "drop"
  )

# Calculate spatial coverage ----------------------------------

coverage <- sp_data %>%
  filter(!is.na(subcatchment_ID)) %>%
  distinct(cluster_id, subcatchment_ID) %>%
  count(cluster_id, name = "sampled_subcatchments") %>%
  left_join(subcatchments, by = "cluster_id") %>%
  mutate(
    spatial_coverage =
      100 * sampled_subcatchments / total_subcatchments
  )

# Create indices matrix --------------------------------------

incidence <- sp_data %>%
  filter(clean_species != "") %>%
  distinct(cluster_id, subcatchment_ID, taxon)

# 
chao_table <-
  incidence %>%
  group_by(cluster_id, taxon) %>%
  summarise(
    incidence = n(),
    .groups = "drop"
  ) %>%
  group_by(cluster_id) %>%
  summarise(

    observed = n(),

    Q1 = sum(incidence == 1),

    Q2 = sum(incidence == 2),

    chao2 = case_when(
      Q2 > 0 ~ observed + (Q1^2) / (2 * Q2),
      TRUE   ~ observed + (Q1 * (Q1 - 1)) / 2
    ),

    completeness = observed / chao2,

    prop_singletons = Q1 / observed,

    .groups = "drop"
  )

write.csv(chao_table, "/data/mschuerz/clustering_global/world_v2/chao2_20260828.csv", row.names = FALSE)

# Create cluster-level community matrix -----------------------

# Only species-level records are included because richness
# and endemism require taxonomic identities.

cluster_taxa <- sp_data %>%
  filter(clean_species != "") %>%
  distinct(cluster_id, taxon)


# Convert occurrence data into presence/absence matrix

cluster_matrix <- cluster_taxa %>%
  mutate(presence = 1) %>%
  pivot_wider(
    id_cols = cluster_id,
    names_from = taxon,
    values_from = presence,
    values_fill = 0
  )


# Extract community matrix for biodiversity calculations

comm <- cluster_matrix %>%
  select(-cluster_id) %>%
  as.data.frame()


rownames(comm) <- cluster_matrix$cluster_id


# Calculate biodiversity metrics ------------------------------

# Number of species per cluster

richness <- rowSums(comm)


# Number of clusters occupied by each taxon

taxon_occupancy <- colSums(comm)


# Weighted Endemism ------------------------------------------

# Rare taxa contribute more strongly because they occur in
# fewer clusters.

weights <- 1 / taxon_occupancy

WE <- apply(comm, 1, function(x) {sum(weights[x == 1])})

# Corrected Weighted Endemism -------------------------------

# Corrects WE by species richness.

CWE <- WE / richness


# Restricted taxa metrics ------------------------------------

# Taxa occurring in only one cluster are considered restricted.

restricted_taxa <- names(taxon_occupancy[taxon_occupancy <=1])

restricted_counts <- apply(
  comm[, restricted_taxa, drop = FALSE], 1, sum)

restricted_prop <- restricted_counts / richness

# Combine biodiversity and sampling metrics ------------------

cluster_summary <- data.frame(
    cluster_id = cluster_matrix$cluster_id,
    richness = richness,
    WE = WE,
    CWE = CWE,
    restricted_taxa_n = restricted_counts,
    restricted_taxa_prop = restricted_prop) %>%
  left_join(records_cluster, by = "cluster_id") %>%
  left_join(coverage, by = "cluster_id") %>%
  left_join(chao_table, by = "cluster_id") %>%
  mutate(richness_per_100_records = richness / n_total * 100,
         WE_per_100_records = WE / n_total * 100)


# Correct biodiversity metrics for sampling effort -----------

# Richness and WE are expected to increase with sampling effort.
# Residuals show clusters that are higher or lower than expected
# given the number of available records.

model_richness <- lm(
  richness ~ log10(n_total),
  data = cluster_summary
)


model_WE <- lm(
  WE ~ log10(n_total),
  data = cluster_summary
)


cluster_summary <- cluster_summary %>%
  mutate(richness_residual = residuals(model_richness),
         WE_residual = residuals(model_WE))


# Create final output table ----------------------------------

# Final table ordered first by cluster_id and then by
# number of total occurrence records.

stat_table_cluster <- cluster_summary %>%
  select(
    cluster_id,

    n_total,

    sampled_subcatchments,
    total_subcatchments,
    spatial_coverage,

    species_id_rate,

    richness,
    chao2,
    completeness,
    prop_singletons,

    richness_per_100_records,
    richness_residual,

    WE,
    CWE,
    WE_per_100_records,
    WE_residual,

    restricted_taxa_n,
    restricted_taxa_prop
  ) %>%
  rename(total_records = n_total,
         detected_richness = richness,
         prop_single_subc_species = prop_singletons) %>%
  arrange(desc(total_records))


# Save -------------------------------------------------------
fwrite(stat_table_cluster,
  "/data/mschuerz/clustering_global/world_v2/cluster30_epto_statistics_20260828.csv", 
  row.names = FALSE, col.names = TRUE
)

selected <- stat_table_cluster %>%
  select(cluster_id, total_records, spatial_coverage, species_id_rate, detected_richness, completeness, CWE, restricted_taxa_n)

fwrite(selected,
  "/data/mschuerz/clustering_global/world_v2/cluster30_epto_statistics_selected_20260828.csv", 
  row.names = FALSE, col.names = TRUE
)
