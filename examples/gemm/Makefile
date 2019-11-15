# Choose target FPGA platform vendor
VENDOR=XILINX
#VENDOR=INTEL

# Host Code Compilation settings
HOST_SRC_FILES=./src/harness.cpp ./src/local_support.cpp ./src/support.cpp

# Executable names and arguments
EXE=test_gemmb
ACC_EXE=test_accgemmb
EXE_ARGS=./data/input.data ./data/check.data

CXX=g++
CXX_INC_DIRS=-I ../src -I ./ -I $(MACH_COMMON_DIR)
CXX_FLAGS+= $(CXX_INC_DIRS) -Wall -g
#CXX_FLAGS+= -Wall
#CXX_FLAGS+= -g
ifeq ($(VENDOR),XILINX)

CXX_FLAGS +=-lstdc++ -L$(XILINX_SDX)/lib/lnx64.o
endif

# DSE flow setting
AUTODSE=1

# Accelerated Kernel settings
KERNEL_NAME=bbgemm_kernel
KERNEL_SRC_FILES=./src/gemm.cpp
KERNEL_INC_DIR=$(CXX_INC_DIRS)
CMP_OPT=-d11
LNK_OPT=-d11

include ./mcc_common.mk
