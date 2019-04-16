#include "kmeans.h"
#include <string.h>
#include <stdio.h>
#ifndef FLT_MAX
#define FLT_MAX 3.40282347e+38
#endif

#define NFEATURES 32
#define NPOINTS 819200
#define NCLUSTERS 5

#pragma ACCEL kernel
void workload(float  *feature, /* [npoints][nfeatures] */
        int *membership,
        float  *clusters) /* [n_clusters][n_features] */
{
#pragma ACCEL interface variable=feature depth=26214400 bus_bitwidth=auto{BW1}
#pragma ACCEL interface variable=membership depth=819200 bus_bitwidth=auto{BW2}
#pragma ACCEL interface variable=clusters depth=160
#pragma ACCEL coalescing variable=feature force=on
#pragma ACCEL coalescing variable=membership force=on
#pragma ACCEL coalescing variable=clusters force=on

    int i, j, k, index;

    float local_clusters[NCLUSTERS * NFEATURES];

#ifdef DSE_CUSTOM
#pragma ACCEL pipeline auto{CGPIP1}
#pragma ACCEL tile factor=auto{TILE}
#endif
    /*UPDATE_MEMBER:*/ for (i = 0; i < NPOINTS; i++) {

        float min_dist = FLT_MAX;

        /* find the cluster center id with min distance to pt */
#ifdef DSE_CUSTOM
#pragma ACCEL pipeline auto{CGPIP2}
#endif
        /*MIN:*/ for (j = 0; j < NCLUSTERS; j++) {
            float dist = 0.0;

#ifdef DSE_CUSTOM
#pragma ACCEL parallel auto{R} factor=auto{DIST_PAR}
#endif
            /*DIST:*/ for (k = 0; k < NFEATURES; k++) {
                float diff = feature[NFEATURES * i + k] - clusters[NFEATURES * j + k];
                dist += diff * diff;
            }

            if (dist < min_dist) {
                min_dist = dist;
                index = j;
            }
        }

        /* assign the membership to object i */
        membership[i] = index;
    }
}
