"""Tests for data models."""

from pdfnormal.core import PageInfo, ProcessingOptions, ProcessingResult


class TestPageInfo:
    """Tests for PageInfo model."""

    def test_page_info_creation(self):
        """Test creating a PageInfo object."""
        page = PageInfo(page_number=1, original_index=0, width=612, height=792)

        assert page.page_number == 1
        assert page.original_index == 0
        assert page.width == 612
        assert page.height == 792
        assert page.is_blank is False
        assert page.rotation == 0
        assert page.margins == {"top": 0, "bottom": 0, "left": 0, "right": 0}

    def test_page_info_with_margins(self):
        """Test PageInfo with custom margins."""
        margins = {"top": 10, "bottom": 10, "left": 20, "right": 20}
        page = PageInfo(
            page_number=1,
            original_index=0,
            width=612,
            height=792,
            margins=margins,
        )

        assert page.margins == margins


class TestProcessingOptions:
    """Tests for ProcessingOptions model."""

    def test_default_options(self):
        """Test default options."""
        options = ProcessingOptions()

        assert options.remove_blank_pages is False
        assert options.auto_correct_orientation is False
        assert options.blank_page_threshold == 0.10
        assert options.use_ocr_for_orientation is False

    def test_custom_options(self):
        """Test custom options."""
        options = ProcessingOptions(
            remove_blank_pages=True,
            auto_correct_orientation=True,
            blank_page_threshold=0.90,
            use_ocr_for_orientation=True,
        )

        assert options.remove_blank_pages is True
        assert options.auto_correct_orientation is True
        assert options.blank_page_threshold == 0.90
        assert options.use_ocr_for_orientation is True


class TestProcessingResult:
    """Tests for ProcessingResult model."""

    def test_result_creation(self):
        """Test creating a ProcessingResult."""
        result = ProcessingResult(
            success=True,
            total_pages_original=10,
            total_pages_processed=9,
            blank_pages_removed=[5],
            pages_rotated=[2, 3],
        )

        assert result.success is True
        assert result.total_pages_original == 10
        assert result.total_pages_processed == 9
        assert result.blank_pages_removed == [5]
        assert result.pages_rotated == [2, 3]
        assert result.error_message == ""

    def test_result_failure(self):
        """Test creating a failed result."""
        result = ProcessingResult(
            success=False,
            total_pages_original=10,
            total_pages_processed=0,
            error_message="Test error",
        )

        assert result.success is False
        assert result.error_message == "Test error"
