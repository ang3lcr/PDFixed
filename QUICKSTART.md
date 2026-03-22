# Quick Start Guide

## 30-Second Setup

```bash
# 1. Navigate to project
cd pdfNormal

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # or: venv\Scripts\activate on Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run application
python -m pdfnormal
```

## Your First Run

1. **Click "Browse and Select PDF"** - Choose a PDF file
2. **Select Processing Options**:
   - ☑ Remove Blank Pages (optional)
   - ☑ Auto-Correct Orientation (optional)
3. **Click "Continue"** - Analyzes the PDF
4. **Organize Pages** - Reorder if needed, right-click to adjust margins
5. **Click "Continue to Preview"** - Process the PDF
6. **Export Results** - Save your processed PDF

## For Developers

### Initial Setup

```bash
# Install with dev dependencies
pip install -r requirements-dev.txt
pip install -e .

# Run tests to verify everything works
pytest tests/ -v

# Format and lint code
black .
ruff check . --fix
```

### Common Development Tasks

```bash
# Run application in debug mode
python -m pdfnormal

# Run tests with coverage
pytest tests/ --cov=src/pdfnormal

# Format all code
black .

# Check code quality
ruff check .

# Type checking
mypy src/pdfnormal
```

### Project Structure Quick Reference

```
src/pdfnormal/
├── main.py              ← Entry point
├── core/
│   ├── pdf_processor.py ← Main PDF logic
│   ├── image_processor.py ← Image analysis
│   └── models.py        ← Data classes
├── gui/
│   ├── main_window.py   ← Application controller
│   ├── workers.py       ← Background threads
│   ├── screens/         ← UI screens
│   └── widgets/         ← Reusable components
└── utils/
    ├── constants.py     ← Configuration
    └── logger.py        ← Logging setup
```

## Troubleshooting

### "No module named 'pdfnormal'"
- Make sure you're in the virtual environment: `source venv/bin/activate`
- Reinstall: `pip install -r requirements.txt`

### "PyQt6 not found"
- Install it: `pip install PyQt6==6.6.1`

### Tests failing
- Ensure all dependencies are installed: `pip install -r requirements-dev.txt`
- Run tests with verbose output: `pytest tests/ -v`

## Next Steps

- Read [README.md](README.md) for full feature overview
- Check [INSTALL.md](INSTALL.md) for detailed installation
- See [ARCHITECTURE.md](ARCHITECTURE.md) to understand design
- Review [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines
- Follow [DEVELOPMENT.md](DEVELOPMENT.md) for dev workflow

## Getting Help

1. Check existing [GitHub Issues](https://github.com/yourusername/pdfnormal/issues)
2. Read [CONTRIBUTING.md](CONTRIBUTING.md#troubleshooting)
3. Review [ARCHITECTURE.md](ARCHITECTURE.md) for design questions
4. Check test files for usage examples

## Performance Tips

- Use test PDFs while developing (start small!)
- Enable debug logging to track issues
- Profile performance with `pytest --durations=10`
- Check logs in `~/.pdfnormal/temp/pdfnormal.log`

---

**Happy PDF Processing! 🎉**
