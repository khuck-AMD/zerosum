# Copyright (c) 2026 Advanced Micro Devices, Inc. All rights reserved.
# SPDX-License-Identifier: MIT
# See LICENSE in the project root for license information.

set -e 

rm -rf build

cmake -B build \
-DCMAKE_BUILD_TYPE=RelWithDebInfo \
-DCMAKE_CXX_COMPILER=`which icpx` \
-DCMAKE_C_COMPILER=`which icx` \
-DCMAKE_INSTALL_PREFIX=`pwd`/install \
-DZeroSum_WITH_SYCL=TRUE \
-DZeroSum_STANDALONE=TRUE \
-DZeroSum_WITH_HWLOC=TRUE \

cmake --build build -j
cmake --install build
#ctest --test-dir build

#-DZeroSum_WITH_PerfStubs=FALSE \


