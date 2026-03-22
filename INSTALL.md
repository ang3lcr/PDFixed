# Installation Instructions

## Quick Start

### 1. Prerequisites
- Python 3.11 or higher
- pip (Python package manager)
- Virtual environment recommended

### 2. Clone or Download Project
```bash
cd pdfNormal
```

### 3. Create Virtual Environment
```bash
# On macOS/Linux
python3 -m venv venv
source venv/bin/activate

# On Windows
python -m venv venv
venv\Scripts\activate
```

### 4. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Run the Application
```bash
python -m pdfnormal
```

## Installation for Development

### 1. Install Development Dependencies
```bash
pip install -r requirements-dev.txt
```

### 2. Install Package in Editable Mode
```bash
pip install -e .
```

### 3. Run Tests
```bash
pytest tests/
pytest --cov=src/pdfnormal tests/  # With coverage
```

### 4. Format and Lint Code
```bash
black .
ruff check . --fix
```

## Optional: Tesseract OCR

For enhanced orientation detection (optional):

### On Ubuntu/Debian:
```bash
sudo apt-get install tesseract-ocr
```

### On macOS:
```bash
brew install tesseract
```

### On Windows:
Download installer from: https://github.com/UB-Mannheim/tesseract/wiki

## Troubleshooting

### Module not found errors
```bash
# Ensure you're in the virtual environment
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

### PyQt6 display issues on Linux
```bash
# Install Qt libraries
sudo apt-get install libqt6gui6 libqt6widgets6
```

### PDF processing errors
- Ensure PDF file is valid (not corrupted)
- Check file permissions
- Try with a simpler PDF first

## Running Tests

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_pdf_processor.py -v

# With coverage report
pytest tests/ --cov=src/pdfnormal --cov-report=html
```

## Building Executable (Optional)

To create a standalone executable:

```bash
pip install pyinstaller

# Build executable
pyinstaller --name "PDF Normal" \
    --windowed \
    --icon=icon.ico \
    --add-data "src/pdfnormal:pdfnormal" \
    src/pdfnormal/main.py
```

Executable will be in the `dist/` directory.

## Uninstall

```bash
# Remove virtual environment
deactivate
rm -rf venv  # macOS/Linux
rmdir /s venv  # Windows
```
