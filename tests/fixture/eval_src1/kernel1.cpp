#pragma ACCEL kernel
void kernel(int N, int *v1, int *v2, int *v3)
{
#pragma ACCEL parallel auto{R} factor=auto{PE}	
	for (int i = 0; i < N; ++i) {
		v3[i] = func(v1[i], v2[i]);
	}
}