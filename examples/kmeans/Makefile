# Copyright (C) 2017 Falcon Computing Solutions, Inc. - All rights reserved.
#
# Choose target FPGA platform & vendor
VENDOR=INTEL

# Host Code Compilation settings
HOST_SRC_FILES=./src/local_support.cpp ./src/harness.cpp ./src/support.cpp

# Executable names and arguments
EXE=test
ACC_EXE=test_acc
EXE_ARGS=./data/input.data ./data/check.data

CXX_INC_DIRS=-I./src
CXX_FLAGS+= $(CXX_INC_DIRS)
CXX_FLAGS+= -Wall -O3 -lrt
CXX_FLAGS+=-DPLATFORM=\"$(PLATFORM)\" -DKERNEL=\"$(KERNEL_NAME)\" -DKERNEL_NAME=$(KERNEL_NAME) -DBLACKASIAN=1
# Uncomment the following line to compile the Baseline
CXX_FLAGS+= -DBASELINE=1
#CXX_FLAGS+= -g

# Accelerated Kernel settings
KERNEL_NAME=kmeans

KERNEL_SRC_FILES=./src/kmeans_dse.cpp
KERNEL_INC_DIR=$(CXX_INC_DIRS)

# MerlinCC Options
CMP_OPT= -d11 -DDSE_CUSTOM
LNK_OPT= -g -d11 -DDSECUSTOM

MCC_COMMON_DIR=./
include $(MCC_COMMON_DIR)/mcc_common.mk

