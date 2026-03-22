"""Worker threads for background operations."""

from PyQt6.QtCore import QThread, pyqtSignal, QObject
import logging
from typing import Optional, Callable, Any

from ..core import PDFProcessor, ProcessingOptions, ProcessingResult

logger = logging.getLogger(__name__)


class PDFLoadWorker(QThread):
    """Worker thread for loading PDF files."""

    progress = pyqtSignal(int, int)  # current, total
    finished = pyqtSignal(object)  # PDFProcessor
    error = pyqtSignal(str)

    def __init__(self, pdf_path: str):
        """Initialize worker."""
        super().__init__()
        self.pdf_path = pdf_path

    def run(self):
        """Run the worker."""
        try:
            logger.info(f"Loading PDF: {self.pdf_path}")
            processor = PDFProcessor(self.pdf_path)
            logger.info(f"PDF loaded successfully: {processor.total_pages} pages")
            self.finished.emit(processor)
        except Exception as e:
            logger.error(f"Error loading PDF: {type(e).__name__}: {e}", exc_info=True)
            self.error.emit(f"{type(e).__name__}: {str(e)}")


class PDFAnalysisWorker(QThread):
    """Worker thread for analyzing PDF pages."""

    progress = pyqtSignal(int, int)  # current, total
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, processor: PDFProcessor, options: ProcessingOptions):
        """Initialize worker."""
        super().__init__()
        self.processor = processor
        self.options = options

    def run(self):
        """Run the worker."""
        try:
            self.processor.analyze_pages(self.options, self.progress.emit)
            self.finished.emit()
        except Exception as e:
            logger.error(f"Error analyzing PDF: {e}")
            self.error.emit(str(e))


class PDFProcessingWorker(QThread):
    """Worker thread for processing PDF."""

    progress = pyqtSignal(int, int)  # current, total
    finished = pyqtSignal(object)  # ProcessingResult
    error = pyqtSignal(str)

    def __init__(
        self,
        processor: PDFProcessor,
        output_path: str,
        options: ProcessingOptions,
        pages_info: Optional[Any] = None,
    ):
        """Initialize worker."""
        super().__init__()
        self.processor = processor
        self.output_path = output_path
        self.options = options
        self.pages_info = pages_info or processor.pages_info

    def run(self):
        """Run the worker."""
        try:
            result = self.processor.process_pdf(
                self.output_path, self.options, self.pages_info, self.progress.emit
            )
            self.finished.emit(result)
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            self.error.emit(str(e))


class ThumbnailWorker(QThread):
    """Worker thread for generating thumbnails."""

    thumbnail_ready = pyqtSignal(int, object)  # page_index, thumbnail_image
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(
        self,
        processor: PDFProcessor,
        page_indices: list,
        size: int = 150,
    ):
        """Initialize worker."""
        super().__init__()
        self.processor = processor
        self.page_indices = page_indices
        self.size = size

    def run(self):
        """Run the worker."""
        try:
            for page_idx in self.page_indices:
                thumbnail = self.processor.get_page_thumbnail(page_idx, self.size)
                self.thumbnail_ready.emit(page_idx, thumbnail)
            self.finished.emit()
        except Exception as e:
            logger.error(f"Error generating thumbnails: {e}")
            self.error.emit(str(e))
