# Development Workflow

## Daily Workflow

### 1. Starting a New Feature

```bash
# Update main branch
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/my-new-feature

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements-dev.txt
```

### 2. Implementing Feature

```bash
# Write tests first (TDD)
# Edit tests/test_*.py

# Then implement
# Edit src/pdfnormal/*/

# Run tests frequently
pytest tests/ -v

# Check coverage
pytest tests/ --cov=src/pdfnormal
```

### 3. Before Committing

```bash
# Format code
black .

# Lint
ruff check . --fix

# Type check
mypy src/pdfnormal

# Run full test suite
pytest tests/ -v

# Check for any uncommitted files
git status
```

### 4. Committing

```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "feat: Add blank page detection with threshold adjustment"

# View commit
git log --oneline -1
```

### 5. Pushing and Pull Request

```bash
# Push to your fork
git push origin feature/my-new-feature

# Create PR on GitHub
# Add description explaining changes
# Reference any related issues
```

## Testing Workflow

### Run Tests During Development

```bash
# Watch mode (requires pytest-watch)
pytest-watch tests/

# Run specific test
pytest tests/test_pdf_processor.py::TestPDFProcessor::test_init_with_valid_pdf -v

# Run with markers
pytest -m "not slow" tests/

# Run with output capture disabled (see print statements)
pytest -s tests/
```

### Coverage Analysis

```bash
# Generate coverage report
pytest tests/ --cov=src/pdfnormal --cov-report=html

# View report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows

# Minimum coverage enforcement
pytest tests/ --cov=src/pdfnormal --cov-fail-under=80
```

## Code Quality Workflow

### Pre-commit Checks

```bash
#!/bin/bash
# Run before committing
set -e

echo "Formatting code..."
black .

echo "Linting..."
ruff check . --fix

echo "Type checking..."
mypy src/pdfnormal

echo "Running tests..."
pytest tests/ -q

echo "All checks passed!"
```

### Full Quality Audit

```bash
# Comprehensive check
bash -c '
black --check .
ruff check .
mypy src/pdfnormal
pytest tests/ -q --cov=src/pdfnormal --cov-fail-under=80
'
```

## Release Workflow

### Preparing a Release

1. **Update version**:
```bash
# Update in src/pdfnormal/__init__.py
__version__ = "1.0.1"

# Update in pyproject.toml
version = "1.0.1"
```

2. **Update changelog**:
```markdown
## [1.0.1] - 2024-03-25

### Fixed
- Fixed margin adjustment widget display bug
- Improved blank page detection accuracy

### Changed
- Updated orientation detection algorithm
```

3. **Test release package**:
```bash
# Build distribution
python -m build

# Check before uploading
python -m twine check dist/*
```

4. **Create GitHub release**:
```bash
git tag v1.0.1
git push origin v1.0.1

# Create release notes on GitHub
```

## Debugging Workflow

### Enable Debug Logging

```python
# In your code or REPL
from pdfnormal.utils import setup_logger
import logging

logger = setup_logger("pdfnormal", logging.DEBUG)
```

### Profiling Performance

```python
# Profile CPU usage
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Your code here
processor = PDFProcessor("large_file.pdf")
processor.analyze_pages(options)

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)  # Top 20 functions
```

### Memory Profiling

```bash
pip install memory-profiler

python -m memory_profiler your_script.py
```

### Debugging with IDE

#### VS Code
```json
// .vscode/launch.json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: PDF Normal",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/src/pdfnormal/main.py",
            "console": "integratedTerminal",
            "justMyCode": true
        }
    ]
}
```

#### PyCharm
- Right-click on `main.py` → "Run 'main'" or "Debug 'main'"

## Collaboration

### Keeping Fork Updated

```bash
# Add upstream remote
git remote add upstream https://github.com/original/pdfnormal.git

# Fetch latest
git fetch upstream

# Rebase your branch
git rebase upstream/main

# Force push (use carefully!)
git push origin feature/my-feature --force-with-lease
```

### Handling Merge Conflicts

```bash
# During rebase/merge
# Edit conflicted files
# Mark as resolved
git add conflicted_file.py

# Continue rebase
git rebase --continue
```

## Common Tasks

### Adding a New Screen

```bash
# 1. Create screen file
touch src/pdfnormal/gui/screens/new_screen.py

# 2. Implement screen class
# Extend QWidget, define signals, implement UI

# 3. Add to main window
# Edit src/pdfnormal/gui/main_window.py
# Add: self.new_screen = NewScreen()
# Add to stack widget

# 4. Connect signals
# In MainWindow._connect_signals()

# 5. Write tests
touch tests/test_new_screen.py
```

### Adding a New Processing Option

```
1. Add to ProcessingOptions in src/pdfnormal/core/models.py
2. Implement logic in PDFProcessor or ImageProcessor
3. Add UI control in ImportScreen
4. Test in tests/test_pdf_processor.py
5. Update documentation
```

### Running Full Application Stack

```bash
# Terminal 1: Development server (if applicable)
# Terminal 2: Application
source venv/bin/activate
python -m pdfnormal

# Terminal 3: Tests/monitoring
pytest tests/ -v --tb=short
```

## Performance Tuning

### Identifying Bottlenecks

```python
# Use Python profiler
python -m pstats

# Or use line_profiler for line-by-line analysis
pip install line_profiler

# Decorate function with @profile
@profile
def slow_function():
    # Your code
    pass

# Run with: kernprof -l -v your_script.py
```

### Memory Usage

```bash
# Monitor memory during execution
ps aux | grep pdfnormal

# Or use activity monitor (macOS)
# Or task manager (Windows)
```

## Troubleshooting Development Issues

### Module Import Errors
```bash
# Reinstall in development mode
pip install -e .

# Verify installation
python -c "import pdfnormal; print(pdfnormal.__version__)"
```

### Test Database/Fixtures
```bash
# Regenerate test fixtures
pytest tests/conftest.py -v

# Use specific fixture
pytest tests/ -k "sample_pdf"
```

### Virtual Environment Issues
```bash
# Recreate virtual environment
deactivate
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
```

## Resources

- [Git Documentation](https://git-scm.com/doc)
- [Python Testing Best Practices](https://docs.pytest.org/)
- [PyQt6 Documentation](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- [PyMuPDF Documentation](https://pymupdf.readthedocs.io/)
