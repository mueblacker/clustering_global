
# Libraries --------------------------------------------------

library(dplyr)
library(tidyr)
library(data.table)

# Load data --------------------------------------------------

epto <- fread("/mnt/shared/mschuerz/Global_EPTO_database_clean_species_cluster_id.csv")


# Select taxon -----------------------------------------------

sp_data <- epto %>%
  mutate(taxon = genus) %>%
  filter(!order == "Odonata") %>%
  na.omit() 

# Sampling effort --------------------------------------------

records <- sp_data %>%
    group_by(cluster_id) %>%
    mutate(n = 1) %>%
    summarise(n_records = sum(n))

# Aggregate occurrences to cluster level ---------------------

cluster_taxa <- sp_data %>%
  distinct(cluster_id, taxon)


# Cluster × Taxon presence matrix ----------------------------

cluster_matrix <- cluster_taxa %>%
  mutate(presence = 1) %>%
  pivot_wider(
    names_from = taxon,
    values_from = presence,
    values_fill = 0
  )

cluster_ids <- cluster_matrix$cluster_id

comm <- cluster_matrix %>%
  select(-cluster_id)

comm <- as.data.frame(comm)
rownames(comm) <- cluster_ids


# Observed richness ------------------------------------------

richness <- rowSums(comm)

# Taxon occupancy across clusters ----------------------------

taxon_occupancy <- colSums(comm)

# number of clusters occupied by each taxon


# Weighted Endemism (WE) -------------------------------------

weights <- 1 / taxon_occupancy

WE <- apply(comm, 1, function(x) {
  sum(weights[x == 1])
})


# Corrected Weighted Endemism (CWE) --------------------------

CWE <- WE / richness



# Restricted taxa proportion ---------------------------------

restricted_taxa <- names(taxon_occupancy[taxon_occupancy <= 2])

restricted_counts <- apply(
  comm[, restricted_taxa, drop = FALSE],
  1,
  sum
)

restricted_prop <- restricted_counts / richness


# Summary table ----------------------------------------------

cluster_summary <- data.frame(
  cluster_id = cluster_ids,
  richness = richness,
  WE = WE,
  CWE = CWE,
  restricted_taxa_n = restricted_counts,
  restricted_taxa_prop = restricted_prop
)


# Order by CWE -----------------------------------------------

cluster_summary2 <- cluster_summary2 %>%
  arrange(desc(CWE))


# Save results -----------------------------------------------

write_csv(
  cluster_summary,
  "cluster_uniqueness_summary.csv"
)

