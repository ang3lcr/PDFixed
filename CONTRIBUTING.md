# Contributing Guide

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/pdfnormal.git`
3. Create a branch: `git checkout -b feature/your-feature-name`

## Development Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dev dependencies
pip install -r requirements-dev.txt
pip install -e .
```

## Code Standards

### Style Guide
- Follow **PEP 8** conventions
- Use **type hints** for all function signatures
- Maximum line length: 100 characters
- Use f-strings for formatting

### Formatting
```bash
# Format with Black
black .

# Lint with Ruff
ruff check . --fix

# Type checking
mypy src/pdfnormal
```

### Naming Conventions
- Classes: `PascalCase` (e.g., `PDFProcessor`)
- Functions/methods: `snake_case` (e.g., `process_pdf`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_PAGES`)
- Private members: prefix with `_` (e.g., `_internal_method`)

## Testing

### Run Tests
```bash
# All tests
pytest tests/ -v

# Specific test
pytest tests/test_pdf_processor.py::TestPDFProcessor::test_init_with_valid_pdf -v

# With coverage
pytest --cov=src/pdfnormal tests/
```

### Writing Tests
- Place tests in `tests/` directory
- Use `test_` prefix for test files
- Use `Test` prefix for test classes
- Use descriptive names for test methods

Example:
```python
def test_blank_page_detection_with_high_threshold():
    """Test that blank detection respects threshold parameter."""
    # Arrange
    image = create_blank_image()
    
    # Act
    result = ImageProcessor.detect_blank_page(image, threshold=0.99)
    
    # Assert
    assert result is False
```

## Commit Guidelines

- Use clear, descriptive commit messages
- Reference issues: "Fix #123"
- Use imperative mood: "Add feature" not "Added feature"
- Prefix with type: `feat:`, `fix:`, `docs:`, `test:`, etc.

Examples:
```
feat: Add margin adjustment with live preview
fix: Correct blank page detection threshold
docs: Update installation instructions
test: Add tests for orientation detection
refactor: Simplify PDF processing pipeline
```

## Pull Request Process

1. **Before submitting**:
   - Run tests: `pytest tests/ -v`
   - Format code: `black .`
   - Run linter: `ruff check . --fix`

2. **PR description** should include:
   - What problem does this solve?
   - How does it solve it?
   - Testing information
   - Screenshots (if UI changes)

3. **PR checklist**:
   - [ ] Tests pass
   - [ ] Code is formatted
   - [ ] Documentation updated
   - [ ] No breaking changes (or clearly documented)

## Documentation

### Docstrings
Use Google-style docstrings:

```python
def process_pdf(self, output_path: str, options: ProcessingOptions) -> ProcessingResult:
    """
    Process PDF with selected options and save to output file.
    
    Args:
        output_path: Path for output PDF
        options: Processing options
        
    Returns:
        ProcessingResult with details of changes
        
    Raises:
        ValueError: If output path is invalid
    """
```

### Code Comments
- Be helpful and clear
- Explain *why*, not *what*
- Keep comments up-to-date with code
- Remove commented-out code before committing

## Project Architecture

### Core Module (`src/pdfnormal/core/`)
- `pdf_processor.py`: Main PDF operations
- `image_processor.py`: Image analysis utilities
- `models.py`: Data classes

### GUI Module (`src/pdfnormal/gui/`)
- `main_window.py`: Application controller
- `workers.py`: Threading workers
- `screens/`: Individual application screens
- `widgets/`: Reusable GUI components

### Utils Module (`src/pdfnormal/utils/`)
- `constants.py`: Configuration values
- `logger.py`: Logging setup

## Performance Considerations

- Avoid loading full PDFs into memory
- Use page-by-page processing
- Implement lazy loading for thumbnails
- Use background workers for long operations
- Cache intermediate results when appropriate

## Debugging

### Enable Debug Logging
```python
from pdfnormal.utils import setup_logger
import logging

logger = setup_logger("pdfnormal", logging.DEBUG)
```

### Common Issues
- **Memory usage**: Profile with `memory_profiler`
- **Performance**: Use `cProfile` to identify bottlenecks
- **Threading**: Check for deadlocks with logging

## Release Process

1. Update version in `src/pdfnormal/__init__.py`
2. Update `pyproject.toml`
3. Update `CHANGELOG.md`
4. Create git tag: `git tag v1.0.0`
5. Push tag: `git push origin v1.0.0`

## Need Help?

- Check existing issues and discussions
- Read the code documentation
- Look at similar implementations
- Ask in GitHub discussions

## Code Review Feedback

Please be receptive to feedback:
- We're all learning
- Constructive criticism helps the project
- Ask questions if feedback is unclear
- Don't take criticism personally

Thank you for contributing! 🎉
