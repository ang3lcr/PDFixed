"""Margin adjustment screen."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import logging

from ..widgets import MarginAdjustmentWidget

logger = logging.getLogger(__name__)


class MarginAdjustmentScreen(QWidget):
    """Screen for adjusting page margins."""

    margins_confirmed = pyqtSignal(int, dict)  # page_index, margins
    closed = pyqtSignal()

    def __init__(self, parent=None):
        """Initialize margin adjustment screen."""
        super().__init__(parent)
        self.page_index = None
        self.processor = None
        self._preview_image_shape = None  # (height_px, width_px) used for unit conversion
        # (width_pdf_points, height_pdf_points) captured from the underlying
        # page *before* we optionally apply rotation. We convert the preview
        # sliders into margins in the same coordinate space PyMuPDF expects
        # for cropboxes.
        self._base_pdf_size = None
        # Rotation that was applied for rendering the preview (0, 90, 180, 270).
        self._preview_rotation = 0
        self.setup_ui()

    def setup_ui(self) -> None:
        """Set up the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Adjust Page Margins")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        header_layout.addWidget(title)
        header_layout.addStretch()

        close_button = QPushButton("×")
        close_button.setMaximumWidth(40)
        close_button.setMaximumHeight(40)
        close_button.clicked.connect(self._on_close)
        header_layout.addWidget(close_button)

        layout.addLayout(header_layout)

        # Margin adjustment widget
        self.margin_widget = MarginAdjustmentWidget()
        layout.addWidget(self.margin_widget, 1)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        reset_button = QPushButton("Reset")
        reset_button.setMinimumHeight(40)
        reset_button.setMinimumWidth(120)
        reset_button.clicked.connect(self._on_reset)
        button_layout.addWidget(reset_button)

        cancel_button = QPushButton("Cancel")
        cancel_button.setMinimumHeight(40)
        cancel_button.setMinimumWidth(120)
        cancel_button.clicked.connect(self._on_cancel)
        button_layout.addWidget(cancel_button)

        confirm_button = QPushButton("Apply Margins")
        confirm_button.setMinimumHeight(40)
        confirm_button.setMinimumWidth(150)
        confirm_button.setStyleSheet("""
            QPushButton {
                background-color: #107c10;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0d6107;
            }
        """)
        confirm_button.clicked.connect(self._on_confirm)
        button_layout.addWidget(confirm_button)

        layout.addLayout(button_layout)

    def load_page(
        self,
        processor,
        page_index: int,
        *,
        apply_rotation: bool = False,
    ) -> None:
        """
        Load a page for margin adjustment.

        Args:
            processor: PDFProcessor instance
            page_index: Index of page to adjust
            apply_rotation: If True, temporarily apply `page_info.rotation`
                before rendering the preview so the visual preview matches
                export behavior when `auto_correct_orientation` is enabled.
        """
        underlying_page = None
        underlying_original_rotation = None
        page_info = None

        try:
            self.processor = processor
            self.page_index = page_index

            self._preview_image_shape = None
            self._base_pdf_size = None
            self._preview_rotation = 0

            # Render with rotation (if requested) and capture the rotated page
            # dimensions to calibrate px->PDF-unit conversion.
            if hasattr(processor, "merged_pages_info"):
                # MultiPDFProcessor case
                page_info = processor.merged_pages_info[page_index]
                for p in processor.processors:
                    if page_info.source_pdf_path == str(p.pdf_path):
                        underlying_page = p.document[page_info.original_index]
                        break
            else:
                # PDFProcessor case
                if hasattr(processor, "pages_info") and page_index < len(processor.pages_info):
                    page_info = processor.pages_info[page_index]
                underlying_page = processor.document[page_index]

            if underlying_page is not None:
                underlying_original_rotation = underlying_page.rotation

                # Apply rotation for preview rendering (if requested).
                if apply_rotation and page_info is not None and page_info.rotation != 0:
                    underlying_page.set_rotation(page_info.rotation)
                    self._preview_rotation = int(page_info.rotation)
                else:
                    self._preview_rotation = 0

                # Capture geometry from the same rotated state that was used
                # to render the preview image. This ensures pixel->PDF
                # conversion uses a consistent axis space.
                rect = underlying_page.rect
                self._base_pdf_size = (float(rect.width), float(rect.height))

            # Get full resolution page image
            image = processor.get_page_image(page_index, zoom=1.0)
            if image is not None:
                height_px, width_px = image.shape[:2]
                self._preview_image_shape = (height_px, width_px)
            self.margin_widget.set_page_image(image)
        except Exception as e:
            logger.error(f"Error loading page for margin adjustment: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load page: {e}")
        finally:
            # Restore rotation after rendering (so we don't mutate processor
            # state across UI operations).
            if (
                underlying_page is not None
                and underlying_original_rotation is not None
                and apply_rotation
                and page_info is not None
                and page_info.rotation != 0
            ):
                try:
                    underlying_page.set_rotation(underlying_original_rotation)
                except Exception:
                    # Preview restoration failures shouldn't crash the UI.
                    pass

    def _on_reset(self) -> None:
        """Reset margins to zero."""
        self.margin_widget.reset_margins()

    def _on_confirm(self) -> None:
        """Confirm margin changes."""
        if self.page_index is not None:
            margins_px = self.margin_widget.get_margins()

            # Convert preview-image pixels -> PDF page coordinates.
            # `compute_safe_cropbox` expects margins in the same coordinate
            # system as `page.rect` (PyMuPDF points), not UI pixels.
            margins_pdf = margins_px
            try:
                if (
                    self._preview_image_shape is not None
                    and self._base_pdf_size is not None
                    and self.processor is not None
                ):
                    height_px, width_px = self._preview_image_shape
                    pdf_w, pdf_h = self._base_pdf_size

                    if height_px > 0 and width_px > 0 and pdf_w > 0 and pdf_h > 0:
                        top_px = float(margins_px.get("top", 0) or 0)
                        bottom_px = float(margins_px.get("bottom", 0) or 0)
                        left_px = float(margins_px.get("left", 0) or 0)
                        right_px = float(margins_px.get("right", 0) or 0)

                        # Convert preview-image pixels -> PDF points using a
                        # consistent per-axis scale.
                        # Edge semantics (top/bottom vs y0/y1) are handled in
                        # `compute_safe_cropbox`.
                        scale_x = float(pdf_w) / float(width_px)
                        scale_y = float(pdf_h) / float(height_px)

                        def _clamp_points(v: float) -> float:
                            return max(0.0, float(v))

                        margins_pdf = {
                            "top": _clamp_points(top_px * scale_y),
                            "bottom": _clamp_points(bottom_px * scale_y),
                            "left": _clamp_points(left_px * scale_x),
                            "right": _clamp_points(right_px * scale_x),
                        }
                elif self._preview_image_shape is not None and self.processor is not None:
                    # Fallback: do simple direct scaling if we can't calibrate axes.
                    height_px, width_px = self._preview_image_shape
                    if height_px > 0 and width_px > 0:
                        if hasattr(self.processor, "merged_pages_info"):
                            page_info = self.processor.merged_pages_info[self.page_index]
                        else:
                            page_info = self.processor.pages_info[self.page_index]

                        scale_x = float(page_info.width) / float(width_px)
                        scale_y = float(page_info.height) / float(height_px)

                        margins_pdf = {
                            "top": max(0.0, float(margins_px.get("top", 0)) * scale_y),
                            "bottom": max(0.0, float(margins_px.get("bottom", 0)) * scale_y),
                            "left": max(0.0, float(margins_px.get("left", 0)) * scale_x),
                            "right": max(0.0, float(margins_px.get("right", 0)) * scale_x),
                        }
            except Exception as e:
                # Fallback: preserve the old behaviour (pixels-as-units) if
                # conversion fails for any reason.
                logger.error(f"Error converting margin units: {e}")

            self.margins_confirmed.emit(self.page_index, margins_pdf)
            self.closed.emit()

    def _on_cancel(self) -> None:
        """Cancel without saving."""
        self.closed.emit()

    def _on_close(self) -> None:
        """Close the screen."""
        self.closed.emit()
