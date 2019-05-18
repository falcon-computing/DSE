#include "gemm.h"
#include <string.h>
#include <sys/time.h>

int INPUT_SIZE = sizeof(struct bench_args_t);
#ifdef MCC_ACC
#include MCC_ACC_H_FILE
#else
void bbgemm_kernel(TYPE m1[N], TYPE m2[N], TYPE prod[N]);
#endif

#define EPSILON ((TYPE)1.0e-6)

void run_benchmark( void *vargs ) {
  struct bench_args_t *args = (struct bench_args_t *)vargs;
  //------------------------------------------------------
  printf("INFO: Starting processing ...\n");
  struct timeval tv_start, tv_end;
  double kernel_time;
  gettimeofday (&tv_start, NULL);

#ifdef MCC_ACC
  __merlin_bbgemm_kernel( args->m1, args->m2, args->prod );
#else
  #pragma ACCEL task name="bbgemm"
  bbgemm_kernel( args->m1, args->m2, args->prod );
#endif

  //stop the timer
  gettimeofday (&tv_end, NULL);
  printf("INFO: Kernel execution completed.\n");
  kernel_time = (tv_end.tv_sec - tv_start.tv_sec) * 1000.0 +
    (tv_end.tv_usec - tv_start.tv_usec)/1000.0;
#ifdef RUNS
  kernel_time /= RUNS;
#endif

  printf("INFO: Kernel execution time=%f ms\n", kernel_time);
  fprintf(stderr, "[INFO] kernel_run_time:%f ms\n", kernel_time);
  printf("TAGTIME:%f\n", kernel_time);
  //------------------------------------------------------
}

/* Input format:
%% Section 1
TYPE[N]: matrix 1
%% Section 2
TYPE[N]: matrix 2
*/

void input_to_data(int fd, void *vdata) {
  struct bench_args_t *data = (struct bench_args_t *)vdata;
  char *p, *s;
  // Zero-out everything.
  memset(vdata,0,sizeof(struct bench_args_t));
  // Load input string
  p = readfile(fd);

  s = find_section_start(p,1);
  STAC(parse_,TYPE,_array)(s, data->m1, N);

  s = find_section_start(p,2);
  STAC(parse_,TYPE,_array)(s, data->m2, N);

}

void data_to_input(int fd, void *vdata) {
  struct bench_args_t *data = (struct bench_args_t *)vdata;

  write_section_header(fd);
  STAC(write_,TYPE,_array)(fd, data->m1, N);

  write_section_header(fd);
  STAC(write_,TYPE,_array)(fd, data->m2, N);
}

/* Output format:
%% Section 1
TYPE[N]: output matrix
*/

void output_to_data(int fd, void *vdata) {
  struct bench_args_t *data = (struct bench_args_t *)vdata;
  char *p, *s;
  // Load input string
  p = readfile(fd);

  s = find_section_start(p,1);
  STAC(parse_,TYPE,_array)(s, data->prod, N);
}

void data_to_output(int fd, void *vdata) {
  struct bench_args_t *data = (struct bench_args_t *)vdata;

  write_section_header(fd);
  STAC(write_,TYPE,_array)(fd, data->prod, N);
}

int check_data( void *vdata, void *vref ) {
  struct bench_args_t *data = (struct bench_args_t *)vdata;
  struct bench_args_t *ref = (struct bench_args_t *)vref;
  int has_errors = 0;
  int r,c;
  TYPE diff;

  for( r=0; r<row_size; r++ ) {
    for( c=0; c<col_size; c++ ) {
      diff = data->prod[r*row_size + c] - ref->prod[r*row_size+c];
      has_errors |= (diff<-EPSILON) || (EPSILON<diff);
    }
  }

  // Return true if it's correct.
  return !has_errors;
}
