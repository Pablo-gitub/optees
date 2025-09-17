# src/optees/utility/io_knapsack.py
from __future__ import annotations
from typing import Dict, List, Optional
import os

__all__ = ["load_knapsack_burkardt"]

def _read_numbers(path: str) -> List[float]:
    with open(path, "r", encoding="utf-8") as f:
        return [float(line.strip()) for line in f if line.strip()]

def _read_single_int(path: str) -> int:
    vals = _read_numbers(path)
    if len(vals) != 1:
        raise ValueError(f"Expected a single number in {path}")
    v = vals[0]
    if abs(v - round(v)) > 1e-9:
        raise ValueError(f"Capacity must be an integer in {path}")
    return int(round(v))

def load_knapsack_burkardt(dir_path: str, instance: str) -> Dict:
    """
    Load a 0/1 knapsack instance from text files following the Burkardt naming:
      <inst>_c.txt (capacity), <inst>_w.txt (weights),
      <inst>_p.txt (profits/values), <inst>_s.txt (optional optimal selection).

    Example:
      dir_path="tests/data/knapsack/p01", instance="p01"
      expects files p01_c.txt, p01_w.txt, p01_p.txt, p01_s.txt in that folder.
    """
    inst = instance.lower()
    c_file = os.path.join(dir_path, f"{inst}_c.txt")
    w_file = os.path.join(dir_path, f"{inst}_w.txt")
    p_file = os.path.join(dir_path, f"{inst}_p.txt")
    s_file = os.path.join(dir_path, f"{inst}_s.txt")

    capacity = _read_single_int(c_file)
    weights_f = _read_numbers(w_file)
    values_f  = _read_numbers(p_file)

    if len(weights_f) != len(values_f):
        raise ValueError("weights and values length mismatch")

    # cast weights to int, check non-negative
    weights: List[int] = []
    for w in weights_f:
        if w < 0 or abs(w - round(w)) > 1e-9:
            raise ValueError("weights must be non-negative integers")
        weights.append(int(round(w)))

    opt_selection: Optional[List[int]] = None
    if os.path.exists(s_file):
        s = _read_numbers(s_file)
        if len(s) != len(values_f):
            raise ValueError("selection length mismatch")
        opt_selection = [int(round(v)) for v in s]

    return {
        "values": [float(v) for v in values_f],
        "weights": weights,
        "capacity": capacity,
        "opt_selection": opt_selection,
        "metadata": {"source": "burkardt", "instance": inst},
    }
