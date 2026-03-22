"""Import screen for selecting and importing PDF files."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox,
    QFileDialog, QGroupBox, QGridLayout, QSpinBox, QProgressBar,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import logging

from ...core import ProcessingOptions

logger = logging.getLogger(__name__)


class ImportScreen(QWidget):
    """Screen for importing PDF and selecting processing options."""

    file_selected = pyqtSignal(str)  # pdf_path
    analysis_started = pyqtSignal(object)  # ProcessingOptions

    def __init__(self, parent=None):
        """Initialize import screen."""
        super().__init__(parent)
        self.pdf_path = None
        self.setup_ui()

    def setup_ui(self) -> None:
        """Set up the UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)

        # Title
        title = QLabel("Import PDF Document")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # File info group
        file_group = QGroupBox("File Information")
        file_layout = QGridLayout()

        self.file_label = QLabel("No file selected")
        self.file_label.setWordWrap(True)
        file_layout.addWidget(QLabel("File:"), 0, 0)
        file_layout.addWidget(self.file_label, 0, 1)

        self.pages_label = QLabel("-")
        file_layout.addWidget(QLabel("Pages:"), 1, 0)
        file_layout.addWidget(self.pages_label, 1, 1)

        self.size_label = QLabel("-")
        file_layout.addWidget(QLabel("Size:"), 2, 0)
        file_layout.addWidget(self.size_label, 2, 1)

        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # File selection button
        button_layout = QHBoxLayout()
        self.browse_button = QPushButton("Browse and Select PDF")
        self.browse_button.setMinimumHeight(40)
        self.browse_button.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """)
        self.browse_button.clicked.connect(self._on_browse_clicked)
        button_layout.addWidget(self.browse_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        # Processing options group
        options_group = QGroupBox("Processing Options")
        options_layout = QVBoxLayout()

        self.blank_checkbox = QCheckBox("Remove Blank Pages")
        self.blank_checkbox.setChecked(False)
        options_layout.addWidget(self.blank_checkbox)

        # Blank page threshold
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("Blank Page Sensitivity (% dark pixels):"))
        self.threshold_spinbox = QSpinBox()
        self.threshold_spinbox.setRange(1, 30)  # 1% to 30% dark pixels
        self.threshold_spinbox.setValue(10)  # Default 10% dark pixels
        self.threshold_spinbox.setSuffix("%")
        threshold_layout.addWidget(self.threshold_spinbox)
        threshold_layout.addStretch()
        options_layout.addLayout(threshold_layout)

        self.orientation_checkbox = QCheckBox("Auto-Correct Page Orientation")
        self.orientation_checkbox.setChecked(False)
        options_layout.addWidget(self.orientation_checkbox)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # Progress bar
        self.progress_label = QLabel("Ready")
        layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        layout.addStretch()

        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.start_button = QPushButton("Continue")
        self.start_button.setMinimumHeight(40)
        self.start_button.setMinimumWidth(150)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #107c10;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover:!pressed {
                background-color: #0d6107;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
        """)
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self._on_start_clicked)
        button_layout.addWidget(self.start_button)

        layout.addLayout(button_layout)

    def _on_browse_clicked(self) -> None:
        """Handle browse button click."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select PDF File", "", "PDF Files (*.pdf);;All Files (*)"
        )

        if file_path:
            self.pdf_path = file_path
            self.file_label.setText(file_path.split("/")[-1])
            self.file_selected.emit(file_path)

    def _on_start_clicked(self) -> None:
        """Handle start button click."""
        if not self.pdf_path:
            return

        options = ProcessingOptions(
            remove_blank_pages=self.blank_checkbox.isChecked(),
            auto_correct_orientation=self.orientation_checkbox.isChecked(),
            blank_page_threshold=self.threshold_spinbox.value() / 100.0,
        )

        self.analysis_started.emit(options)

    def update_file_info(self, file_info: dict) -> None:
        """Update file information display."""
        try:
            self.pages_label.setText(str(file_info.get("total_pages", "-")))
            size_mb = file_info.get("size_mb", 0)
            self.size_label.setText(f"{size_mb:.2f} MB")
            self.start_button.setEnabled(True)
        except Exception as e:
            logger.error(f"Error updating file info: {e}")

    def set_progress(self, current: int, total: int) -> None:
        """Update progress bar."""
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.progress_label.setText(f"Analyzing: {current}/{total} pages")

    def clear(self) -> None:
        """Clear the screen."""
        self.pdf_path = None
        self.file_label.setText("No file selected")
        self.pages_label.setText("-")
        self.size_label.setText("-")
        self.blank_checkbox.setChecked(False)
        self.orientation_checkbox.setChecked(False)
        self.threshold_spinbox.setValue(10)
        self.progress_bar.setVisible(False)
        self.progress_label.setText("Ready")
        self.start_button.setEnabled(False)
