# Copyright (c) 2026 Advanced Micro Devices, Inc. All rights reserved.
# SPDX-License-Identifier: MIT
# See LICENSE in the project root for license information.

module load rocm/10.0.0

PATH=$PATH:$HOME/src/apex/install_gilgamesh_5.2.0/bin
export ROCM_ROOT=${ROCM_ROOT:-${ROCM_PATH}}
export ZEROSUM_HIP_ARCH=${ZEROSUM_HIP_ARCH:-gfx942}
if [ -z "${ROCM_ROOT}" ] ; then
    echo "ROCM_ROOT/ROCM_PATH not set. Load rocm/10.0.0 first."
    exit 1
fi

rm -rf build_hip

cmake -B build_hip \
-DCMAKE_BUILD_TYPE=Debug \
-DCMAKE_CXX_COMPILER=`which amdclang++` \
-DCMAKE_C_COMPILER=`which amdclang` \
-DCMAKE_INSTALL_PREFIX=`pwd`/install_hip \
-DCMAKE_C_FLAGS=-gdwarf-4 \
-DCMAKE_CXX_FLAGS=-gdwarf-4 \
-DROCM_ROOT=${ROCM_ROOT} \
-DCMAKE_HIP_ARCHITECTURES=${ZEROSUM_HIP_ARCH} \
-DZeroSum_WITH_HIP=TRUE \
-DZeroSum_STANDALONE=TRUE \

cmake --build build_hip -j
cmake --install build_hip
ctest --test-dir build_hip

#-DZeroSum_WITH_PerfStubs=FALSE \


