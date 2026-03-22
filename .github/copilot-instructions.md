# pdfNormal Workspace Instructions

**Project**: A Python desktop application for PDF processing and normalization  
**Language**: Python  
**Type**: Desktop Application with Testing Framework

---

## Quick Start

### Essential Commands
- **Run tests**: `pytest` or `python -m pytest`
- **Run application**: `python -m pdfnormal` or local executable
- **Install dependencies**: `pip install -r requirements.txt` (or `requirements-dev.txt` for dev tools)
- **Format code**: `black .` or `ruff format .`
- **Lint code**: `ruff check .` or `pylint`

### Repository Structure
```
pdfNormal/
├── src/pdfnormal/          # Main application package
│   ├── __init__.py
│   ├── core/               # Core PDF processing logic
│   ├── gui/                # Desktop UI (if using Qt, Tkinter, etc.)
│   └── utils/              # Utility functions
├── tests/                  # Unit and integration tests
│   └── test_*.py           # Test files
├── docs/                   # Documentation
├── setup.py                # Package configuration
├── requirements.txt        # Production dependencies
├── requirements-dev.txt    # Development dependencies
└── pyproject.toml          # Modern Python project config
```

---

## Development Practices

### Testing
- All new features require **unit tests** in the `tests/` directory
- Use `pytest` for test execution and discovery
- Test naming: `test_<feature>_<scenario>.py` or `<module>_test.py`
- Aim for >80% code coverage on critical PDF processing functions
- Run tests before committing: `pytest -v`

### Code Style
- Follow **PEP 8** conventions
- Use type hints for function signatures
- Format with Black (line length: 88 characters, unless configured)
- Lint with Ruff or Pylint to catch common issues

### Git Workflow
- Branch naming: `feature/<description>`, `bugfix/<description>`, `refactor/<description>`
- Commit messages: Clear, present tense (e.g., "Add PDF normalization filter")
- PR/commit reviews should verify tests pass and coverage maintained

### Documentation
- Docstrings for all public functions/classes (Google or NumPy style)
- README.md for high-level overview and setup instructions
- Code comments for complex PDF processing logic
- Changelog for notable updates (CHANGELOG.md)

---

## PDF Processing Considerations

### Common Patterns
- **PDF Libraries**: Consider `PyPDF2`, `pdfplumber`, `pikepdf`, or `pypdf` depending on use case
- **Normalization Tasks**: Text extraction, page reordering, compression, metadata cleanup, font standardization
- **Error Handling**: PDF files can be malformed—graceful error handling is essential
- **Performance**: Large PDF batches may need progress reporting or async processing

### Testing PDFs
- Use variety of PDF types in tests (text-based, scanned, encrypted, corrupted)
- Keep test fixtures small (< 1MB) for fast test runs
- Mock external dependencies when possible

---

## AI Assistant Guidance

### When Helping with This Project, Focus On
1. **PDF Processing**: Understand the PDF task (e.g., normalization = removing duplicates, correcting text, standardizing format)
2. **Desktop Integration**: If using GUI framework, be mindful of thread management and responsiveness
3. **Test Coverage**: Ask for/write tests alongside feature implementation
4. **Type Safety**: Encourage type hints for better IDE support and fewer runtime errors

### Known Patterns & Pitfalls
- PDF parsing can raise exceptions unexpectedly—always test with real-world PDFs
- Memory usage matters when processing large files—profile and optimize batch operations
- Desktop GUI can become unresponsive with blocking I/O—use threading or async carefully
- Dependency versions (especially PDF libraries) can introduce breaking changes—lock versions in requirements.txt

---

## Next Steps

1. Set up initial project structure (see Repository Structure above)
2. Install core PDF library and dev dependencies
3. Create first unit test
4. Implement core PDF processing function
5. Add basic desktop UI or CLI entry point

For more details on specific features or decisions, update this file or create dedicated docs in `docs/`.
