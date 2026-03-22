# Changelog

All notable changes to PDF Normal will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-03-22

### Added
- Initial release of PDF Normal
- Modern PyQt6-based GUI with multi-screen workflow
- PDF import and processing with real-time file information
- Blank page detection using pixel analysis
- Automatic page orientation correction
- Interactive page organizer with drag-and-drop support
- Thumbnail gallery with lazy loading
- Margin adjustment tool with live preview
- Processing results summary screen
- Comprehensive logging system
- Full test suite with >80% coverage
- Threading system for responsive UI
- Temporary file caching for performance
- Command-line and GUI entry points

### Features
- Support for PDFs with 500+ pages
- Memory-optimized processing (page-by-page)
- Real-time progress feedback
- Background worker threads
- Export with PDF compression
- Detailed processing report

### Documentation
- Comprehensive README
- Installation guide
- Contributing guidelines
- Architecture documentation
- API documentation in docstrings

---

## [Unreleased]

### Planned Features
- Undo/redo system
- Project file format for saving processing steps
- Batch processing for multiple PDFs
- Advanced zoom and navigation in preview
- OCR text extraction option
- Custom quality/compression settings
- CLI interface options
- Plugin system for custom processors

### Known Issues
- Tesseract OCR is optional (some features degraded without it)
- Very large PDFs (>1000 pages) may need system optimization

### Future Improvements
- Machine learning-based orientation detection
- Parallel processing for batch operations
- Web interface option
- Mobile app companion
- Cloud processing support
