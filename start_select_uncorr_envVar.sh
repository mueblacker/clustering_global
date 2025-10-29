#!/bin/bash
#SBATCH --job-name=select_uncorr
#SBATCH -p scavenge
#SBATCH -n 1 -c 1 -N 1
#SBATCH -t 0:10:00
#SBATCH -o /vast/palmer/scratch/sbsc/mu78/stdout/select_uncorr_envVar.%A_%a.out
#SBATCH -e /vast/palmer/scratch/sbsc/mu78/stderr/select_uncorr_envVar.%A_%a.err
#SBATCH --mem-per-cpu=5G


module load R/4.4.1-foss-2022b

R --slave -f /gpfs/gibbs/project/sbsc/mu78/code/clustering_global/select_uncorr_envVar.R

exit
