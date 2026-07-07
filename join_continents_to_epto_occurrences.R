#  Add sub-region to sub-catchments with occurrence data

# Load libraries ----------------------------------------------

library(dplyr)
library(tidyr)
library(data.table)
library(arrow)


# Load occurrence data ----------------------------------------

epto <- fread(
  "/mnt/shared/mschuerz/Global_EPTO_database_clean_species_cluster_id.csv"
)
# Load sub-catchment spatial information ----------------------

tiles <- open_dataset(
  "/data/mschuerz/clustering_global/sub_catchment_country_parquet",
  format = "parquet"
)

subcatchment_info <- tiles %>%
  select(subc_id,sub_region_name,pixel_count) %>%
  filter(subc_id %in% unique(epto$subcatchment_ID)) %>%
  collect()


# Assign dominant sub-region to sub-catchments --------------

# Some sub-catchments overlap multiple UN sub-regions.
# The dominant sub-region is assigned based on the largest
# number of pixels belonging to each region.

subcatchment_info <- subcatchment_info %>%
  group_by(subc_id, sub_region_name) %>%
  summarise(pixel_count = sum(pixel_count),
    .groups = "drop") %>%
  group_by(subc_id) %>%
  slice_max(order_by = pixel_count, n = 1, with_ties = FALSE) %>%
  ungroup()


# Prepare occurrence dataset ---------------------------------

# Join spatial information and collapse UN sub-regions into
# broader continental categories.

sp_data <- epto %>%
  left_join(subcatchment_info, by = c("subcatchment_ID" = "subc_id")) %>%
  filter(!is.na(cluster_id), !is.na(sub_region_name)) %>%
  mutate(continent = case_when(

      sub_region_name %in% c(
        "Northern Europe",
        "Southern Europe",
        "Eastern Europe",
        "Western Europe"
      ) ~ "Europe",

      sub_region_name %in% c(
        "Eastern Asia",
        "Southern Asia",
        "South-eastern Asia",
        "Western Asia",
        "Central Asia"
      ) ~ "Asia",

      sub_region_name == "Northern America" ~ "North America",

      sub_region_name == "Latin America and the Caribbean" ~
        "South America",

      sub_region_name %in% c(
        "Sub-Saharan Africa",
        "Northern Africa"
      ) ~ "Africa",

      sub_region_name %in% c(
        "Melanesia",
        "Polynesia",
        "Micronesia",
        "Australia and New Zealand"
      ) ~ "Oceania",

      TRUE ~ "Other"
    ))

# Save ----------------------------------------------------

fwrite(sp_data,
  "/mnt/shared/mschuerz/Global_EPTO_database_clean_species_cluster_id_sub_region.csv", 
  row.names = FALSE, col.names = TRUE
)