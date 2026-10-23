# Copyright (c) 2026 Advanced Micro Devices, Inc. All rights reserved.
# SPDX-License-Identifier: MIT
# See LICENSE in the project root for license information.

export OMP_NUM_THREADS=8
export OMP_PROC_BIND=spread
export OMP_PLACES=cores
export CUDA_VISIBLE_DEVICES=0
export ROCR_VISIBLE_DEVICES=0
export ZES_ENABLE_SYSMAN=1
export ZE_AFFINITY_MASK=0

