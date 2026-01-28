# Set working directory
setwd('/home/mueblacker/Documents/Glowabio/Data/clustering_global')

# Functions ---------------------------------------------------------------

# Function to check if the required packages are installed and to load the library
usePackage <- function(p){
  if (!is.element(p, installed.packages()[,1])) install.packages(p, dep = TRUE)
  library(p, character.only = TRUE)
}

# Libraries ---------------------------------------------------------------

usePackage("data.table")
usePackage("tidyverse")
usePackage("ggplot2")


idx_path <- '/home/mueblacker/Documents/Glowabio/Data/clustering_global'

# Input data --------------------------------------------------------------
wss_path <- list.files("/home/mueblacker/Documents/Glowabio/Data/clustering_global/world/wss_0.25_seed3",
                   pattern = ".csv$", full.names = TRUE)
wss_1 <- fread(wss_path[1])
#wss_2 <- fread(wss_path[2])

wss <- wss_1 #%>% 
  #add_row(wss_2) %>% 
  #arrange(k)
#
sil_path <- list.files("/home/mueblacker/Documents/Glowabio/Data/clustering_global/world/sil_0.25_seed3",
                       pattern = ".csv$", full.names = TRUE)
sil_1 <- fread(sil_path[1])
#sil_2 <- fread(sil_path[2])

sil <- sil_1 #%>% 
  #add_row(sil_2) %>% 
 # arrange(k)

#Join tables
idx_tbl <- inner_join(wss, sil, by = 'k') %>% 
  pivot_longer(., cols = wss:sil, names_to = 'indices')

# Labeller for plot -------------------------------------------------------

# Labeller for indices
idx_name <- c(sil = "Silhouette Score", 
              wss = "Total Within Sum of Squares")



# Create plot with all calculated indices ---------------------------------

idx_plot <-  ggplot(idx_tbl, aes(x = k, y = value)) +
             geom_line() +
             geom_point()+
             facet_wrap(.~indices, scales = "free", labeller = labeller(indices = idx_name))+
             #scale_x_continuous(breaks = x_breaks, minor_breaks = 1:max(idx_tbl$k)) +
             #geom_point(data = bst_ncl, aes(x = k, y = values), col = "red", size = 2) +
             theme_bw() +
             theme(axis.title.y = element_blank(),
                  strip.placement = "outside",
                  strip.background=element_blank(),
                  strip.text.y = element_text(size = rel(1.1))) +
             xlab("Number of clusters") 

# Create filenames --------------------------------------------------------s

filename_idx <- paste0("indices_global_0.25_seed3.png")


# Save output -------------------------------------------------------------

ggsave(filename_idx, plot = idx_plot, device = "png", path = idx_path, width= 20, 
       height = 15, units = "cm", dpi = 300)


# Exit R ------------------------------------------------------------------

quit(save = "no")
