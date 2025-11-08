"""Toyota GR Cup Racing Analytics Package.

A comprehensive toolkit for analyzing Toyota GR Cup racing data,
including telemetry analysis, lap time optimization, and race strategy.
"""

__version__ = "0.1.0"
__author__ = "TRD Hackathon Team"
__email__ = "team@trd-hackathon.com"

# Make key modules easily accessible
from . import data_processing
from . import analysis
from . import visualization
from . import models

__all__ = [
    "data_processing",
    "analysis",
    "visualization",
    "models",
]