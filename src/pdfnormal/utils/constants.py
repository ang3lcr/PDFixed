"""Constants and configuration."""

import os
from pathlib import Path

# Application info
APP_NAME = "PDF Normal"
APP_VERSION = "1.0.0"
APP_AUTHOR = "PDF Normal Team"

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
TEMP_DIR = Path(os.path.expanduser("~/.pdfnormal/temp"))
CACHE_DIR = Path(os.path.expanduser("~/.pdfnormal/cache"))

# PDF settings
DEFAULT_ZOOM = 1.0
THUMBNAIL_SIZE = 150
MAX_PREVIEW_PIXELS = 1000000
BLANK_PAGE_THRESHOLD = 0.95

# UI settings
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900
ANIMATION_DURATION = 300  # ms

# Threading
WORKER_THREADS = 2

# Create necessary directories
for directory in [TEMP_DIR, CACHE_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
