"""Main application window."""

from PyQt6.QtWidgets import (
    QMainWindow, QStackedWidget, QDialog, QVBoxLayout, QLabel,
    QMessageBox, QProgressDialog,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QIcon
from pathlib import Path
import logging
import shutil

from ..core import PDFProcessor, ProcessingOptions
from .workers import (
    PDFLoadWorker, PDFAnalysisWorker, PDFProcessingWorker, ThumbnailWorker
)
from .screens.import_screen import ImportScreen
from .screens.organizer_screen import OrganizerScreen
from .screens.blank_confirmation_screen import BlankPagesConfirmationScreen
from .screens.margin_screen import MarginAdjustmentScreen
from .screens.results_screen import ResultsScreen
from ..utils.constants import APP_NAME, APP_VERSION, WINDOW_WIDTH, WINDOW_HEIGHT, TEMP_DIR

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        """Initialize main window."""
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} - {APP_VERSION}")
        self.setGeometry(100, 100, WINDOW_WIDTH, WINDOW_HEIGHT)

        self.processor = None
        self.processing_options = None
        self.current_output_path = None
        self.pages_to_remove = None  # Pages selected for deletion by user

        # Create main stack widget
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # Create screens
        self.import_screen = ImportScreen()
        self.organizer_screen = OrganizerScreen()
        self.blank_confirmation_screen = BlankPagesConfirmationScreen()
        self.margin_screen = MarginAdjustmentScreen()
        self.results_screen = ResultsScreen()

        # Add screens to stack
        self.stack.addWidget(self.import_screen)        # Index 0
        self.stack.addWidget(self.organizer_screen)     # Index 1
        self.stack.addWidget(self.blank_confirmation_screen)  # Index 2
        self.stack.addWidget(self.margin_screen)        # Index 3
        self.stack.addWidget(self.results_screen)       # Index 4

        # Connect signals
        self._connect_signals()

        # Show first screen
        self.stack.setCurrentIndex(0)

        # Workers
        self.load_worker = None
        self.analysis_worker = None
        self.processing_worker = None

        logger.info(f"Application started: {APP_NAME} {APP_VERSION}")

    def _connect_signals(self) -> None:
        """Connect all signals."""
        # Import screen
        self.import_screen.file_selected.connect(self._on_file_selected)
        self.import_screen.analysis_started.connect(self._on_analysis_started)

        # Organizer screen
        self.organizer_screen.back_button.clicked.connect(self._on_organizer_back)
        self.organizer_screen.process_button.clicked.connect(self._on_organizer_process)
        self.organizer_screen.margin_adjustment_requested.connect(self._on_margin_adjustment)

        # Blank pages confirmation screen
        self.blank_confirmation_screen.back_clicked.connect(self._on_blank_confirmation_back)
        self.blank_confirmation_screen.confirmed.connect(self._on_blank_confirmation_confirmed)

        # Margin screen
        self.margin_screen.margins_confirmed.connect(self._on_margins_confirmed)
        self.margin_screen.closed.connect(self._on_margin_screen_closed)

        # Results screen
        self.results_screen.export_requested.connect(self._on_export_requested)
        self.results_screen.done_clicked.connect(self._on_done)

    def _on_file_selected(self, pdf_path: str) -> None:
        """Handle file selection."""
        try:
            # Load PDF in background worker
            self.load_worker = PDFLoadWorker(pdf_path)
            self.load_worker.finished.connect(self._on_pdf_loaded)
            self.load_worker.error.connect(self._on_pdf_load_error)
            self.load_worker.start()

            self.import_screen.progress_label.setText("Loading PDF...")
        except Exception as e:
            logger.error(f"Error loading PDF: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load PDF: {e}")

    def _on_pdf_loaded(self, processor: PDFProcessor) -> None:
        """Handle PDF loaded."""
        try:
            self.processor = processor
            file_info = processor.get_file_info()
            self.import_screen.update_file_info(file_info)
            self.import_screen.progress_label.setText("Ready")
            logger.info(f"PDF loaded successfully: {file_info['total_pages']} pages")
        except Exception as e:
            logger.error(f"Error processing loaded PDF: {e}")
            QMessageBox.critical(self, "Error", f"Error processing PDF: {e}")

    def _on_pdf_load_error(self, error: str) -> None:
        """Handle PDF load error."""
        logger.error(f"PDF load error: {error}")
        error_message = f"""Failed to load PDF

Error: {error}

Please ensure:
- The file is a valid PDF document
- The file is not corrupted
- You have read permissions for the file"""
        QMessageBox.critical(self, "PDF Load Failed", error_message)
        self.import_screen.progress_label.setText("Error")

    def _on_analysis_started(self, options: ProcessingOptions) -> None:
        """Handle analysis start."""
        try:
            if not self.processor:
                QMessageBox.warning(self, "Warning", "No PDF loaded")
                return

            self.processing_options = options

            # Start analysis in background
            self.analysis_worker = PDFAnalysisWorker(self.processor, options)
            self.analysis_worker.progress.connect(self.import_screen.set_progress)
            self.analysis_worker.finished.connect(self._on_analysis_finished)
            self.analysis_worker.error.connect(self._on_analysis_error)
            self.analysis_worker.start()

            self.import_screen.browse_button.setEnabled(False)
            self.import_screen.start_button.setEnabled(False)

        except Exception as e:
            logger.error(f"Error starting analysis: {e}")
            QMessageBox.critical(self, "Error", f"Error analyzing PDF: {e}")

    def _on_analysis_finished(self) -> None:
        """Handle analysis completion."""
        try:
            logger.info("PDF analysis completed")
            self.import_screen.browse_button.setEnabled(True)

            # Check if there are blank pages and user wants to remove them
            has_blank_pages = any(p.is_blank for p in self.processor.pages_info)

            if has_blank_pages and self.processing_options.remove_blank_pages:
                # Show blank pages confirmation screen
                self.blank_confirmation_screen.load_blank_pages(
                    self.processor, self.processor.pages_info
                )
                self.stack.setCurrentIndex(2)
            else:
                # Move to organizer screen
                self.organizer_screen.load_thumbnails(
                    self.processor, self.processor.pages_info
                )
                self.stack.setCurrentIndex(1)

        except Exception as e:
            logger.error(f"Error finishing analysis: {e}")
            QMessageBox.critical(self, "Error", f"Error: {e}")

    def _on_analysis_error(self, error: str) -> None:
        """Handle analysis error."""
        logger.error(f"Analysis error: {error}")
        QMessageBox.critical(self, "Error", f"Analysis failed:\n{error}")
        self.import_screen.browse_button.setEnabled(True)
        self.import_screen.start_button.setEnabled(True)

    def _on_blank_confirmation_back(self) -> None:
        """Handle back from blank confirmation screen."""
        # Load organizer screen for page review
        self.organizer_screen.load_thumbnails(
            self.processor, self.processor.pages_info
        )
        self.stack.setCurrentIndex(1)

    def _on_blank_confirmation_confirmed(self, pages_to_remove: list) -> None:
        """Handle blank pages confirmation."""
        try:
            logger.info(f"User confirmed removal of {len(pages_to_remove)} blank pages")
            self.pages_to_remove = pages_to_remove

            # Load organizer screen for final review before processing
            self.organizer_screen.load_thumbnails(
                self.processor, self.processor.pages_info
            )
            self.stack.setCurrentIndex(1)

        except Exception as e:
            logger.error(f"Error confirming blank pages: {e}")
            QMessageBox.critical(self, "Error", f"Error: {e}")

    def _on_organizer_back(self) -> None:
        """Handle back from organizer."""
        if self.processor:
            self.processor.close()
        self.processor = None
        self.import_screen.clear()
        self.stack.setCurrentIndex(0)

    def _on_organizer_process(self) -> None:
        """Handle process from organizer."""
        try:
            # Prepare output file
            self.current_output_path = str(
                TEMP_DIR / f"processed_{Path(self.processor.pdf_path).stem}.pdf"
            )

            pages_info = self.organizer_screen.get_pages_order()

            # If user selected specific blank pages to remove, update pages_info
            if self.pages_to_remove is not None:
                pages_to_keep = set(range(len(pages_info))) - set(self.pages_to_remove)
                for idx, page_info in enumerate(pages_info):
                    if idx not in pages_to_keep:
                        page_info.is_blank = True
                    else:
                        page_info.is_blank = False

            # Start processing in background
            self.processing_worker = PDFProcessingWorker(
                self.processor,
                self.current_output_path,
                self.processing_options,
                pages_info,
            )
            self.processing_worker.progress.connect(self.organizer_screen.set_progress)
            self.processing_worker.finished.connect(self._on_processing_finished)
            self.processing_worker.error.connect(self._on_processing_error)
            self.processing_worker.start()

            self.organizer_screen.process_button.setEnabled(False)
            self.organizer_screen.back_button.setEnabled(False)

        except Exception as e:
            logger.error(f"Error starting processing: {e}")
            QMessageBox.critical(self, "Error", f"Error processing PDF: {e}")

    def _on_processing_finished(self, result) -> None:
        """Handle processing completion."""
        try:
            logger.info(f"Processing completed: {result.total_pages_processed} pages")

            self.organizer_screen.process_button.setEnabled(True)
            self.organizer_screen.back_button.setEnabled(True)
            self.organizer_screen.clear_progress()

            # Display results
            self.results_screen.display_result(result)
            self.stack.setCurrentIndex(4)

        except Exception as e:
            logger.error(f"Error finishing processing: {e}")
            QMessageBox.critical(self, "Error", f"Error: {e}")

    def _on_processing_error(self, error: str) -> None:
        """Handle processing error."""
        logger.error(f"Processing error: {error}")
        QMessageBox.critical(self, "Error", f"Processing failed:\n{error}")
        self.organizer_screen.process_button.setEnabled(True)
        self.organizer_screen.back_button.setEnabled(True)

    def _on_margin_adjustment(self, page_index: int) -> None:
        """Handle margin adjustment request."""
        try:
            self.margin_screen.load_page(self.processor, page_index)
            self.stack.setCurrentIndex(3)
        except Exception as e:
            logger.error(f"Error loading margin adjustment: {e}")
            QMessageBox.critical(self, "Error", f"Error: {e}")

    def _on_margins_confirmed(self, page_index: int, margins: dict) -> None:
        """Handle margin confirmation."""
        try:
            if self.processor and page_index < len(self.processor.pages_info):
                self.processor.pages_info[page_index].margins = margins
                logger.info(f"Margins set for page {page_index + 1}: {margins}")
        except Exception as e:
            logger.error(f"Error setting margins: {e}")

    def _on_margin_screen_closed(self) -> None:
        """Handle margin screen close."""
        self.stack.setCurrentIndex(1)

    def _on_export_requested(self, export_path: str) -> None:
        """Handle export request."""
        try:
            if self.current_output_path and Path(self.current_output_path).exists():
                shutil.copy(self.current_output_path, export_path)
                logger.info(f"PDF exported to: {export_path}")
                QMessageBox.information(
                    self, "Success", f"PDF successfully exported to:\n{export_path}"
                )
            else:
                QMessageBox.warning(self, "Warning", "Output file not found")
        except Exception as e:
            logger.error(f"Error exporting PDF: {e}")
            QMessageBox.critical(self, "Error", f"Export failed:\n{e}")

    def _on_done(self) -> None:
        """Handle done button."""
        # Clean up
        if self.processor:
            self.processor.close()

        # Reset to import screen
        self.processor = None
        self.processing_options = None
        self.import_screen.clear()
        self.results_screen.clear()
        self.stack.setCurrentIndex(0)

    def closeEvent(self, event):
        """Handle window close."""
        try:
            if self.processor:
                self.processor.close()

            # Clean up temp files
            import glob
            for temp_file in glob.glob(str(TEMP_DIR / "processed_*.pdf")):
                try:
                    Path(temp_file).unlink()
                except:
                    pass

            logger.info("Application closed")
            event.accept()
        except Exception as e:
            logger.error(f"Error closing application: {e}")
            event.accept()
