"""Detect dataset shift before it quietly reaches a model."""

from data_shift_watch.core import analyze_shift
from data_shift_watch.models import ColumnShift, DriftReport, Thresholds

__all__ = ["ColumnShift", "DriftReport", "Thresholds", "analyze_shift"]
__version__ = "0.1.0"
