#!/bin/bash
#SBATCH --job-name=sil
#SBATCH --partition=day
#SBATCH --nodes=6                # node count, change as needed
#SBATCH --ntasks-per-node=4      # do not change, leave as 1 task per node
#SBATCH --cpus-per-task=8       # cpu-cores per task, change as needed
#SBATCH --mem 160G               # memory per node, change as needed
#SBATCH --time=04:30:00
#SBATCH -o /vast/palmer/scratch/sbsc/mu78/stdout/sil_sample_0.25_seed3.%A_%a.out
#SBATCH -e /vast/palmer/scratch/sbsc/mu78/stderr/sil_sample_0.25_seed3.%A_%a.err
#SBATCH --mail-type=NONE

# Determine settings for Spark based on requested SLURM resources
TOTALEXEC=$(($SLURM_NNODES * $SLURM_NTASKS_PER_NODE * $SLURM_CPUS_PER_TASK))
EXECMEM=$(($SLURM_MEM_PER_NODE / $SLURM_NTASKS_PER_NODE / 1024))

# These modules are required. You may need to customize the module version
# depending on which cluster you are on.
module load Spark/3.5.1-foss-2022b-Scala-2.13

# Start the Spark instance.
spark-start

# Source spark-env.sh to get useful env variables.
source ${HOME}/.spark-local/${SLURM_JOB_ID}/spark/conf/spark-env.sh

echo "***** Spark cluster is running. Submit jobs to ${SPARK_MASTER_URL}. *****"

# set up SSH tunnel for spark web-interface
node=$(hostname -s)
user=$(whoami)
cluster=$(hostname -f | awk -F"." '{print $2}')
web_port=8080

# print tunneling instructions
echo -e "
MacOS or linux terminal command to create your ssh tunnel:
ssh -N -L ${web_port}:${node}:${web_port} ${user}@${cluster}.ycrc.yale.edu

Forwarded port:same as remote port
Remote server: ${node}
Remote port: ${web_port}
SSH server: ${cluster}.hpc.yale.edu
SSH login: $user
SSH port: 22

Use a Browser on your local machine to go to:
localhost:${web_port} 
"

date

# Customize the executor resources below to match resources requested above
# with an allowance for spark driver overhead. Also change the path to your spark job.
spark-submit --master ${SPARK_MASTER_URL} \
  --executor-memory ${EXECMEM}G \
  --total-executor-cores ${TOTALEXEC} \
  /gpfs/gibbs/project/sbsc/mu78/code/clustering_global/silhouette_score_sample.py


date
