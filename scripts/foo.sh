# Copyright (c) 2026 Advanced Micro Devices, Inc. All rights reserved.
# SPDX-License-Identifier: MIT
# See LICENSE in the project root for license information.


NRANKS=$(( NNODES * RANKS_PER_NODE ))

let nthreads=16
mylist=""

let first_hwthread=2
let first_core=${first_hwthread}
let last_core=${first_core}+${nthreads}-1

for i in {1..6} ; do
    if [ $i -gt 1 ] ; then
        mylist="${mylist}:"
    fi
    mylist="${mylist}${first_core}-${last_core}"
    let first_core=${first_core}+${nthreads}
    let last_core=${last_core}+${nthreads}
done

let first_hwthread=106
let first_core=${first_hwthread}
let last_core=${first_core}+${nthreads}-1

for i in {1..6} ; do
    mylist="${mylist}:${first_core}-${last_core}"
    let first_core=${first_core}+${nthreads}
    let last_core=${last_core}+${nthreads}
done

echo ${mylist}