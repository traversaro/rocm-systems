"""
Metric Generator Package
Provides reverse engineering approach for ROCm metric generator system
"""

from .component_extractor import ComponentExtractor
from .detection_module import ChangeDetector, ChangeType
from .main_controller import MetricGeneratorController
from .validation_generator import UnifiedConfigGenerator, ValidationFileGenerator

__version__ = "1.0.0"
__all__ = [
    "MetricGeneratorController",
    "ChangeDetector",
    "ChangeType",
    "ComponentExtractor",
    "ValidationFileGenerator",
    "UnifiedConfigGenerator"
]