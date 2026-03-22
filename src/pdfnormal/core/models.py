"""Data models for PDF processing."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class PageInfo:
    """Information about a single PDF page."""

    page_number: int
    original_index: int
    width: float
    height: float
    is_blank: bool = False
    rotation: int = 0  # 0, 90, 180, 270
    margins: dict = field(default_factory=lambda: {"top": 0, "bottom": 0, "left": 0, "right": 0})


@dataclass
class ProcessingOptions:
    """Options for PDF processing."""

    remove_blank_pages: bool = False
    auto_correct_orientation: bool = False
    blank_page_threshold: float = 0.10  # 10% dark pixels max = blank (using Otsu binarization)
    use_ocr_for_orientation: bool = False


@dataclass
class ProcessingResult:
    """Result of PDF processing."""

    success: bool
    total_pages_original: int
    total_pages_processed: int
    blank_pages_removed: List[int] = field(default_factory=list)
    pages_rotated: List[int] = field(default_factory=list)
    pages_with_margin_changes: List[int] = field(default_factory=list)
    output_file_path: str = ""
    error_message: str = ""
    pages_info: List[PageInfo] = field(default_factory=list)
