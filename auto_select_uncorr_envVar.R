# Set working directory
setwd("/home/mu78/palmer_scratch/clustering_global")

# Functions ---------------------------------------------------------------

# Function to check if the required packages are installed and to load the library
usePackage <- function(p){
  if (!is.element(p, installed.packages()[,1])) install.packages(p, dep = TRUE)
  library(p, character.only = TRUE)
}


# Libraries ---------------------------------------------------------------

# Load libraries
usePackage("dplyr")
usePackage("data.table")

# Load data  -------------------------------------------------------------

# Path to correlation dataset
path <- list.files("/home/mu78/palmer_scratch/clustering_global/south_america/correlation",
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

fwrite(uncorr_enVar, "/home/mu78/palmer_scratch/clustering_global/south_america/correlation/uncorr_envVar_south_america.csv")


# Exit R ------------------------------------------------------------------

quit(save ="no")



