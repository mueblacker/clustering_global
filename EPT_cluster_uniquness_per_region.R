
# Libraries --------------------------------------------------

library(dplyr)
library(tidyr)
library(data.table)
library(arrow)


# Load data --------------------------------------------------

epto <- fread("/mnt/shared//Global_EPTO_database_clean_species_cluster_id.csv")

tiles <- open_dataset(
  "/data/mschuerz/clustering_global/sub_catchment_continent_parquet",
  format = "parquet"
)

subcatchment_continent <- tiles %>%
  filter(subc_id %in% unique(epto$subcatchment_ID)) %>%
  select(subc_id, continent) %>%
  collect()


# Join with sp data
epto <- epto %>%
  filter(!is.na(cluster_id)) %>%
  left_join(subcatchment_continent, by = c("subcatchment_ID" = "subc_id"))

# Select taxon -----------------------------------------------

sp_data <- epto %>%
    mutate(clean_species = ifelse(grepl("sp\\.", clean_species), "", clean_species),
            taxon = clean_species) 
   

# Sampling effort --------------------------------------------

records_summary <- sp_data %>%
  group_by(cluster_id, continent) %>%
  summarise(
    n_records = sum(clean_species != ""),
    n_nosp_records = sum(clean_species == ""),
    n_total = n(),
    perc_nosp = 100 * n_nosp_records / n_total,
    species_id_rate = 100 * n_records / n_total,
    .groups = "drop"
  )

# Aggregate occurrences to cluster level ---------------------

cluster_taxa <- sp_data %>%
   filter(clean_species != "") %>%
  distinct(cluster_id, continent, taxon)

cluster_matrix <- cluster_taxa %>%
  mutate(
    presence = 1,
    cluster_region = paste(cluster_id, continent, sep = "_")
  ) %>%
  pivot_wider(
    id_cols = c(cluster_region, cluster_id, continent),
    names_from = taxon,
    values_from = presence,
    values_fill = 0
  )

cluster_info <- cluster_matrix %>%
  select(cluster_region, cluster_id, continent)

comm <- cluster_matrix %>%
  select(-cluster_region, -cluster_id, -continent)

comm <- as.data.frame(comm)
rownames(comm) <- cluster_info$cluster_region

richness <- rowSums(comm)

taxon_occupancy <- colSums(comm)

weights <- 1 / taxon_occupancy

WE <- apply(comm, 1, function(x) sum(weights[x == 1]))

CWE <- WE / richness

restricted_taxa <- names(taxon_occupancy[taxon_occupancy <= 1])

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
  left_join(., records_summary, by = c("cluster_id", "continent"))


cluster_summary <- cluster_summary %>%
  mutate(
    richness_per_records = richness/ n_records,
    richness_per_100_records = richness / n_total * 100,
    WE_per_100_records = WE / n_records * 100
  )

model <- lm(richness ~ log10(n_total), data = cluster_summary)
model_we <- lm(WE ~ log10(n_total), data = cluster_summary)

cluster_summary <- cluster_summary %>%
  mutate(
    richness_residual = residuals(model),
    WE_residual = residuals(model_we)
  ) 

stat_table <- cluster_summary %>%
  select(n_total, species_id_rate, richness, richness_per_100_records, richness_residual, restricted_taxa_prop, WE, WE_residual)
