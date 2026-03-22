"""Tests for PDF processor module."""

import pytest
from pathlib import Path

from pdfnormal.core import PDFProcessor, ProcessingOptions, ProcessingResult


class TestPDFProcessor:
    """Tests for PDFProcessor class."""

    def test_init_with_valid_pdf(self, sample_pdf):
        """Test initialization with valid PDF."""
        processor = PDFProcessor(sample_pdf)
        assert processor.total_pages == 3
        assert len(processor.pages_info) == 3
        processor.close()

    def test_init_with_nonexistent_file(self):
        """Test initialization with non-existent file."""
        with pytest.raises(FileNotFoundError):
            PDFProcessor("/nonexistent/path/file.pdf")

    def test_get_file_info(self, sample_pdf):
        """Test getting file information."""
        processor = PDFProcessor(sample_pdf)
        info = processor.get_file_info()

        assert info["is_pdf"] is True
        assert info["total_pages"] == 3
        assert info["size_bytes"] > 0
        assert "filename" in info
        processor.close()

    def test_get_page_image(self, sample_pdf):
        """Test getting page image."""
        import numpy as np

        processor = PDFProcessor(sample_pdf)
        img = processor.get_page_image(0)

        assert isinstance(img, np.ndarray)
        assert len(img.shape) == 3
        assert img.shape[2] == 3  # BGR format
        processor.close()

    def test_get_page_thumbnail(self, sample_pdf):
        """Test getting page thumbnail."""
        import numpy as np

        processor = PDFProcessor(sample_pdf)
        thumb = processor.get_page_thumbnail(0, size=150)

        assert isinstance(thumb, np.ndarray)
        assert len(thumb.shape) == 3
        processor.close()

    def test_get_page_image_invalid_index(self, sample_pdf):
        """Test getting page image with invalid index."""
        processor = PDFProcessor(sample_pdf)

        with pytest.raises(IndexError):
            processor.get_page_image(100)

        processor.close()

    def test_analyze_pages_blank_detection(self, blank_pdf):
        """Test analyzing pages for blank detection."""
        processor = PDFProcessor(blank_pdf)
        options = ProcessingOptions(remove_blank_pages=True)

        processor.analyze_pages(options)

        # Check that blank page was detected
        pages_info = processor.pages_info
        assert any(p.is_blank for p in pages_info)
        processor.close()

    def test_process_pdf(self, sample_pdf, tmp_path):
        """Test processing and saving PDF."""
        processor = PDFProcessor(sample_pdf)
        output_path = str(tmp_path / "output.pdf")
        options = ProcessingOptions(remove_blank_pages=False)

        processor.analyze_pages(options)
        result = processor.process_pdf(output_path, options)

        assert result.success is True
        assert Path(output_path).exists()
        assert result.total_pages_processed == 3
        processor.close()

    def test_process_pdf_remove_blank(self, blank_pdf, tmp_path):
        """Test processing with blank page removal."""
        processor = PDFProcessor(blank_pdf)
        output_path = str(tmp_path / "output_no_blank.pdf")
        options = ProcessingOptions(remove_blank_pages=True)

        processor.analyze_pages(options)
        result = processor.process_pdf(output_path, options)

        assert result.success is True
        assert len(result.blank_pages_removed) > 0
        assert result.total_pages_processed < result.total_pages_original
        processor.close()

    def test_context_manager(self, sample_pdf):
        """Test using PDFProcessor as context manager."""
        with PDFProcessor(sample_pdf) as processor:
            assert processor.total_pages == 3


class TestProcessingOptions:
    """Tests for ProcessingOptions."""

    def test_default_options(self):
        """Test default processing options."""
        options = ProcessingOptions()
        assert options.remove_blank_pages is False
        assert options.auto_correct_orientation is False
        assert options.blank_page_threshold == 0.10

    def test_custom_options(self):
        """Test custom processing options."""
        options = ProcessingOptions(
            remove_blank_pages=True,
            auto_correct_orientation=True,
            blank_page_threshold=0.90,
        )
        assert options.remove_blank_pages is True
        assert options.auto_correct_orientation is True
        assert options.blank_page_threshold == 0.90
