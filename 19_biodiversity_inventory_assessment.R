# =========================================================================
# Biodiversity inventory assessment of freshwater insects
#
# Spatial unit: cluster_id
#
# Calculates:
# - sampling effort and spatial coverage
# - observed species richness and Chao2 estimated richness
# - weighted endemism (WE) and corrected weighted endemism (CWE)
# - restricted-taxa metrics
# - sampling-effort-normalised diversity metrics
# - residuals from richness/WE models accounting for sampling effort
# ==========================================================================


# Load libraries ----------------------------------------------------------

library(dplyr)
library(tidyr)
library(data.table)
library(arrow)


# Load occurrence data ----------------------------------------------------

# Read the cleaned and spatially corrected EPTO occurrence dataset.
epto <- fread(
  "/my_directory/data/Global_EPTO_database_corrected_continent_20260804.csv"
)

# Keep records with an assigned cluster and prepare species names for analysis.
#
# Records that are only identified as "sp." or appear to be uncertain
# species-level names are assigned an empty species name. These records remain
# available for sampling-effort calculations but are excluded from species
# richness and endemism calculations.
sp_data <- epto %>%
    filter(!is.na(cluster_id)) %>%
    
    # Create the taxon column used in the cluster-by-species matrix.
    mutate(
      clean_species = ifelse(
        grepl("sp\\.", clean_species),
        "",
        clean_species
      ),
      clean_species = ifelse(
        grepl("^[^_]+_[^_,]+,_[0-9]{4}$", species),
        "",
        clean_species
      ),
      taxon = clean_species
    )


# Load cluster size -------------------------------------------------------

# Read the number of sub-catchments contained in each cluster.
subcatchments <- fread(
  "/my_directory/data/clustering_global/l_fhc/cluster_size_count_20260714.csv"
)


# Calculate sampling effort -----------------------------------------------

# Summarise occurrence-record counts and species-level identification rates
# separately for each cluster.
records_cluster <- sp_data %>%
  group_by(cluster_id) %>%
  summarise(

    # Number of records identified to species level.
    n_records = sum(clean_species != ""),

    # Number of records without a usable species-level identification.
    n_nosp_records = sum(clean_species == ""),

    # Total number of occurrence records in the cluster.
    n_total = n(),

    # Percentage of records identified to species level.
    species_id_rate = 100 * n_records / n_total,

    .groups = "drop"
  )


# Calculate spatial coverage ----------------------------------------------

# Calculate the proportion of sub-catchments sampled in each cluster.
#
# - Count distinct sampled sub-catchments per cluster.
# - Join the total number of sub-catchments in each cluster.
# - Calculate sampled sub-catchments as a percentage of the cluster total.
coverage <- sp_data %>%
  filter(!is.na(subcatchment_ID)) %>%
  distinct(cluster_id, subcatchment_ID) %>%
  count(cluster_id, name = "sampled_subcatchments") %>%
  left_join(subcatchments, by = "cluster_id") %>%
  mutate(
    spatial_coverage =
      100 * sampled_subcatchments / total_subcatchments
  )


# Create incidence matrix and Chao2 estimates -----------------------------

# Create sub-catchment-level species incidences.
# A species is counted once per sub-catchment, regardless of how many
# occurrence records it has within that sub-catchment.
incidence <- sp_data %>%
  filter(clean_species != "") %>%
  distinct(cluster_id, subcatchment_ID, taxon)

# Calculate observed richness and Chao2 estimated richness for each cluster.
#
# - `observed`: number of observed taxa in the cluster.
# - `Q1`: number of taxa occurring in one sampled sub-catchment.
# - `Q2`: number of taxa occurring in two sampled sub-catchments.
# - `chao2`: estimated total richness based on incidence data.
# - `completeness`: observed richness divided by estimated richness.
# - `prop_singletons`: proportion of observed taxa found in only one
#   sampled sub-catchment.
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

    # Use the standard Chao2 estimate when doubletons are available.
    # Use the bias-corrected alternative when no doubletons occur.
    chao2 = case_when(
      Q2 > 0 ~ observed + (Q1^2) / (2 * Q2),
      TRUE   ~ observed + (Q1 * (Q1 - 1)) / 2
    ),

    completeness = observed / chao2,

    prop_singletons = Q1 / observed,

    .groups = "drop"
  )

# Save the Chao2 completeness results as a separate table.
write.csv(
  chao_table,
  "/my_directory/data/clustering_global/l_fhc/chao2_20260828.csv",
  row.names = FALSE
)


# Create cluster-level community matrix -----------------------------------

# Retain unique cluster-by-taxon combinations for records identified
# to species level.
cluster_taxa <- sp_data %>%
  filter(clean_species != "") %>%
  distinct(cluster_id, taxon)

