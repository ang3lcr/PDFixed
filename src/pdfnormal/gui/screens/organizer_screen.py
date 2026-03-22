"""Page organizer screen for reordering pages."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QGridLayout, QProgressBar, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QDrag
import logging

from ..widgets import PageThumbnailWidget

logger = logging.getLogger(__name__)


class OrganizerScreen(QWidget):
    """Screen for organizing and reordering PDF pages."""

    pages_reordered = pyqtSignal(object)  # list of PageInfo in new order
    margin_adjustment_requested = pyqtSignal(int)  # page_index

    def __init__(self, parent=None):
        """Initialize organizer screen."""
        super().__init__(parent)
        self.page_widgets = []
        self.selected_page_index = None
        self.pages_info = None
        self.setup_ui()

    def setup_ui(self) -> None:
        """Set up the UI."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Organize Pages")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Instructions
        instructions = QLabel(
            "Drag and drop pages to reorder them. Right-click on a page to adjust margins."
        )
        instructions.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(instructions)

        # Scrollable thumbnails area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #ddd;
                background: #fafafa;
            }
        """)

        self.thumbnails_container = QWidget()
        self.thumbnails_layout = QGridLayout(self.thumbnails_container)
        self.thumbnails_layout.setSpacing(10)
        self.thumbnails_layout.setContentsMargins(10, 10, 10, 10)

        scroll_area.setWidget(self.thumbnails_container)
        layout.addWidget(scroll_area, 1)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.back_button = QPushButton("Back")
        self.back_button.setMinimumHeight(40)
        self.back_button.setMinimumWidth(120)
        self.back_button.clicked.connect(self.back_clicked)
        button_layout.addWidget(self.back_button)

        self.process_button = QPushButton("Continue to Preview")
        self.process_button.setMinimumHeight(40)
        self.process_button.setMinimumWidth(150)
        self.process_button.setStyleSheet("""
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
        self.process_button.clicked.connect(self.process_clicked)
        button_layout.addWidget(self.process_button)

        layout.addLayout(button_layout)

    def back_clicked(self):
        """Handle back button."""
        pass  # Connect in main window

    def process_clicked(self):
        """Handle process button."""
        pass  # Connect in main window

    def load_thumbnails(self, processor, pages_info) -> None:
        """
        Load thumbnails for all pages.

        Args:
            processor: PDFProcessor instance
            pages_info: List of PageInfo objects
        """
        self.pages_info = pages_info

        # Clear existing widgets
        while self.thumbnails_layout.count():
            item = self.thumbnails_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.page_widgets.clear()

        # Create thumbnail widgets
        columns = 5
        for page_idx in range(len(pages_info)):
            page_info = pages_info[page_idx]

            widget = PageThumbnailWidget(page_idx)
            widget.clicked.connect(self._on_page_clicked)
            widget.right_clicked.connect(self._on_page_right_clicked)
            self.page_widgets.append(widget)

            row = page_idx // columns
            col = page_idx % columns
            self.thumbnails_layout.addWidget(widget, row, col)

            # Load thumbnail in background
            try:
                thumbnail = processor.get_page_thumbnail(page_idx, size=150)
                widget.set_thumbnail(thumbnail)
            except Exception as e:
                logger.error(f"Error loading thumbnail {page_idx}: {e}")

        # Add stretch rows after the last row
        last_row = (len(pages_info) - 1) // columns + 1
        for i in range(last_row, last_row + 5):
            self.thumbnails_layout.setRowStretch(i, 1)

    def _on_page_clicked(self, page_index: int) -> None:
        """Handle page click."""
        # Update selection
        if self.selected_page_index is not None:
            self.page_widgets[self.selected_page_index].set_selected(False)

        self.selected_page_index = page_index
        self.page_widgets[page_index].set_selected(True)

    def _on_page_right_clicked(self, page_index: int) -> None:
        """Handle page right-click."""
        self.margin_adjustment_requested.emit(page_index)

    def get_pages_order(self):
        """Get current page order."""
        if self.pages_info:
            return self.pages_info
        return []

    def set_progress(self, current: int, total: int) -> None:
        """Update progress bar."""
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)

    def clear_progress(self) -> None:
        """Clear progress bar."""
        self.progress_bar.setVisible(False)
