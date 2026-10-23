# Copyright (c) 2026 Advanced Micro Devices, Inc. All rights reserved.
# SPDX-License-Identifier: MIT
# See LICENSE in the project root for license information.

cmake_minimum_required (VERSION 3.20.1 FATAL_ERROR)
project(ompt_5.0_test)
set (CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${OpenMP_CXX_FLAGS}")
SET(CMAKE_EXE_LINKER_FLAGS  "${CMAKE_EXE_LINKER_FLAGS} ${OpenMP_CXX_FLAGS}")
add_executable(ompt_5.0_test ompt_test.cpp)