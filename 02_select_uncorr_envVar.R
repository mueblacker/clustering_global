# =========================================================================
# Progressively remove highly correlated variables
# =========================================================================

# Set working directory
setwd("/my_directory/clustering_global")

# Functions ---------------------------------------------------------------

# Function to check if the required packages are installed and to load the library
usePackage <- function(p){
  if (!is.element(p, installed.packages()[,1])) install.packages(p, dep = TRUE)
  library(p, character.only = TRUE)
}


# Libraries ---------------------------------------------------------------

# Load libraries
usePackage("data.table")
usePackage("dplyr")


# Load data  -------------------------------------------------------------

# Path to the results of the correlation analysis 
path <- list.files("/my_directory/data/clustering_global/l_fhc/correlation",
                   pattern = ".csv$", full.names = TRUE)

corr_matrix <- fread(path[1], header = TRUE)

corr_matrix$term <- names(corr_matrix)

# Remove correlated variables ---------------------------------------------
 
ranking = c('elev', 'flow_ltm', 'spi', 'sti', 'cti', 'flowpos', 'bio1',
	          'bio2', 'bio3', 'bio4', 'bio5', 'bio6', 'bio7', 'bio8',
            'bio9', 'bio10', 'bio11', 'bio12', 'bio13', 'bio14', 'bio15', 'bio16', 
            'bio17', 'bio18', 'bio19', 'gradient', 'cum_length', 'out_dist', 'sinusoid',
            'c10', 'c20', 'c30', 'c40', 'c50', 'c60', 'c70',
            'c80', 'c90', 'c100', 'c110', 'c120', 'c130', 'c140', 'c150', 'c160', 'c170', 'c180',
            'c190', 'c200', 'c210', 'c220') 

# ranking <- corr_matrix$term


# Change NAs into zeros
corr_matrix <- corr_matrix %>% 
  mutate_all(~ifelse(.x == 1, 0, .))



# Loop through variables in order of importance/ranking
for (var in ranking) {
  
  # Check whether the variable is still available in the correlation matrix
  variable_exists <- var %in% corr_matrix$term
  
  if (variable_exists) {
    
    # Keep variables whose absolute correlation with `var`
    # is no greater than the threshold of 0.85
    keep_rows <- abs(corr_matrix[[var]]) <= 0.85
    
    # Remove highly correlated variables from the matrix
    corr_matrix <- corr_matrix[keep_rows, ]
    
    # Get the names of the variables that remain
    remaining_variables <- corr_matrix$term
    
    # Keep only the term column and columns for remaining variables
    corr_matrix <- corr_matrix %>%
      dplyr::select(term, dplyr::all_of(remaining_variables))
  }
}


# List of uncorrelated variables 
uncorr_enVar <- as.data.table(corr_matrix$term)


# Selection output ---------------------------------------------------------

fwrite(uncorr_enVar, paste0("/my_directory/data/clustering_global/l_fhc/correlation/uncorr_envVar_lfhc_085.csv"))


# Exit R ------------------------------------------------------------------

quit(save = "no")
