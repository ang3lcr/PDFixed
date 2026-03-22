"""Results summary screen."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit,
    QGroupBox, QGridLayout, QFileDialog,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ResultsScreen(QWidget):
    """Screen displaying processing results."""

    export_requested = pyqtSignal(str)  # output_file_path
    done_clicked = pyqtSignal()

    def __init__(self, parent=None):
        """Initialize results screen."""
        super().__init__(parent)
        self.result = None
        self.setup_ui()

    def setup_ui(self) -> None:
        """Set up the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Title
        title = QLabel("Processing Complete ✓")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Summary group
        summary_group = QGroupBox("Summary")
        summary_layout = QGridLayout()

        self.original_pages_label = QLabel("-")
        summary_layout.addWidget(QLabel("Original Pages:"), 0, 0)
        summary_layout.addWidget(self.original_pages_label, 0, 1)

        self.processed_pages_label = QLabel("-")
        summary_layout.addWidget(QLabel("Processed Pages:"), 1, 0)
        summary_layout.addWidget(self.processed_pages_label, 1, 1)

        self.blank_removed_label = QLabel("-")
        summary_layout.addWidget(QLabel("Blank Pages Removed:"), 2, 0)
        summary_layout.addWidget(self.blank_removed_label, 2, 1)

        self.rotated_label = QLabel("-")
        summary_layout.addWidget(QLabel("Pages Rotated:"), 3, 0)
        summary_layout.addWidget(self.rotated_label, 3, 1)

        self.margins_label = QLabel("-")
        summary_layout.addWidget(QLabel("Pages with Margin Changes:"), 4, 0)
        summary_layout.addWidget(self.margins_label, 4, 1)

        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)

        # Details group
        details_group = QGroupBox("Details")
        details_layout = QVBoxLayout()

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(200)
        details_layout.addWidget(self.details_text)

        details_group.setLayout(details_layout)
        layout.addWidget(details_group)

        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.export_button = QPushButton("Export PDF")
        self.export_button.setMinimumHeight(40)
        self.export_button.setMinimumWidth(150)
        self.export_button.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        self.export_button.clicked.connect(self._on_export)
        button_layout.addWidget(self.export_button)

        self.done_button = QPushButton("Done")
        self.done_button.setMinimumHeight(40)
        self.done_button.setMinimumWidth(120)
        self.done_button.setStyleSheet("""
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
        self.done_button.clicked.connect(self.done_clicked.emit)
        button_layout.addWidget(self.done_button)

        layout.addLayout(button_layout)

    def display_result(self, result) -> None:
        """Display processing result."""
        self.result = result

        # Update labels
        self.original_pages_label.setText(str(result.total_pages_original))
        self.processed_pages_label.setText(str(result.total_pages_processed))
        self.blank_removed_label.setText(str(len(result.blank_pages_removed)))
        self.rotated_label.setText(str(len(result.pages_rotated)))
        self.margins_label.setText(str(len(result.pages_with_margin_changes)))

        # Build details text
        details = []
        if result.blank_pages_removed:
            details.append(f"Blank pages removed: {result.blank_pages_removed}")
        if result.pages_rotated:
            details.append(f"Pages rotated: {result.pages_rotated}")
        if result.pages_with_margin_changes:
            details.append(f"Pages with margin changes: {result.pages_with_margin_changes}")

        self.details_text.setText(
            "\n\n".join(details) if details else "No modifications applied."
        )

    def _on_export(self) -> None:
        """Handle export button click."""
        if not self.result:
            return

        # Get default filename
        default_filename = Path(self.result.output_file_path).stem + "_processed.pdf"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Processed PDF",
            default_filename,
            "PDF Files (*.pdf);;All Files (*)",
        )

        if file_path:
            self.export_requested.emit(file_path)

    def clear(self) -> None:
        """Clear the screen."""
        self.result = None
        self.original_pages_label.setText("-")
        self.processed_pages_label.setText("-")
        self.blank_removed_label.setText("-")
        self.rotated_label.setText("-")
        self.margins_label.setText("-")
        self.details_text.clear()
