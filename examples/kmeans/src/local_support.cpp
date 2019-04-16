#include "kmeans.h"
#include <string.h>
#if TIMER
#include "__merlin_timer.h"
#else
#include <sys/time.h>
#endif

int INPUT_SIZE = sizeof(struct bench_args_t);

#ifdef MCC_ACC
#include MCC_ACC_H_FILE
#else
void workload(float *feature, int *membership, float *clusters);
#endif


void run_benchmark( void *vargs ) {
  struct bench_args_t *args = (struct bench_args_t *)vargs;

  #if TIMER
  start_timer();
  #else
  //------------------------------------------------------
  printf("INFO: Starting processing ...\n");
  struct timeval tv_start, tv_end;
  double kernel_time;
  gettimeofday (&tv_start, NULL);
  #endif

  float *feature = (float *) malloc (sizeof(args->feature));
  float *clusters = (float *) malloc (sizeof(args->clusters));
  int *membership = (int *) malloc (sizeof(args->membership));

  memcpy(feature, args->feature, sizeof(args->feature));
  memcpy(clusters, args->clusters, sizeof(args->clusters));

  #ifdef MCC_ACC
  __merlin_workload( feature,membership,clusters);
  #else
  workload(feature,membership,clusters);
  #endif

  memcpy(args->membership, membership, sizeof(args->membership));

  #if TIMER
  printf("Kernel time: %lf\n", read_timer());
  #else
  //stop the timer
  gettimeofday (&tv_end, NULL);
  printf("INFO: Kernel execution completed.\n");
  kernel_time = (tv_end.tv_sec - tv_start.tv_sec) * 1000.0 +
    (tv_end.tv_usec - tv_start.tv_usec)/1000.0;

  printf("INFO: Kernel execution time=%f ms\n", kernel_time);
  fprintf(stderr, "[INFO] kernel_run_time:%f ms\n", kernel_time);

  printf("TAGTIME:%f\n", kernel_time);
  //------------------------------------------------------
  #endif


}

void input_to_data(int fd, void *vdata) {
  struct bench_args_t *data = (struct bench_args_t *)vdata;
  char *p, *s;

  // Zero-out everything.
  memset(vdata,0,sizeof(struct bench_args_t));
  // Load input string
  p = readfile(fd);
  s = find_section_start(p,1);

  int input_size = 1024 * 34;
  STAC(parse_,float,_array)(s, data->feature, input_size);

  // comaniac: Duplicate input
  for (int i = 1; i < 27852800 / input_size; i++)
      memcpy(&data->feature[i * input_size], data->feature,
              input_size * sizeof(float));

  s = find_section_start(p,2);
  STAC(parse_,float,_array)(s, data->clusters, 170);

}

void data_to_input(int fd, void *vdata) {
  struct bench_args_t *data = (struct bench_args_t *)vdata;

  write_section_header(fd);
  STAC(write_, float, _array)(fd, data->feature, 27852800);
  write_section_header(fd);
  STAC(write_, float, _array)(fd, data->clusters, 170);

  write_section_header(fd);
}

void output_to_data(int fd, void *vdata) {
  struct bench_args_t *data = (struct bench_args_t *)vdata;
  char *p, *s;
  // Zero-out everything.
  memset(vdata,0,sizeof(struct bench_args_t));
  // Load input string
  p = readfile(fd);

  s = find_section_start(p,1);
  STAC(parse_,int32_t,_array)(s, data->membership, 819200);
}

void data_to_output(int fd, void *vdata) {
  struct bench_args_t *data = (struct bench_args_t *)vdata;


  write_section_header(fd);
  STAC(write_,int32_t,_array)(fd, data->membership, 819200);
  write_section_header(fd);
}

int check_data( void *vdata, void *vref ) {
  //printf("starting check data\n");
  struct bench_args_t *data = (struct bench_args_t *)vdata;
  //printf("converting data\n");
  struct bench_args_t *ref = (struct bench_args_t *)vref;
  //printf("converting ref\n");
  int has_errors = 0;

  has_errors |= memcmp(data->membership, ref->membership, 819200);
  //printf("finished comparing\n");

  // Return true if it's correct.
  return !has_errors;
}

