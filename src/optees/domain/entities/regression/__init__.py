"""Entities for educational supervised regression."""

from .dataset import RegressionDataset
from .solution import RegressionMetrics, RegressionPrediction, RegressionSolution

__all__ = [
    "RegressionDataset",
    "RegressionMetrics",
    "RegressionPrediction",
    "RegressionSolution",
]
