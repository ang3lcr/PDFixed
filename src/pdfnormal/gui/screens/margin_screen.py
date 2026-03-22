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

    def load_page(self, processor, page_index: int) -> None:
        """
        Load a page for margin adjustment.

        Args:
            processor: PDFProcessor instance
            page_index: Index of page to adjust
        """
        try:
            self.processor = processor
            self.page_index = page_index

            # Get full resolution page image
            image = processor.get_page_image(page_index, zoom=1.0)
            self.margin_widget.set_page_image(image)
        except Exception as e:
            logger.error(f"Error loading page for margin adjustment: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load page: {e}")

    def _on_reset(self) -> None:
        """Reset margins to zero."""
        self.margin_widget.reset_margins()

    def _on_confirm(self) -> None:
        """Confirm margin changes."""
        if self.page_index is not None:
            margins = self.margin_widget.get_margins()
            self.margins_confirmed.emit(self.page_index, margins)
            self.closed.emit()

    def _on_cancel(self) -> None:
        """Cancel without saving."""
        self.closed.emit()

    def _on_close(self) -> None:
        """Close the screen."""
        self.closed.emit()
