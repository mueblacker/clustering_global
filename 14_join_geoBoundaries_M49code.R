# =========================================================================
# Script to merge United Nations Statistics Division (UNSD) standard country
# or area codes (M49) with the geoBoundaries country-level spatial dataset.
#
# The script also assigns broad UN regions and sub-regions to territories,
# disputed areas, and other geoBoundaries features that are not directly
# included in the UNSD M49 reference table.
# =========================================================================

# Libraries ---------------------------------------------------------------
library(data.table)
library(sf)
library(dplyr)

# Load data ---------------------------------------------------------------

# Read the UNSD M49 methodology/reference table
unm49 <- fread("/my_directory/data/m49/UNSD_Methodology.csv")

# Read the geoBoundaries country/area boundary dataset from a GeoPackage file
geoBound <- read_sf("/my_directory/data/m49/geoBoundariesCGAZ_ADM0.gpkg")


# Merge geoBoundaries geometries and UNSD M49 attributes-------------------

# Create a combined spatial dataset containing geoBoundaries geometries and
# UNSD M49 attributes
 # Assign broad UN region names to geoBoundaries features that do not have
  # a direct M49 region and sub-region assignment after the join.
df <- unm49 %>%
  mutate(shapeGroup = `ISO-alpha3 Code`) %>%
  left_join(geoBound,., by="shapeGroup") %>%
  select(
    shapeGroup, 
    shapeName, 
    `Region Name`, 
    `Region Name`, 
    `Sub-region Name`, 
    `Country or Area`, 
    `ISO-alpha3 Code`, 
    `M49 Code`, 
    geom) %>%
  rename(geoBoundaries_names = shapeName,
         region_name = `Region Name`,
         sub_region_name = `Sub-region Name`,
         country_or_area = `Country or Area`,
         iso_alpha3_code = `ISO-alpha3 Code`,
         m49_code = `M49 Code`) %>%
  mutate(region_name = case_when(
    geoBoundaries_names %in% c("Kosovo", "Dragonja") ~ "Europe",
    
    geoBoundaries_names %in% c(
      "Taiwan", "Aksai Chin", "CH-IN", "Demchok", "Dramana-Shakatoe", 
      "Gaza Strip", "Kalapani", "Siachen-Saltoro", "Liancourt Rocks", 
      "No Man's Land", "Paracel Is", "Senkakus", "Spratly Is", "West Bank"
    ) ~ "Asia",
    
    geoBoundaries_names %in% c("Abyei", "Koualou", "Sanafir & Tiran Is.") ~ "Africa",
    
    geoBoundaries_names %in% c("Falkland Islands (UK)", "Isla Brasilera") ~ "Americas"
  )) %>%
  mutate(sub_region_name = case_when(
    geoBoundaries_names %in% c("Kosovo", "Dragonja") ~ "Southern Europe",
    
    geoBoundaries_names %in% c("Taiwan", "Liancourt Rocks", "Senkakus") ~ "Eastern Asia",
    
    geoBoundaries_names %in% c("Abyei", "Koualou") ~ "Sub-Saharan Africa",
    
    geoBoundaries_names %in% c(
      "Aksai Chin", "CH-IN", "Demchok", "Dramana-Shakatoe", 
      "Kalapani", "Siachen-Saltoro"
    ) ~ "Southern Asia",
    
    geoBoundaries_names %in% c("Falkland Islands (UK)", "Isla Brasilera") ~ "Latin America and the Caribbean",
    
    geoBoundaries_names %in% c("Gaza Strip", "No Man's Land", "West Bank") ~ "Western Asia",
    
    geoBoundaries_names %in% c("Paracel Is", "Spratly Is") ~ "South-eastern Asia",
    
    geoBoundaries_names == "Sanafir & Tiran Is." ~ "Northern Africa"
  ))

# Convert the spatial data object to a regular data frame and remove the
# geometry column before writing a non-spatial CSV output
df <- as.data.frame(test) %>% 
    select(-geom)

# Save output table -----------------------------------------------------------

# Write the final non-spatial data frame to a CSV file
write.csv(n, "/my_directory/data/regions_20260603.csv", row.names = FALSE)

