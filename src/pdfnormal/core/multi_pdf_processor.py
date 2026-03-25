"""Multi-PDF processor for handling merged PDF operations."""

import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Optional, Callable, Dict
import logging

from .models import ProcessingOptions, ProcessingResult, PageInfo
from .image_processor import ImageProcessor
from .crop_utils import compute_safe_cropbox

logger = logging.getLogger(__name__)


class MultiPDFProcessor:
    """Processor for handling multiple PDF files with merge capabilities."""

    def __init__(self):
        """Initialize multi-PDF processor."""
        self.processors: List['PDFProcessor'] = []
        self.merged_pages_info: List[PageInfo] = []

    def add_processor(self, processor: 'PDFProcessor') -> None:
        """Add a PDF processor to the collection."""
        self.processors.append(processor)
        # Update source info for pages
        for page_info in processor.pages_info:
            page_info.source_pdf_path = str(processor.pdf_path)
            page_info.source_pdf_name = Path(processor.pdf_path).stem
        self.merged_pages_info.extend(processor.pages_info)
        logger.info(f"Added PDF with {len(processor.pages_info)} pages")

    def get_page_image(self, page_index: int, zoom: float = 1.0, max_pixels: Optional[int] = None):
        """Get image array for a specific page from any PDF."""
        if page_index < 0 or page_index >= len(self.merged_pages_info):
            raise IndexError(f"Page index {page_index} out of range")

        page_info = self.merged_pages_info[page_index]
        
        # Find the processor that contains this page
        for processor in self.processors:
            if page_info.source_pdf_path == str(processor.pdf_path):
                return processor.get_page_image(page_info.original_index, zoom, max_pixels)
        
        raise ValueError(f"Could not find processor for page {page_index}")

    def get_page_thumbnail(self, page_index: int, size: int = 150):
        """Get thumbnail for a page from any PDF."""
        if page_index < 0 or page_index >= len(self.merged_pages_info):
            raise IndexError(f"Page index {page_index} out of range")

        page_info = self.merged_pages_info[page_index]
        
        # Find the processor that contains this page
        for processor in self.processors:
            if page_info.source_pdf_path == str(processor.pdf_path):
                return processor.get_page_thumbnail(page_info.original_index, size)
        
        raise ValueError(f"Could not find processor for page {page_index}")

    def analyze_pages(
        self,
        options: ProcessingOptions,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        """Analyze all pages from all PDFs."""
        image_processor = ImageProcessor()

        for i, page_info in enumerate(self.merged_pages_info):
            if progress_callback:
                progress_callback(i + 1, len(self.merged_pages_info))

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
                f"Page {i + 1} ({page_info.source_pdf_name}): blank={page_info.is_blank}, rotation={page_info.rotation}°"
            )

    def process_pdf(
        self,
        output_path: str,
        options: ProcessingOptions,
        pages_info: Optional[List[PageInfo]] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> ProcessingResult:
        """Process merged PDFs with selected options and save to output file."""
        if pages_info is None:
            pages_info = self.merged_pages_info

        total_original = len(self.merged_pages_info)
        result = ProcessingResult(
            success=False,
            total_pages_original=total_original,
            total_pages_processed=0,
        )

        try:
            # Create new PDF
            output_doc = fitz.open()

            # Group pages by source PDF for efficient processing
            source_groups: Dict[str, List[PageInfo]] = {}
            for page_info in pages_info:
                source = page_info.source_pdf_path
                if source not in source_groups:
                    source_groups[source] = []
                source_groups[source].append(page_info)

            # Process each source PDF
            processed_count = 0
            for source_path, source_pages in source_groups.items():
                # Find the processor for this source
                processor = None
                for p in self.processors:
                    if str(p.pdf_path) == source_path:
                        processor = p
                        break

                if not processor:
                    logger.error(f"Could not find processor for {source_path}")
                    continue

                # Process pages from this source in order
                for page_info in source_pages:
                    if progress_callback:
                        progress_callback(processed_count + 1, len(pages_info))

                    original_idx = page_info.original_index

                    # Skip blank pages
                    if page_info.is_blank and options.remove_blank_pages:
                        result.blank_pages_removed.append(page_info.page_number)
                        continue

                    # Get source page
                    source_page = processor.document[original_idx]

                    # Apply rotation
                    if page_info.rotation != 0 and options.auto_correct_orientation:
                        source_page.set_rotation(page_info.rotation)
                        result.pages_rotated.append(page_info.page_number)

                    # Copy page to output document
                    output_doc.insert_pdf(
                        processor.document, from_page=original_idx, to_page=original_idx
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
                        # PyMuPDF validates cropboxes against MediaBox.
                        mediabox = new_page.mediabox

                        # Calculate crop rectangle safely.
                        crop_rect = compute_safe_cropbox(
                            rect,
                            page_info.margins,
                            clamp_rect=mediabox,
                        )
                        if crop_rect is not None:
                            new_page.set_cropbox(crop_rect)
                            result.pages_with_margin_changes.append(page_info.page_number)

                    result.total_pages_processed += 1
                    processed_count += 1

            # Save output PDF
            output_doc.save(
                output_path,
                garbage=4,  # Maximum compression
                deflate=True,
            )
            output_doc.close()

            result.success = True
            result.output_file_path = output_path
            result.pages_info = pages_info
            logger.info(
                f"Merged PDF processing complete: {result.total_pages_original} → "
                f"{result.total_pages_processed} pages"
            )

        except Exception as e:
            result.success = False
            result.error_message = str(e)
            logger.error(f"Error processing merged PDF: {e}")

        return result

    def close(self) -> None:
        """Close all PDF processors."""
        for processor in self.processors[:]:  # Create a copy to iterate
            try:
                if hasattr(processor, 'close'):
                    processor.close()
            except Exception as e:
                logger.debug(f"Error closing processor: {e}")
        
        self.processors.clear()
        self.merged_pages_info.clear()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
