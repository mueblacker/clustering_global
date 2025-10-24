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


# Load data  -------------------------------------------------------------

# Path to correlation dataset
path <- list.files("/home/mueblacker/Documents/Glowabio/Data/clustering_global/correlation",
                   pattern = ".csv$", full.names = TRUE)

corr_matrix <- fread(path, header = TRUE)

corr_matrix$term <- names(corr_matrix)

# Remove correlated variables ---------------------------------------------

ranking <- corr_matrix$term

# For Spearman's rank correlation
# Change NAs into zeros
corr_matrix <- corr_matrix %>% 
  mutate_all(~ifelse(.x == 1, 0, .))


for(var in ranking){
  
  # Check if variable is available within the matrix
  c <- var %in%  corr_matrix$term
  
  if(c==TRUE){
  uncorr <- abs(corr_matrix[[var]])<=0.7  
  corr_matrix <- corr_matrix[uncorr,]
  variables <- corr_matrix$term
  corr_matrix <- corr_matrix %>% 
    select(term, all_of(variables))
  }

}

# List of uncorrelated variables 
uncorr_enVar <- as.data.table(corr_matrix$term)


# Selection output ---------------------------------------------------------

fwrite(uncorr_enVar, paste0(vset01_path, "/correlation/sman_uncorr_envVar_", 
                                 cunit,"_", basinID,"_", vset01, ".csv"))


# Exit R ------------------------------------------------------------------

quit(save ="no")



