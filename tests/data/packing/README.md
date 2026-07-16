# 3D Packing Benchmark Data

`orlib/thpack1.txt` is the original OR-Library file published by J. E.
Beasley and contributed by M. S. W. Ratcliff. The instances were generated for
E. E. Bischoff and M. S. W. Ratcliff, *Issues in the Development of Approaches
to Container Loading*, OMEGA 23(4), 1995, pp. 377-390.

- Source: https://people.brunel.ac.uk/~mastjjb/jeb/orlib/thpackinfo.html
- File: https://people.brunel.ac.uk/~mastjjb/jeb/orlib/files/thpack1.txt
- SHA-256: `d6f0b99b4cc6e51c5753565b175a778a40422dc92cffee3204bf16cc1d23f341`
- Objective: maximize occupied volume in one rectangular container.
- Contents: 100 instances with three box types each.

The complete instances contain more than one hundred physical boxes and are
not run by the exact pairwise MILP during normal CI. The end-to-end test uses
two copies of the first published box type as an explicitly labelled
**derived smoke subset**. Its expected objective is analytic (twice the box
volume); it is not reported as a published benchmark optimum. The original
file is retained so parsing and provenance remain verifiable and larger
experiments can opt into the complete data.
