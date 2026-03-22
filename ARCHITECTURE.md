# Architecture and Design

## Overview

PDF Normal is built using clean architecture principles with clear separation of concerns. The application is organized into distinct layers:

1. **Presentation Layer (GUI)**: PyQt6 user interface
2. **Application Layer**: Business logic and workflow orchestration
3. **Core Layer**: PDF and image processing
4. **Infrastructure Layer**: Utilities and configuration

## Layer Architecture

### 1. Core Layer (`src/pdfnormal/core/`)

**Responsibility**: Pure PDF and image processing

**Components**:
- `PDFProcessor`: High-level PDF operations
  - Load and parse PDFs
  - Extract pages as images
  - Generate thumbnails
  - Perform batch processing
  
- `ImageProcessor`: Image analysis utilities
  - Blank page detection (pixel analysis)
  - Orientation detection (Hough transform)
  - Image manipulation (rotation, cropping)
  
- `PageInfo`, `ProcessingOptions`, `ProcessingResult`: Type-safe data models

**Design Decisions**:
- No GUI dependencies
- Thread-safe operations
- Progress callbacks for long operations
- Context manager support for resource cleanup

### 2. Application Layer (`src/pdfnormal/gui/`)

**Responsibility**: Orchestrate workflow and manage application state

**Main Components**:
- `MainWindow`: Central controller
  - Manages screen transitions
  - Coordinates between screens
  - Manages worker threads
  - Handles post-processing

**Worker Threads** (`workers.py`):
- `PDFLoadWorker`: Background PDF loading
- `PDFAnalysisWorker`: Page analysis
- `PDFProcessingWorker`: Batch processing
- `ThumbnailWorker`: Thumbnail generation

**Design Pattern**: **State Machine**
```
ImportScreen → OrganizerScreen → MarginScreen → ResultsScreen
     ↑            ↑                                    ↓
     └────────────┴────────────────────────────────────
```

### 3. Presentation Layer

**Screens**:
- `ImportScreen`: PDF import and option selection
- `OrganizerScreen`: Page visualization and reordering
- `MarginAdjustmentScreen`: Interactive margin adjustment
- `ResultsScreen`: Processing summary and export

**Custom Widgets**:
- `PageThumbnailWidget`: Individual page thumbnail
- `MarginAdjustmentWidget`: Margin control interface

### 4. Infrastructure Layer (`src/pdfnormal/utils/`)

**Components**:
- `constants.py`: Configuration and paths
- `logger.py`: Structured logging setup

## Threading Model

### UI Thread
- Main event loop
- User interactions
- Screen rendering
- Non-blocking UI updates

### Worker Threads
```python
Worker Thread
    ↓
Long-running task (PDF processing, image analysis)
    ↓
Emit signal with result
    ↓
Main thread slot receives result
    ↓
Update UI
```

**Benefits**:
- Responsive interface
- No UI freezing
- Progress feedback
- Cancellation support

## Data Flow

```
User Input (ImportScreen)
    ↓
Load PDF (PDFLoadWorker)
    ↓
Analyze Pages (PDFAnalysisWorker)
    ↓
Display Thumbnails (OrganizerScreen)
    ↓
User Reorders Pages
    ↓
Process PDF (PDFProcessingWorker)
    ↓
Display Results (ResultsScreen)
    ↓
Export PDF
    ↓
Cleanup
```

## Key Design Patterns

### 1. Model-View-Separation
- **Models** (`core/models.py`): Data structures with no business logic
- **Views** (GUI screens): Display models and capture user input
- **Controllers** (MainWindow): Coordinate models and views

### 2. Strategy Pattern
- `ProcessingOptions`: Encapsulates different processing strategies
- Allows flexible selection of operations

### 3. Worker Thread Pattern
- Separate long operations from UI thread
- Signal/slot communication for thread safety

### 4. Context Manager Pattern
```python
with PDFProcessor(filename) as processor:
    # Auto-cleanup on exit
    pass
```

### 5. Factory Pattern
- Worker thread creation in MainWindow

## Performance Optimization

### Memory Management
- **Page-by-page processing**: Load one page at a time
- **Lazy loading**: Thumbnails generated on-demand
- **Caching**: Temporary storage in `~/.pdfnormal/cache`
- **Streaming**: Results processed incrementally

### CPU Optimization
- **Image downsampling**: Reduced resolution for analysis
- **Vectorized operations**: NumPy for image processing
- **Parallelization opportunity**: Multiple PDFs (future)

### UI Responsiveness
- **Background threading**: Heavy ops don't block UI
- **Progress feedback**: Real-time updates via progress callbacks
- **Async operations**: Signal/slot decouples processing from rendering

## Error Handling

### Strategy
1. **Validation**: Check inputs early
2. **Logging**: Record all errors with context
3. **User feedback**: Display clear error messages
4. **Recovery**: Graceful degradation where possible

### Example
```python
try:
    processor = PDFProcessor(pdf_path)
except FileNotFoundError:
    logger.error(f"PDF not found: {pdf_path}")
    QMessageBox.critical(self, "Error", "PDF file not found")
except ValueError as e:
    logger.error(f"Invalid PDF: {e}")
    QMessageBox.critical(self, "Error", f"Invalid PDF: {e}")
```

## Extensibility

### Adding New Processing Options
1. Add option to `ProcessingOptions` in `models.py`
2. Implement logic in `PDFProcessor` or `ImageProcessor`
3. Add UI controls in `ImportScreen`
4. Test with `test_*.py`

### Adding New Screen
1. Create screen class in `gui/screens/`
2. Add to `MainWindow.stack` widget
3. Connect signals
4. Update workflow state machine

## Testing Strategy

### Unit Tests
- Test individual components (processors, widgets)
- Mock external dependencies
- Focus on business logic

### Integration Tests
- Test workflow between components
- Verify signal/slot connections
- Check state transitions

### Test Coverage Goals
- Core module: >90% coverage
- GUI module: >70% coverage (UI testing is harder)
- Overall: >80% coverage

## Dependency Management

### Production Dependencies
- PyQt6: GUI framework
- PyMuPDF (fitz): PDF processing
- OpenCV: Image processing
- NumPy: Numerical computing
- Pillow: Image manipulation

### Development Dependencies
- pytest: Testing
- black: Code formatting
- ruff: Linting
- mypy: Type checking

## Future Improvements

### Short-term
- [ ] Undo/redo system
- [ ] Project save/load
- [ ] Batch file processing
- [ ] Advanced preview with zoom

### Medium-term
- [ ] Plugin system for custom processors
- [ ] CLI interface
- [ ] Configuration file support
- [ ] Keyboard shortcuts customization

### Long-term
- [ ] Machine learning for orientation detection
- [ ] OCR text extraction
- [ ] PDF compression options
- [ ] Parallel processing for large batches

## Code Organization Principles

1. **Single Responsibility**: Each class/module has one reason to change
2. **Dependency Inversion**: High-level modules don't depend on low-level
3. **Open/Closed**: Open for extension, closed for modification
4. **Interface Segregation**: Clients don't depend on interfaces they don't use
5. **DRY**: Don't Repeat Yourself

## Documentation

- **Docstrings**: Google-style for all public APIs
- **Comments**: Why, not what (code shows what)
- **Type hints**: Enable IDE support and catch bugs
- **Architecture docs**: This file explains design decisions
