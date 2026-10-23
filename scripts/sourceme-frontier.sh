# Copyright (c) 2026 Advanced Micro Devices, Inc. All rights reserved.
# SPDX-License-Identifier: MIT
# See LICENSE in the project root for license information.

module reset
module unload perftools-base
module load cmake
module load PrgEnv-amd
module swap amd
module load rocm/10.0.0
module swap cray-mpich cray-mpich/8.1.28
module load craype-accel-amd-gfx90a
module unload darshan-runtime
export CRAYPE_LINK_TYPE=dynamic
export OMP_PROC_BIND=true
export OMP_PLACES=threads
export OMP_NUM_THREADS=7