# Convert the cluster-by-taxon data into a presence/absence matrix.
#
# Rows represent clusters and columns represent taxa:
# - 1 = taxon occurs in the cluster
# - 0 = taxon is not observed in the cluster
cluster_matrix <- cluster_taxa %>%
  mutate(presence = 1) %>%
  pivot_wider(
    id_cols = cluster_id,
    names_from = taxon,
    values_from = presence,
    values_fill = 0
  )

# Extract the numeric community matrix used for biodiversity calculations.
# Cluster IDs are stored as row names rather than as a matrix column.
comm <- cluster_matrix %>%
  select(-cluster_id) %>%
  as.data.frame()

rownames(comm) <- cluster_matrix$cluster_id


# Calculate biodiversity metrics ------------------------------------------

# Calculate observed species richness as the number of taxa per cluster.
richness <- rowSums(comm)

# Calculate the number of clusters occupied by each taxon.
taxon_occupancy <- colSums(comm)


# Weighted Endemism -------------------------------------------------------

# Assign each taxon a weight equal to the inverse of its cluster occupancy.
# Taxa present in fewer clusters receive a larger endemism weight.
weights <- 1 / taxon_occupancy

# Calculate Weighted Endemism (WE) for every cluster by summing the weights
# of all taxa present in that cluster.
WE <- apply(
  comm,
  1,
  function(x) {
    sum(weights[x == 1])
  }
)


# Corrected Weighted Endemism ----------------------------------------------

# Calculate Corrected Weighted Endemism (CWE) by dividing WE by richness.
# This accounts for differences in the number of observed taxa per cluster.
CWE <- WE / richness


# Restricted taxa metrics -------------------------------------------------

# Define restricted taxa as those observed in only one cluster.
restricted_taxa <- names(taxon_occupancy[taxon_occupancy <= 1])

# Count the number of restricted taxa present in each cluster.
restricted_counts <- apply(
  comm[, restricted_taxa, drop = FALSE],
  1,
  sum
)

# Calculate the proportion of each cluster's taxa that are restricted.
restricted_prop <- restricted_counts / richness


# Combine biodiversity and sampling metrics --------------------------------

# Combine biodiversity, sampling effort, spatial coverage, and Chao2 results
# into a single cluster-level summary table.
cluster_summary <- data.frame(
    cluster_id = cluster_matrix$cluster_id,
    richness = richness,
    WE = WE,
    CWE = CWE,
    restricted_taxa_n = restricted_counts,
    restricted_taxa_prop = restricted_prop
  ) %>%
  left_join(records_cluster, by = "cluster_id") %>%
  left_join(coverage, by = "cluster_id") %>%
  left_join(chao_table, by = "cluster_id") %>%
  mutate(
    
    # Standardise richness and WE by the number of occurrence records.
    richness_per_100_records = richness / n_total * 100,
    WE_per_100_records = WE / n_total * 100
  )


# Correct biodiversity metrics for sampling effort ------------------------

# Fit a model describing the expected relationship between observed richness
# and the log10 number of occurrence records.
model_richness <- lm(
  richness ~ log10(n_total),
  data = cluster_summary
)

# Fit a similar model for Weighted Endemism.
model_WE <- lm(
  WE ~ log10(n_total),
  data = cluster_summary
)

# Add model residuals to the cluster summary.
#
# Positive residuals indicate richness or WE higher than expected given
# sampling effort; negative residuals indicate lower-than-expected values.
cluster_summary <- cluster_summary %>%
  mutate(
    richness_residual = residuals(model_richness),
    WE_residual = residuals(model_WE)
  )


# Create final output table -----------------------------------------------

# Select the final cluster-level metrics, rename selected columns for clarity,
# and sort clusters from most to fewest total occurrence records.
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
  rename(
    total_records = n_total,
    observed_richness = richness,
    SLIR = species_id_rate,
    prop_single_subc_species = prop_singletons
  ) %>%
  arrange(desc(total_records))


# Save results ------------------------------------------------------------

# Save the full cluster-level biodiversity and sampling-statistics table.
fwrite(
  stat_table_cluster,
  "/my_directory/data/clustering_global/l_fhc/cluster30_epto_statistics_20260828.csv", 
  row.names = FALSE,
  col.names = TRUE
)

# Create a smaller table containing selected indicators for reporting or maps.
selected <- stat_table_cluster %>%
  select(
    cluster_id,
    total_records,
    spatial_coverage,
    SLIR,
    observed_richness,
    completeness,
    CWE,
    restricted_taxa_n
  )

# Save the selected cluster-level statistics table.
fwrite(
  selected,
  "/my_directory/data/clustering_global/l_fhc/cluster30_epto_statistics_selected_20260828.csv", 
  row.names = FALSE,
  col.names = TRUE
)