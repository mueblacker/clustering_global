#!/bin/bash
#SBATCH --job-name=select_uncorr
#SBATCH -p day
#SBATCH -n 1 -c 1 -N 1
#SBATCH -t 0:10:00
#SBATCH -o /scratch/stdout/select_uncorr_envVar.%A_%a.out
#SBATCH -e /scratch/stderr/select_uncorr_envVar.%A_%a.err
#SBATCH --mem-per-cpu=5G


module load R/4.4.1-foss-2022b

R --slave -f /my_directory/code/clustering_global/02_select_uncorr_envVar.R

exit
