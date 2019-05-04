//#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <assert.h>

#define WRITE_OUTPUT
#define CHECK_OUTPUT

#include "support.h"
#ifdef MCC_ACC
#include MCC_ACC_H_FILE
#endif

int main(int argc, char **argv)
{
  // Parse command line.
  char *in_file;
  #ifdef CHECK_OUTPUT
  char *check_file;
  #endif

#ifdef MCC_ACC
  assert( argc<5 && "Usage: ./benchmark <input_file> <check_file> <kernel_binary>" );
#else
  assert( argc<4 && "Usage: ./benchmark <input_file> <check_file>" );
#endif

  in_file = "input.data";
  #ifdef CHECK_OUTPUT
  check_file = "check.data";
  #endif
 if( argc>1 )
    in_file = argv[1];
  #ifdef CHECK_OUTPUT
  if( argc>2 )
    check_file = argv[2];
  #endif

#ifdef MCC_ACC
  char *kernel_binary_file = argv[3];

  __merlin_init(kernel_binary_file);
#endif

  // Load input data
  int in_fd;
  char *data;
  //data = malloc(INPUT_SIZE);
  //data = (char *) malloc(INPUT_SIZE);
  posix_memalign ((void**)&data, 64, INPUT_SIZE);
  assert( data!=NULL && "Out of memory" );
  in_fd = open( in_file, O_RDONLY );
  assert( in_fd>0 && "Couldn't open input data file");
  input_to_data(in_fd, data);
  
  // Unpack and call
  run_benchmark( data );

  #ifdef WRITE_OUTPUT
  int out_fd;
  out_fd = open("output.data", O_WRONLY|O_CREAT|O_TRUNC, S_IRUSR|S_IWUSR|S_IRGRP|S_IWGRP|S_IROTH|S_IWOTH);
  assert( out_fd>0 && "Couldn't open output data file" );
  data_to_output(out_fd, data);
  close(out_fd);
  #endif

  // Load check data
  #ifdef CHECK_OUTPUT
  int check_fd;
  char *ref;
  //ref = malloc(INPUT_SIZE);
  ref = (char *) malloc(INPUT_SIZE);
  assert( ref!=NULL && "Out of memory" );
  check_fd = open( check_file, O_RDONLY );
  assert( check_fd>0 && "Couldn't open check data file");
  output_to_data(check_fd, ref);
  #endif

  // Validate benchmark results
  #ifdef CHECK_OUTPUT
  if( !check_data(data, ref) ) {
    fprintf(stderr, "Benchmark results are incorrect\n");
    char file_name[256] = "fail.o";
    FILE *fp=fopen(file_name,"ab+");
    if(fp==NULL) printf("can't create file!");
    return -1;
  }
  #endif

  printf("Success.\n");
  char file_name_s[256] = "pass.o";
  FILE *fp_s=fopen(file_name_s,"ab+");
  if(fp_s==NULL) printf("can't create file!");
  return 0;
}
