#!/bin/bash
#SBATCH --job-name=diac
#SBATCH --partition=day
#SBATCH --nodes=6                # node count, change as needed
#SBATCH --ntasks-per-node=1      # do not change, leave as 1 task per node
#SBATCH --cpus-per-task=32       # cpu-cores per task, change as needed
#SBATCH --mem 256G               # memory per node, change as needed
#SBATCH --time=00:30:00
#SBATCH -o /vast/palmer/scratch/sbsc/mu78/stdout/diac.%A_%a.out
#SBATCH -e /vast/palmer/scratch/sbsc/mu78/stderr/diac.%A_%a.err
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
spark-submit \
  --master ${SPARK_MASTER_URL} \
  --num-executors 30 \
  --executor-cores 6 \
  --executor-memory 40G \
  --driver-memory 16G \
  --conf spark.sql.shuffle.partitions=600 \
  --conf spark.network.timeout=600s \
  --conf spark.executor.heartbeatInterval=60s \
  --conf spark.shuffle.io.maxRetries=10 \
  --conf spark.shuffle.io.retryWait=10s \
  /gpfs/gibbs/project/sbsc/mu78/code/clustering_global/cluster_diagnostic2.py

date
