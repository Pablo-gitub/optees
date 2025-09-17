# Datasets & Formats

This project intentionally keeps solvers **agnostic** of file formats. Adapters live in `src/optees/data/adapters/` (currently under `src/optees/utility/` while bootstrapping).

## LP (continuous)
- **LPnetlib (SuiteSparse)**: `.mat` instances (A, c, row bounds `rl/ru`, or RHS `b`, and var bounds `lo/hi`).
  - Source: https://sparse.tamu.edu/LPnetlib
  - Adapter: `load_lpnetlib_mat(path)` → canonical LP dict.

## 0/1 Knapsack
- **Burkardt / KNAPSACK_01**: text files per instance:
  - `<inst>_c.txt` (capacity, integer)
  - `<inst>_w.txt` (weights, one per line, integers)
  - `<inst>_p.txt` (profits/values, one per line)
  - `<inst>_s.txt` (optional: optimal 0/1 selection, one per line)
  - Source: https://people.sc.fsu.edu/~jburkardt/datasets/knapsack_01/knapsack_01.html
  - Adapter: `load_knapsack_burkardt(dir_path, instance)`.

## Layout under tests
````

tests/data/
        lp/lpnetlib_mat/
                lp_afiro.mat
                lp_25fv47.mat
        knapsack/
            p01/
                p01_c.txt
                p01_w.txt
                p01_p.txt
                p01_s.txt
            p02/
                p02_c.txt
                p02_w.txt
                p02_p.txt
                p02_s.txt
            p08/
                p08_c.txt
                p08_w.txt
                p08_p.txt
                p08_s.txt

````

> For larger sets (OR-Library, Pisinger), we’ll add separate adapters and keep only a few small instances in-repo. The rest should be documented with links and expected checksums.
