"""Main PDF processing module."""

import fitz  # PyMuPDF
import cv2
import numpy as np
from pathlib import Path
from typing import List, Optional, Callable
import logging

from .models import ProcessingOptions, ProcessingResult, PageInfo
from .image_processor import ImageProcessor

logger = logging.getLogger(__name__)


class PDFProcessor:
    """Main class for PDF processing operations."""

    def __init__(self, pdf_path: str):
        """
        Initialize PDF processor with a PDF file.

        Args:
            pdf_path: Path to the PDF file

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            ValueError: If file is not a valid PDF
        """
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        try:
            self.document = fitz.open(str(self.pdf_path))
            self.total_pages = len(self.document)
            logger.info(f"Loaded PDF: {pdf_path} with {self.total_pages} pages")
        except Exception as e:
            raise ValueError(f"Invalid PDF file: {e}")

        self.pages_info: List[PageInfo] = []
        self._initialize_pages_info()

    def _initialize_pages_info(self) -> None:
        """Initialize page information for all pages."""
        self.pages_info = []
        for i in range(self.total_pages):
            page = self.document[i]
            rect = page.rect  # Use .rect instead of .get_rect()
            page_info = PageInfo(
                page_number=i + 1,
                original_index=i,
                width=rect.width,
                height=rect.height,
            )
            self.pages_info.append(page_info)

    def get_page_image(
        self, page_index: int, zoom: float = 1.0, max_pixels: Optional[int] = None
    ) -> np.ndarray:
        """
        Get image array for a specific page.

        Args:
            page_index: Index of the page (0-based)
            zoom: Zoom level for rendering (default 1.0)
            max_pixels: Maximum pixels to render (for memory efficiency)

        Returns:
            NumPy array in BGR format (CV2 compatible)

        Raises:
            IndexError: If page index is out of range
        """
        if page_index < 0 or page_index >= self.total_pages:
            raise IndexError(f"Page index {page_index} out of range")

        page = self.document[page_index]

        # Apply zoom and pixel limit
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)

        # Convert to numpy array
        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            (pix.height, pix.width, 3)
        )

        # Convert RGB to BGR for OpenCV
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

        # Downscale if needed
        if max_pixels:
            height, width = img_array.shape[:2]
            total_pixels = height * width
            if total_pixels > max_pixels:
                scale = np.sqrt(max_pixels / total_pixels)
                new_width = int(width * scale)
                new_height = int(height * scale)
                img_array = cv2.resize(img_array, (new_width, new_height))

        return img_array

    def get_page_thumbnail(self, page_index: int, size: int = 150) -> np.ndarray:
        """
        Get thumbnail for a page (for lazy loading).

        Args:
            page_index: Index of the page (0-based)
            size: Thumbnail size in pixels

        Returns:
            NumPy array of thumbnail image
        """
        try:
            page = self.document[page_index]
            pix = page.get_pixmap(matrix=fitz.Matrix(0.5, 0.5), alpha=False)
            img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                (pix.height, pix.width, 3)
            )
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

            # Resize to thumbnail
            height, width = img_array.shape[:2]
            aspect_ratio = width / height
            if aspect_ratio > 1:
                new_width = size
                new_height = int(size / aspect_ratio)
            else:
                new_height = size
                new_width = int(size * aspect_ratio)

            return cv2.resize(img_array, (new_width, new_height))
        except Exception as e:
            logger.error(f"Error creating thumbnail for page {page_index}: {e}")
            return np.zeros((size, size, 3), dtype=np.uint8)

    def analyze_pages(
        self,
        options: ProcessingOptions,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        """
        Analyze all pages for processing.

        Args:
            options: Processing options
            progress_callback: Callback function(current, total) for progress updates
        """
        image_processor = ImageProcessor()

        for i, page_info in enumerate(self.pages_info):
            if progress_callback:
                progress_callback(i + 1, self.total_pages)

            # Get page image for analysis (lower resolution for speed)
            img_array = self.get_page_image(i, zoom=0.5, max_pixels=500000)

            # Check if blank
            if options.remove_blank_pages:
                page_info.is_blank = image_processor.detect_blank_page(
                    img_array, options.blank_page_threshold
                )

            # Detect orientation
            if options.auto_correct_orientation:
                rotation = image_processor.detect_orientation(img_array)
                page_info.rotation = rotation

            logger.debug(
                f"Page {i + 1}: blank={page_info.is_blank}, rotation={page_info.rotation}°"
            )

    def process_pdf(
        self,
        output_path: str,
        options: ProcessingOptions,
        pages_info: Optional[List[PageInfo]] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> ProcessingResult:
        """
        Process PDF with selected options and save to output file.

        Args:
            output_path: Path for output PDF
            options: Processing options
            pages_info: Updated pages info (for reordering, margin changes)
            progress_callback: Callback function(current, total) for progress

        Returns:
            ProcessingResult with details of changes
        """
        if pages_info is None:
            pages_info = self.pages_info

        result = ProcessingResult(
            success=False,
            total_pages_original=self.total_pages,
            total_pages_processed=0,
            pages_info=pages_info,
        )

        try:
            # Create new PDF
            output_doc = fitz.open()

            # Process each page
            for i, page_info in enumerate(pages_info):
                if progress_callback:
                    progress_callback(i + 1, len(pages_info))

                original_idx = page_info.original_index

                # Skip blank pages
                if page_info.is_blank and options.remove_blank_pages:
                    result.blank_pages_removed.append(page_info.page_number)
                    continue

                # Get source page
                source_page = self.document[original_idx]

                # Apply rotation
                if page_info.rotation != 0 and options.auto_correct_orientation:
                    source_page.set_rotation(page_info.rotation)
                    result.pages_rotated.append(page_info.page_number)

                # Copy page to output document
                output_doc.insert_pdf(
                    self.document, from_page=original_idx, to_page=original_idx
                )

                # Apply margin cropping if specified
                if any(
                    margin > 0
                    for margin in [
                        page_info.margins["top"],
                        page_info.margins["bottom"],
                        page_info.margins["left"],
                        page_info.margins["right"],
                    ]
                ):
                    # Get the newly inserted page
                    new_page = output_doc[output_doc.page_count - 1]
                    rect = new_page.rect

                    # Calculate crop rectangle
                    crop_rect = fitz.Rect(
                        rect.x0 + page_info.margins["left"],
                        rect.y0 + page_info.margins["top"],
                        rect.x1 - page_info.margins["right"],
                        rect.y1 - page_info.margins["bottom"],
                    )

                    new_page.set_cropbox(crop_rect)
                    result.pages_with_margin_changes.append(page_info.page_number)

                result.total_pages_processed += 1

            # Save output PDF
            output_doc.save(
                output_path,
                garbage=4,  # Maximum compression
                deflate=True,
            )
            output_doc.close()

            result.success = True
            result.output_file_path = output_path
            logger.info(
                f"PDF processing complete: {result.total_pages_original} → "
                f"{result.total_pages_processed} pages"
            )

        except Exception as e:
            result.success = False
            result.error_message = str(e)
            logger.error(f"Error processing PDF: {e}")

        return result

    def get_file_info(self) -> dict:
        """
        Get information about the PDF file.

        Returns:
            Dictionary with file info
        """
        try:
            file_size = self.pdf_path.stat().st_size
            return {
                "path": str(self.pdf_path),
                "filename": self.pdf_path.name,
                "size_bytes": file_size,
                "size_mb": file_size / (1024 * 1024),
                "total_pages": self.total_pages,
                "is_pdf": self.pdf_path.suffix.lower() == ".pdf",
            }
        except Exception as e:
            logger.error(f"Error getting file info: {e}")
            return {}

    def close(self) -> None:
        """Close the PDF document."""
        try:
            if self.document and not self.document.is_closed:
                self.document.close()
        except Exception as e:
            logger.debug(f"Error closing document: {e}")
        finally:
            self.document = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
