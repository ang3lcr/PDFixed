"""Test configuration and fixtures."""

import pytest
from pathlib import Path
import tempfile
import fitz  # PyMuPDF

# Test data directory
TEST_DATA_DIR = Path(__file__).parent / "test_data"
TEST_DATA_DIR.mkdir(exist_ok=True)


@pytest.fixture
def sample_pdf():
    """Create a sample PDF for testing."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        pdf_path = tmp.name

    # Create a simple PDF with 3 pages
    doc = fitz.open()

    # Page 1: Normal text
    page = doc.new_page()
    page.insert_text((50, 50), "Test Page 1\nThis is a normal page.", fontsize=12)

    # Page 2: Mostly blank
    page = doc.new_page()
    page.insert_text((50, 50), " ", fontsize=12)  # Minimal text

    # Page 3: Text
    page = doc.new_page()
    page.insert_text((50, 50), "Test Page 3\nAnother normal page.", fontsize=12)

    doc.save(pdf_path)
    doc.close()

    yield pdf_path

    # Cleanup
    Path(pdf_path).unlink(missing_ok=True)


@pytest.fixture
def blank_pdf():
    """Create a PDF with blank pages."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        pdf_path = tmp.name

    doc = fitz.open()

    # Page 1: Normal
    page = doc.new_page()
    page.insert_text((50, 50), "Text Page", fontsize=12)

    # Page 2: Blank
    page = doc.new_page()

    # Page 3: Normal
    page = doc.new_page()
    page.insert_text((50, 50), "More Text", fontsize=12)

    doc.save(pdf_path)
    doc.close()

    yield pdf_path

    Path(pdf_path).unlink(missing_ok=True)
