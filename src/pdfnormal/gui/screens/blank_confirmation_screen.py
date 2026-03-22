"""Blank pages confirmation screen."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QGridLayout, QMessageBox, QCheckBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import logging

from ..widgets import PageThumbnailWidget

logger = logging.getLogger(__name__)


class BlankPagesConfirmationScreen(QWidget):
    """Screen for confirming and selecting which blank pages to remove."""

    back_clicked = pyqtSignal()
    confirmed = pyqtSignal(list)  # List of page indices to remove

    def __init__(self, parent=None):
        """Initialize blank pages confirmation screen."""
        super().__init__(parent)
        self.page_widgets = []
        self.pages_info = None
        self.blank_page_indices = []
        self.selected_for_deletion = set()
        self.setup_ui()

    def setup_ui(self) -> None:
        """Set up the UI."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Confirm Blank Pages")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Instructions
        instructions = QLabel(
            "The following pages were detected as blank. Click on a page to toggle selection. "
            "Selected pages will be removed. Click 'Continue' to proceed."
        )
        instructions.setStyleSheet("color: #666; font-size: 11px;")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Select all / Deselect all buttons
        select_layout = QHBoxLayout()
        select_layout.addStretch()

        self.select_all_button = QPushButton("Select All")
        self.select_all_button.setMinimumHeight(32)
        self.select_all_button.setMinimumWidth(100)
        self.select_all_button.clicked.connect(self._select_all)
        select_layout.addWidget(self.select_all_button)

        self.deselect_all_button = QPushButton("Deselect All")
        self.deselect_all_button.setMinimumHeight(32)
        self.deselect_all_button.setMinimumWidth(100)
        self.deselect_all_button.clicked.connect(self._deselect_all)
        select_layout.addWidget(self.deselect_all_button)

        layout.addLayout(select_layout)

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

        # Summary info
        self.summary_label = QLabel()
        self.summary_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #333;")
        layout.addWidget(self.summary_label)

        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.back_button = QPushButton("Back")
        self.back_button.setMinimumHeight(40)
        self.back_button.setMinimumWidth(120)
        self.back_button.clicked.connect(self.back_clicked.emit)
        button_layout.addWidget(self.back_button)

        self.continue_button = QPushButton("Continue")
        self.continue_button.setMinimumHeight(40)
        self.continue_button.setMinimumWidth(150)
        self.continue_button.setStyleSheet("""
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
        self.continue_button.clicked.connect(self._on_continue_clicked)
        button_layout.addWidget(self.continue_button)

        layout.addLayout(button_layout)

    def load_blank_pages(self, processor, pages_info) -> None:
        """
        Load and display only the blank pages.

        Args:
            processor: PDFProcessor instance
            pages_info: List of PageInfo objects (all pages)
        """
        self.pages_info = pages_info
        self.blank_page_indices = []
        self.selected_for_deletion.clear()

        # Find all blank pages
        for idx, page_info in enumerate(pages_info):
            if page_info.is_blank:
                self.blank_page_indices.append(idx)
                self.selected_for_deletion.add(idx)

        # Clear existing widgets
        while self.thumbnails_layout.count():
            item = self.thumbnails_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.page_widgets.clear()

        if not self.blank_page_indices:
            # No blank pages
            self.summary_label.setText("No blank pages detected. Click 'Continue' to proceed.")
            self.continue_button.setEnabled(True)
            return

        # Create thumbnail widgets for blank pages only
        columns = 5
        for display_idx, page_idx in enumerate(self.blank_page_indices):
            widget = PageThumbnailWidget(page_idx)
            widget.clicked.connect(self._on_page_clicked)
            widget.set_selected(True)  # All selected by default for deletion
            self.page_widgets.append((widget, page_idx))

            row = display_idx // columns
            col = display_idx % columns
            self.thumbnails_layout.addWidget(widget, row, col)

            # Load thumbnail in background
            try:
                thumbnail = processor.get_page_thumbnail(page_idx, size=150)
                widget.set_thumbnail(thumbnail)
            except Exception as e:
                logger.error(f"Error loading thumbnail {page_idx}: {e}")

        # Add stretch rows after the last row
        last_row = (len(self.blank_page_indices) - 1) // columns + 1
        for i in range(last_row, last_row + 5):
            self.thumbnails_layout.setRowStretch(i, 1)

        self._update_summary()

    def _on_page_clicked(self, page_index: int) -> None:
        """Handle page click - toggle selection for deletion."""
        if page_index in self.selected_for_deletion:
            self.selected_for_deletion.remove(page_index)
        else:
            self.selected_for_deletion.add(page_index)

        # Update widget appearance
        for widget, page_idx in self.page_widgets:
            if page_idx == page_index:
                is_selected = page_index in self.selected_for_deletion
                widget.set_selected(is_selected)
                break

        self._update_summary()

    def _select_all(self) -> None:
        """Select all blank pages for deletion."""
        self.selected_for_deletion = set(self.blank_page_indices)
        for widget, page_idx in self.page_widgets:
            widget.set_selected(True)
        self._update_summary()

    def _deselect_all(self) -> None:
        """Deselect all blank pages (keep them)."""
        self.selected_for_deletion.clear()
        for widget, page_idx in self.page_widgets:
            widget.set_selected(False)
        self._update_summary()

    def _update_summary(self) -> None:
        """Update summary label with selection info."""
        total_blank = len(self.blank_page_indices)
        to_delete = len(self.selected_for_deletion)
        to_keep = total_blank - to_delete

        self.summary_label.setText(
            f"Total blank pages: {total_blank} | "
            f"Selected for deletion: {to_delete} | "
            f"Will keep: {to_keep}"
        )

    def _on_continue_clicked(self) -> None:
        """Handle continue button click."""
        to_delete = len(self.selected_for_deletion)
        total_blank = len(self.blank_page_indices)

        if to_delete == 0 and total_blank > 0:
            reply = QMessageBox.question(
                self,
                "No Pages Selected",
                "You haven't selected any blank pages for deletion. Continue anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        # Emit list of pages to delete
        pages_to_delete = sorted(list(self.selected_for_deletion))
        self.confirmed.emit(pages_to_delete)

    def clear(self) -> None:
        """Clear the screen."""
        self.page_widgets.clear()
        self.blank_page_indices.clear()
        self.selected_for_deletion.clear()
        self.pages_info = None

        # Clear widgets
        while self.thumbnails_layout.count():
            item = self.thumbnails_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.summary_label.setText("")
