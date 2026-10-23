# Copyright (c) 2026 Advanced Micro Devices, Inc. All rights reserved.
# SPDX-License-Identifier: MIT
# See LICENSE in the project root for license information.

qsub -l select=1 -l walltime=30:00 -A XGC_aesp_CNDA -q debug -I

