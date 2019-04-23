#pragma ACCEL kernel
void kernel(int N, int *v1, int *v2, int *v3)
{
	for (int i = 0; i < N; ++i) {
		v3[i] = v1[i] + v2[i];
	}
}