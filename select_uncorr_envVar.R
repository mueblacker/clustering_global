# Set working directory
setwd("/vast/palmer/scratch/sbsc/mu78/clustering_global")

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

# Path to correlation dataset
path <- list.files("/vast/palmer/scratch/sbsc/mu78/clustering_global/world_wo_lc/correlation",
                   pattern = ".csv$", full.names = TRUE)

corr_matrix <- fread(path[1], header = TRUE)

corr_matrix$term <- names(corr_matrix)

# Remove correlated variables ---------------------------------------------
#'c10', 'c20', 'c30', 'c40', 'c50', 'c60', 'c70',
#'c80', 'c90', 'c100', 'c110', 'c120', 'c130', 'c140', 'c150', 'c160', 'c170', 'c180',
 # 'c190', 'c200', 'c210', 'c220', 
ranking = c('elev', 'flow_ltm', 'spi', 'sti', 'cti', 'flowpos', 'bio1',
	   'bio2', 'bio3', 'bio4', 'bio5', 'bio6', 'bio7', 'bio8',
           'bio9', 'bio10', 'bio11', 'bio12', 'bio13', 'bio14', 'bio15', 'bio16', 
           'bio17', 'bio18', 'bio19', 'gradient', 'cum_length', 'out_dist', 'sinusoid') 

#ranking <- corr_matrix$term

# For Spearman's rank correlation
# Change NAs into zeros
corr_matrix <- corr_matrix %>% 
  mutate_all(~ifelse(.x == 1, 0, .))


for(var in ranking){
  
  # Check if variable is available within the matrix
  c <- var %in%  corr_matrix$term
  
  if(c==TRUE){
  uncorr <- abs(corr_matrix[[var]])<=0.85  
  corr_matrix <- corr_matrix[uncorr,]
  variables <- corr_matrix$term
  corr_matrix <- corr_matrix %>% 
    select(term, all_of(variables))
  }

}

# List of uncorrelated variables 
uncorr_enVar <- as.data.table(corr_matrix$term)


# Selection output ---------------------------------------------------------

fwrite(uncorr_enVar, paste0("/vast/palmer/scratch/sbsc/mu78/clustering_global/world_wo_lc/correlation/uncorr_envVar_world_085.csv"))


# Exit R ------------------------------------------------------------------

quit(save ="no")
