# Set working directory
setwd("/my/working/directory/data")

# Functions ---------------------------------------------------------------

# Function to check if the required packages are installed and to load the library
usePackage <- function(p){
  if (!is.element(p, installed.packages()[,1])) install.packages(p, dep = TRUE)
  library(p, character.only = TRUE)
}


# Libraries ---------------------------------------------------------------

# Load libraries
usePackage("data.table")
usePackage("tidyverse")

# Select basin and dataset ------------------------------------------------

# Define computational unit
cunit <- Sys.getenv(c("CUNIT"))
# Define basin ID
basinID <- Sys.getenv(c("BID"))
# Define the set of variables
vset01 <- Sys.getenv(c("VSET"))
# Define the set of variables
vset02 <- Sys.getenv(c("VSET2"))

# Directories -------------------------------------------------------------

# Path to environmental variable dataset
vset01_path <- paste0("/my/working/directory/data/partitional_clustering/",
                     vset01, "/basin_", cunit, "_", basinID)

rf_path <- paste0(vset01_path, "/vimp")

# Path to set02uncorr
vset02_path <- paste0("/my/working/directory/data/partitional_clustering/",
                      vset02)
if(!dir.exists(vset02_path)) dir.create(vset02_path)

basin_path <- paste0("/my/working/directory/data/partitional_clustering/",
                      vset02, "/basin_", cunit, "_", basinID)
if(!dir.exists(basin_path)) dir.create(basin_path)


# Input data --------------------------------------------------------------

basin_sc <- fread(paste0(vset01_path, "/basin_envVar_sc_", cunit, "_", 
                         basinID, ".csv"))

sman_corr_matrix <- fread(paste0(vset01_path, "/correlation/spearman_corr_", 
                                 cunit, "_", basinID , "_", vset01, ".csv"))

envVar_ranking <- fread(paste0(rf_path, "/envVar_ranking_", cunit, "_", 
                               basinID , ".csv"))


# Remove correlated variables ---------------------------------------------

ranking <- envVar_ranking$variable

# For Spearman's rank correlation
# Change NAs into zeros
sman_corr_matrix <- sman_corr_matrix %>% 
  mutate_all(~ifelse(is.na(.), 0, .))


for(var in ranking){
  
  # Check if variable is available within the matrix
  c <- var %in%  sman_corr_matrix$term
  
  if(c==TRUE){
  uncorr <- abs(sman_corr_matrix[[var]])<=0.7  
  sman_corr_matrix <- sman_corr_matrix[uncorr,]
  variables <- sman_corr_matrix$term
  sman_corr_matrix <- sman_corr_matrix %>% 
    select(term, all_of(variables))
  }

}

# List of uncorrelated variables 
sman_uncorr_enVar <- as.data.table(sman_corr_matrix$term)


# Selection output ---------------------------------------------------------

fwrite(sman_uncorr_enVar, paste0(vset01_path, "/correlation/sman_uncorr_envVar_", 
                                 cunit,"_", basinID,"_", vset01, ".csv"))


# Select uncorrelated variables -------------------------------------------

variables <- sman_corr_matrix$term

basin_uncorr_var <- basin_sc %>% 
  select(CompUnit, basinID, subcID, all_of(variables))


# Save output -------------------------------------------------------------

fwrite(basin_uncorr_var, paste0(basin_path, 
				"/basin_envVar_sc_", cunit, "_", basinID, "_", vset02, ".csv"))


# Exit R ------------------------------------------------------------------

quit(save ="no")



