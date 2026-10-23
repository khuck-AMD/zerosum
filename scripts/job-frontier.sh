#!/bin/bash -e
# Copyright (c) 2026 Advanced Micro Devices, Inc. All rights reserved.
# SPDX-License-Identifier: MIT
# See LICENSE in the project root for license information.

#SBATCH -A phy122-ecp
#SBATCH -J test_xgc
#SBATCH -t 0:05:00
#SBATCH --threads-per-core=2 
#SBATCH -N 1
#SBATCH -q debug
#SBATCH -S 8

# Assumption - this script will reserve 1 core per L3 bank for system activity.
#module load rocm/10.0.0
cd $HOME/ECP-WDM/ecp-wdm-coe
source frontier.sh
cd $HOME/src/zerosum

unset OMP_PROC_BIND
unset OMP_PLACES
unset OMP_NUM_THREADS
unset OMP_SCHEDULE
export SLURM_CPU_BIND_VERBOSE=1
builddir=${ZEROSUM_BUILD_DIR:-./build.10.0.0}

dosrun() {
    srun -n8 --gpus-per-task=1 --cpus-per-task=14 --gpu-bind=closest ${builddir}/bin/zerosum-mpi ${builddir}/bin/lu-decomp-mpi
}

echo "Defaults"
dosrun
for i in {0..7} ; do
    mv zs.${i}.log zs.14.default.${i}.log
done

echo "With Cores"
export OMP_PROC_BIND=close
export OMP_PLACES=cores
export OMP_NUM_THREADS=14
export OMP_SCHEDULE=dynamic
dosrun
for i in {0..7} ; do
    mv zs.${i}.log zs.14.cores.${i}.log
done

echo "With Threads"
export OMP_PROC_BIND=close
export OMP_PLACES=threads
export OMP_NUM_THREADS=14
dosrun
for i in {0..7} ; do
    mv zs.${i}.log zs.14.threads.${i}.log
done

