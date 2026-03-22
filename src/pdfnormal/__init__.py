"""Package initialization."""

__version__ = "1.0.0"
__author__ = "PDF Normal Team"

from .core import PDFProcessor, ImageProcessor, ProcessingOptions, ProcessingResult

__all__ = [
    "PDFProcessor",
    "ImageProcessor",
    "ProcessingOptions",
    "ProcessingResult",
]
