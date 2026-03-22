"""Main application entry point."""

import sys
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from pdfnormal.utils.logger import setup_logger
from pdfnormal.gui.main_window import MainWindow


def main():
    """Run the application."""
    # Setup logging
    logger = setup_logger("pdfnormal", logging.DEBUG)  # Changed to DEBUG for more info
    logger.info("Application started")

    try:
        # Create application
        app = QApplication(sys.argv)
        app.setApplicationName("PDF Normal")
        app.setApplicationVersion("1.0.0")

        logger.info("Creating main window")
        # Create and show main window
        window = MainWindow()
        window.show()

        logger.info("Application window shown")
        sys.exit(app.exec())

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
