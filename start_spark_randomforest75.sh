#!/bin/bash
#SBATCH --job-name=rf75
#SBATCH --partition=day
#SBATCH --nodes=6                # node count, change as needed
#SBATCH --ntasks-per-node=4      # do not change, leave as 1 task per node
#SBATCH --cpus-per-task=4       # cpu-cores per task, change as needed
#SBATCH --mem 50G               # memory per node, change as needed
#SBATCH --time=00:50:00
#SBATCH -o /vast/palmer/scratch/sbsc/mu78/stdout/rf75.%A_%a.out
#SBATCH -e /vast/palmer/scratch/sbsc/mu78/stderr/rf75.%A_%a.err
#SBATCH --mail-type=NONE

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

### ---- COMPUTE SPARK EXECUTOR SETTINGS ----

# Executors: 1 executor per Slurm task
EXECUTORS=$(( SLURM_NNODES * SLURM_NTASKS_PER_NODE ))

# Cores per executor = CPUs per task
EXECUTOR_CORES=$SLURM_CPUS_PER_TASK

# Total memory per node (in MB) supplied by Slurm
# Slurm sets SLURM_MEM_PER_NODE in MB if --mem is used
MEM_PER_EXEC_MB=$(( SLURM_MEM_PER_NODE / SLURM_NTASKS_PER_NODE ))
MEM_PER_EXEC_GB=$(( MEM_PER_EXEC_MB / 1024 ))

# Split memory into heap (70%) + overhead (30%)
EXECUTOR_HEAP_GB=$(( MEM_PER_EXEC_GB * 70 / 100 ))
EXECUTOR_OVERHEAD_GB=$(( MEM_PER_EXEC_GB - EXECUTOR_HEAP_GB ))

# Ensure overhead is at least 4GB
if [ $EXECUTOR_OVERHEAD_GB -lt 6 ]; then
  EXECUTOR_OVERHEAD_GB=6
fi

echo "### SPARK EXECUTOR CONFIGURATION ###"
echo "Executors:               $EXECUTORS"
echo "Executor cores:          $EXECUTOR_CORES"
echo "Executor heap (GB):      $EXECUTOR_HEAP_GB"
echo "Executor overhead (GB):  $EXECUTOR_OVERHEAD_GB"
echo "Node memory (GB):        $((SLURM_MEM_PER_NODE / 1024))"
echo "Memory per executor (GB): $MEM_PER_EXEC_GB"
echo "---------------------------------------"

### ---- RUN THE SPARK JOB ----

date

# Customize the executor resources below to match resources requested above
# with an allowance for spark driver overhead. Also change the path to your spark job.
spark-submit \
  --master $SPARK_MASTER_URL \
  --conf spark.dynamicAllocation.enabled=false \
  --conf spark.executor.instances=${EXECUTORS} \
  --conf spark.executor.cores=${EXECUTOR_CORES} \
  --conf spark.executor.memory=${EXECUTOR_HEAP_GB}g \
  --conf spark.executor.memoryOverhead=${EXECUTOR_OVERHEAD_GB}g \
  --conf spark.shuffle.file.buffer=1m \
  --conf spark.shuffle.unsafe.file.output.buffer=1m \
  --conf spark.reducer.maxSizeInFlight=96m \
  --conf spark.shuffle.compress=true \
  --conf spark.shuffle.spill.compress=true \
  --conf spark.default.parallelism=300 \
  --conf spark.sql.shuffle.partitions=300 \
  --conf spark.driver.memory=12g \
  --conf spark.driver.memoryOverhead=4g \
 /gpfs/gibbs/project/sbsc/mu78/code/clustering_global/rf_predict_cluster75.py


date
