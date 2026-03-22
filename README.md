# PDF Normal - Professional PDF Processing Application

A modern, user-friendly desktop application for processing and normalizing scanned PDF documents. Built with Python and PyQt6, it provides advanced features for handling large PDFs efficiently.

## ✨ Features

### 📄 Core Processing
- **Blank Page Detection**: Automatically detect and remove blank pages using pixel analysis
- **Orientation Correction**: Auto-detect and correct page rotations (90°, 180°, 270°)
- **Page Reordering**: Intuitive drag-and-drop interface for organizing pages
- **Margin Adjustment**: Interactive margin cropping with live preview
- **Batch Processing**: Handle 500+ page PDFs efficiently with optimized memory management

### 🖥️ User Interface
- **Modern, Responsive Design**: Built with PyQt6 for smooth animations and interactions
- **Multi-Screen Workflow**: 
  - Import screen with processing options
  - Page organizer with thumbnail grid
  - Interactive margin adjustment tool
  - Detailed results summary
- **Real-time Feedback**: Progress bars, visual feedback, and instant previews
- **Drag-and-Drop Support**: Intuitive page reordering

### ⚡ Performance
- **Lazy Loading**: Thumbnails load on-demand for responsiveness
- **Background Processing**: Heavy operations run in worker threads
- **Memory Optimization**: Efficient image handling for large files
- **Responsive UI**: All operations remain non-blocking

## 🚀 Getting Started

### Prerequisites
- Python 3.11 or higher
- pip
- Tesseract OCR (optional, for enhanced orientation detection)

### Installation

1. **Clone the repository**:
```bash
git clone https://github.com/yourusername/pdfnormal.git
cd pdfNormal
```

2. **Create virtual environment** (recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Install in development mode** (optional):
```bash
pip install -e .
```

### Running the Application

```bash
# Using module
python -m pdfnormal

# Or directly
python src/pdfnormal/main.py
```

## 📖 Usage Guide

### 1. Import PDF
- Click "Browse and Select PDF" to choose a document
- Select processing options:
  - **Remove Blank Pages**: Automatically detect and remove blank pages
  - **Auto-Correct Orientation**: Fix rotated pages
  - Adjust sensitivity thresholds as needed
- Click "Continue" to analyze the PDF

### 2. Organize Pages
- View all pages as thumbnails
- Drag and drop to reorder pages
- Right-click on pages to adjust margins individually
- Click "Continue to Preview" when satisfied

### 3. Adjust Margins (Optional)
- Interactive sliders for each margin (top, bottom, left, right)
- Live preview showing areas that will be removed (highlighted in red)
- Click "Apply Margins" to save changes

### 4. Review Results
- View summary of all changes made
- See count of removed pages, rotated pages, margin adjustments
- Export the processed PDF to your desired location

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/pdfnormal tests/

# Run specific test file
pytest tests/test_pdf_processor.py -v
```

### Test Coverage
- Core PDF processing functions
- Image analysis (blank detection, orientation)
- Data models
- Integration tests

## 📊 Project Structure

```
pdfNormal/
├── src/pdfnormal/
│   ├── __init__.py
│   ├── main.py                 # Application entry point
│   ├── core/
│   │   ├── __init__.py
│   │   ├── pdf_processor.py   # Main PDF operations
│   │   ├── image_processor.py # Image analysis utilities
│   │   └── models.py          # Data models
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── main_window.py     # Main application window
│   │   ├── workers.py         # Threading workers for background tasks
│   │   ├── screens/           # Individual screen components
│   │   │   ├── import_screen.py
│   │   │   ├── organizer_screen.py
│   │   │   ├── margin_screen.py
│   │   │   └── results_screen.py
│   │   ├── widgets/           # Custom GUI widgets
│   │   │   └── __init__.py
│   │   └── dialogs/           # Custom dialogs
│   └── utils/
│       ├── __init__.py
│       ├── constants.py       # Application constants
│       └── logger.py          # Logging configuration
├── tests/
│   ├── conftest.py            # Pytest fixtures
│   ├── test_pdf_processor.py
│   ├── test_image_processor.py
│   └── test_models.py
├── requirements.txt           # Production dependencies
├── requirements-dev.txt       # Development dependencies
├── pyproject.toml            # Project metadata and build config
├── setup.py                  # Setup script
├── .gitignore               # Git ignore rules
└── README.md                # This file
```

## 🔧 Development

### Code Style
- Follow PEP 8 guidelines
- Use type hints for function signatures
- Format with Black: `black .`
- Lint with Ruff: `ruff check .`

### Running Development Tools

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Format code
black .

# Lint code
ruff check . --fix

# Type checking
mypy src/pdfnormal

# Run tests with coverage
pytest --cov=src/pdfnormal tests/
```

## 📦 Dependencies

### Core Dependencies
- **PyQt6** (6.6.1): Modern GUI framework
- **PyMuPDF/fitz** (1.23.8): PDF processing
- **OpenCV** (4.8.1.78): Image processing
- **NumPy** (1.24.3): Numerical computing
- **Pillow** (10.1.0): Image manipulation
- **pytesseract** (0.3.10): OCR support

### Development Dependencies
- **pytest** (7.4.3): Testing framework
- **black** (23.12.0): Code formatter
- **ruff** (0.1.11): Fast Python linter
- **mypy** (1.7.1): Static type checker

## 🎯 Performance Considerations

- **Memory Management**: PDFs are processed page-by-page; full documents not loaded into memory
- **Lazy Loading**: Thumbnails are created on-demand
- **Threading**: Long operations run in background workers to keep UI responsive
- **Image Caching**: Processed images cached temporarily for performance
- **Optimization**: Built-in PDF compression for output files

## 🐛 Troubleshooting

### "Failed to load PDF"
- Ensure the PDF file is valid and not corrupted
- Check file permissions
- Try with a different PDF to isolate the issue

### Application freezes
- This shouldn't happen due to threading implementation
- If it does, check logs in `~/.pdfnormal/temp/pdfnormal.log`

### OCR not working
- Install Tesseract: `sudo apt-get install tesseract-ocr` (Linux) or download from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)
- Tesseract is optional; application works without it

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📧 Contact

For questions, issues, or suggestions, please open an issue on GitHub or contact the development team.

## 🙏 Acknowledgments

- PyQt6 for the excellent GUI framework
- PyMuPDF for robust PDF processing
- OpenCV for image processing capabilities
- The Python community for amazing libraries

---

Made with ❤️ by the PDF Normal Team
