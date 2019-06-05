/*
Implementation based on algorithm described in:
The cache performance and optimizations of blocked algorithms
M. D. Lam, E. E. Rothberg, and M. E. Wolf
ASPLOS 1991
*/

#include "gemm.h"

#pragma ACCEL kernel
void bbgemm_kernel(TYPE m1[N], TYPE m2[N], TYPE prod[N]){
    int i, k, j, jj, kk;
    int i_row, k_row;
    TYPE temp_x, mul;
    #pragma ACCEL interface variable=m1 depth=16384 bus_bitwidth=auto{B}
    #pragma ACCEL interface variable=m2 depth=16384 bus_bitwidth=auto{B}
    #pragma ACCEL interface variable=prod depth=16384 bus_bitwidth=auto{B}

    for(int n=0; n<1000; n++) {
    for (jj = 0; jj < row_size; jj += block_size){
        for (kk = 0; kk < row_size; kk += block_size){
#pragma ACCEL pipeline auto{PIPI}
#pragma ACCEL parallel factor=auto{PARI}
            for ( i = 0; i < row_size; ++i){
#pragma ACCEL pipeline auto{PIPK}
#pragma ACCEL parallel factor=auto{PARK}
                for (k = 0; k < block_size; ++k){
                    i_row = i * row_size;
                    k_row = (k  + kk) * row_size;
                    temp_x = m1[i_row + k + kk];
#pragma ACCEL parallel factor=auto{PARJ}
                    for (j = 0; j < block_size; ++j){
                        mul = temp_x * m2[k_row + j + jj];
                        prod[i_row + j + jj] += mul;
                    }
                }
            }
        }
    }
    }
}
