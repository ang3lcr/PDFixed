"""Page organizer screen for reordering pages."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QGridLayout, QProgressBar, QMessageBox, QFileDialog, QFrame, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PyQt6.QtGui import QFont, QCursor
import logging

from ..widgets import PageThumbnailWidget

logger = logging.getLogger(__name__)


class OrganizerScreen(QWidget):
    """Screen for organizing and reordering PDF pages."""

    pages_reordered = pyqtSignal(object)  # list of PageInfo in new order
    margin_adjustment_requested = pyqtSignal(int)  # page_index
    pdf_import_requested = pyqtSignal()  # Import PDF button clicked

    def __init__(self, parent=None):
        """Initialize organizer screen."""
        super().__init__(parent)
        self.page_widgets = []
        self.selected_page_index = None
        self.pages_info = None
        self.current_processor = None
        
        # Drag & Drop state
        self._drag_state = {
            'is_dragging': False,
            'source_index': None,
            'dragged_widget': None,
            'drop_target_index': None,
            'drop_indicator': None
        }
        
        self.setup_ui()

    def setup_ui(self) -> None:
        """Set up the UI."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Organize Pages")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Instructions
        instructions = QLabel(
            "Drag and drop pages to reorder them. Right-click on a page to adjust margins."
        )
        instructions.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(instructions)

        # Scrollable thumbnails area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #ddd;
                background: #fafafa;
            }
        """)

        self.thumbnails_container = QWidget()
        self.thumbnails_layout = QGridLayout(self.thumbnails_container)
        self.thumbnails_layout.setSpacing(10)
        self.thumbnails_layout.setContentsMargins(10, 10, 10, 10)
        
        # Create drop indicator (initially hidden)
        self._drag_state['drop_indicator'] = QFrame()
        self._drag_state['drop_indicator'].setFixedHeight(4)
        self._drag_state['drop_indicator'].setStyleSheet("""
            QFrame {
                background-color: #0078d4;
                border-radius: 2px;
            }
        """)
        self._drag_state['drop_indicator'].hide()

        scroll_area.setWidget(self.thumbnails_container)
        layout.addWidget(scroll_area, 1)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # Import PDF button
        self.import_button = QPushButton("Import PDF")
        self.import_button.setMinimumHeight(40)
        self.import_button.setMinimumWidth(120)
        self.import_button.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                color: #333;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                border-color: #999;
            }
        """)
        self.import_button.clicked.connect(self._on_import_clicked)
        button_layout.addWidget(self.import_button)

        self.back_button = QPushButton("Back")
        self.back_button.setMinimumHeight(40)
        self.back_button.setMinimumWidth(120)
        self.back_button.clicked.connect(self.back_clicked)
        button_layout.addWidget(self.back_button)

        self.process_button = QPushButton("Continue to Preview")
        self.process_button.setMinimumHeight(40)
        self.process_button.setMinimumWidth(150)
        self.process_button.setStyleSheet("""
            QPushButton {
                background-color: #107c10;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0d6107;
            }
        """)
        self.process_button.clicked.connect(self.process_clicked)
        button_layout.addWidget(self.process_button)

        layout.addLayout(button_layout)

    def back_clicked(self):
        """Handle back button."""
        pass  # Connect in main window

    def process_clicked(self):
        """Handle process button."""
        pass  # Connect in main window

    def load_thumbnails(self, processor, pages_info) -> None:
        """
        Load thumbnails for all pages.

        Args:
            processor: PDFProcessor or MultiPDFProcessor instance
            pages_info: List of PageInfo objects
        """
        self.pages_info = pages_info
        self.current_processor = processor

        # Clear existing widgets
        self._clear_thumbnails()

        # Create thumbnail widgets
        columns = 5
        for page_idx in range(len(pages_info)):
            page_info = pages_info[page_idx]

            widget = PageThumbnailWidget(page_idx)
            widget.clicked.connect(self._on_page_clicked)
            widget.right_clicked.connect(self._on_page_right_clicked)
            
            # Install event filter for drag and drop
            widget.installEventFilter(self)
            
            self.page_widgets.append(widget)

            row = page_idx // columns
            col = page_idx % columns
            self.thumbnails_layout.addWidget(widget, row, col)

            # Load thumbnail
            try:
                thumbnail = processor.get_page_thumbnail(page_idx, size=150)
                widget.set_thumbnail(thumbnail)
            except Exception as e:
                logger.error(f"Error loading thumbnail {page_idx}: {e}")

        # Add stretch rows
        last_row = (len(pages_info) - 1) // columns + 1
        for i in range(last_row, last_row + 5):
            self.thumbnails_layout.setRowStretch(i, 1)

    def _clear_thumbnails(self):
        """Clear all thumbnail widgets from the layout."""
        while self.thumbnails_layout.count():
            item = self.thumbnails_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.page_widgets.clear()

    def _on_page_clicked(self, page_index: int) -> None:
        """Handle page click event."""
        # Update selection
        if (self.selected_page_index is not None and 
            0 <= self.selected_page_index < len(self.page_widgets)):
            self.page_widgets[self.selected_page_index].set_selected(False)
        
        self.selected_page_index = page_index
        if 0 <= page_index < len(self.page_widgets):
            self.page_widgets[page_index].set_selected(True)

    def _on_page_right_clicked(self, page_index: int) -> None:
        """Handle page right-click."""
        self.margin_adjustment_requested.emit(page_index)

    def get_pages_order(self):
        """Get current page order."""
        if self.pages_info:
            return self.pages_info
        return []

    def set_progress(self, current: int, total: int) -> None:
        """Update progress bar."""
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)

    def clear_progress(self) -> None:
        """Clear progress bar."""
        self.progress_bar.setVisible(False)

    def _on_import_clicked(self) -> None:
        """Handle import PDF button click."""
        self.pdf_import_requested.emit()

    # ========================================================================
    # NEW DRAG & DROP IMPLEMENTATION
    # ========================================================================

    def eventFilter(self, obj, event):
        """Event filter to handle drag & drop on page widgets."""
        if isinstance(obj, PageThumbnailWidget):
            widget_index = self.page_widgets.index(obj) if obj in self.page_widgets else -1
            
            if event.type() == event.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    # Start drag operation
                    self._start_drag(widget_index, obj)
                    return True
                    
            elif event.type() == event.Type.MouseMove:
                if self._drag_state['is_dragging']:
                    # Update drag position and show visual feedback
                    self._update_drag_visuals(event.globalPosition().toPoint())
                    return True
                    
            elif event.type() == event.Type.MouseButtonRelease:
                if event.button() == Qt.MouseButton.LeftButton and self._drag_state['is_dragging']:
                    # End drag operation
                    self._end_drag(widget_index)
                    return True
        
        return super().eventFilter(obj, event)

    def _start_drag(self, index: int, widget: PageThumbnailWidget) -> None:
        """Start dragging a page."""
        if index < 0 or index >= len(self.page_widgets):
            return
            
        self._drag_state['is_dragging'] = True
        self._drag_state['source_index'] = index
        self._drag_state['dragged_widget'] = widget
        self._drag_state['drop_target_index'] = index
        
        # Apply visual effect to dragged widget (opacity reduction)
        opacity_effect = QGraphicsOpacityEffect()
        opacity_effect.setOpacity(0.5)
        widget.setGraphicsEffect(opacity_effect)
        
        # Change cursor to indicate dragging
        from PyQt6.QtWidgets import QApplication
        QApplication.setOverrideCursor(Qt.CursorShape.ClosedHandCursor)
        
        logger.debug(f"Started dragging page {index + 1}")

    def _update_drag_visuals(self, global_pos: QPoint) -> None:
        """Update visual feedback during drag (drop indicator)."""
        # Map global position to container coordinates
        local_pos = self.thumbnails_container.mapFromGlobal(global_pos)
        
        # Find the widget under the cursor
        target_widget = self.thumbnails_container.childAt(local_pos)
        
        # Find parent PageThumbnailWidget
        while target_widget and not isinstance(target_widget, PageThumbnailWidget):
            target_widget = target_widget.parent()
        
        if target_widget and target_widget in self.page_widgets:
            target_index = self.page_widgets.index(target_widget)
            
            # Determine insert position (before or after based on cursor position)
            widget_rect = target_widget.geometry()
            widget_center = widget_rect.center()
            
            if local_pos.y() < widget_center.y():
                # Insert before this widget
                self._drag_state['drop_target_index'] = target_index
                self._show_drop_indicator(target_index, before=True)
            else:
                # Insert after this widget
                self._drag_state['drop_target_index'] = target_index + 1
                self._show_drop_indicator(target_index, before=False)
        else:
            # Hide indicator if not over a valid target
            self._drag_state['drop_indicator'].hide()

    def _show_drop_indicator(self, index: int, before: bool = True) -> None:
        """Show drop indicator at specified position."""
        if index < 0 or index >= len(self.page_widgets):
            return
            
        columns = 5
        target_widget = self.page_widgets[index]
        
        # Calculate row and position
        if before:
            row = index // columns
        else:
            row = (index + 1) // columns
        
        # Remove indicator from current position if any
        if self._drag_state['drop_indicator'].parent():
            self.thumbnails_layout.removeWidget(self._drag_state['drop_indicator'])
        
        # Add indicator to new position
        self.thumbnails_layout.addWidget(
            self._drag_state['drop_indicator'], 
            row, 0, 1, columns
        )
        self._drag_state['drop_indicator'].show()
        self._drag_state['drop_indicator'].raise_()

    def _end_drag(self, release_index: int) -> None:
        """End drag operation and perform reordering if needed."""
        if not self._drag_state['is_dragging']:
            return
            
        source_index = self._drag_state['source_index']
        target_index = self._drag_state['drop_target_index']
        
        # Hide drop indicator
        self._drag_state['drop_indicator'].hide()
        
        # Restore dragged widget appearance
        if self._drag_state['dragged_widget']:
            self._drag_state['dragged_widget'].setGraphicsEffect(None)
        
        # Restore cursor
        from PyQt6.QtWidgets import QApplication
        QApplication.restoreOverrideCursor()
        
        # Perform reordering if target is different from source
        if (source_index != target_index and 
            0 <= source_index < len(self.page_widgets) and
            0 <= target_index <= len(self.page_widgets)):
            
            self._reorder_pages(source_index, target_index)
        
        # Reset drag state
        self._drag_state['is_dragging'] = False
        self._drag_state['source_index'] = None
        self._drag_state['dragged_widget'] = None
        self._drag_state['drop_target_index'] = None
        
        logger.debug(f"Ended drag. Source: {source_index}, Target: {target_index}")

    def _reorder_pages(self, source_index: int, target_index: int) -> None:
        """Reorder pages with animation."""
        if not self.pages_info or source_index >= len(self.pages_info):
            return
            
        # Adjust target if moving from before to after the same item
        if source_index < target_index:
            target_index -= 1
            
        # Skip if no change
        if source_index == target_index:
            return
            
        logger.info(f"Reordering page {source_index + 1} to position {target_index + 1}")
        
        # Reorder data
        page_info = self.pages_info.pop(source_index)
        self.pages_info.insert(target_index, page_info)
        
        # Reorder widgets
        widget = self.page_widgets.pop(source_index)
        self.page_widgets.insert(target_index, widget)
        
        # Update page indices in all widgets
        for i, w in enumerate(self.page_widgets):
            w.page_index = i
            w.number_label.setText(f"Page {i + 1}")
        
        # Refresh layout with animation
        self._refresh_layout_with_animation()
        
        # Emit signal
        self.pages_reordered.emit(self.pages_info)

    def _refresh_layout_with_animation(self) -> None:
        """Refresh layout with smooth animation."""
        columns = 5
        
        # Store current positions for animation
        old_positions = {}
        for i, widget in enumerate(self.page_widgets):
            old_positions[i] = widget.pos()
        
        # Temporarily remove all widgets from layout
        for widget in self.page_widgets:
            self.thumbnails_layout.removeWidget(widget)
            widget.setParent(self.thumbnails_container)
        
        # Re-add widgets in new order
        for i, widget in enumerate(self.page_widgets):
            row = i // columns
            col = i % columns
            self.thumbnails_layout.addWidget(widget, row, col)
        
        # Add stretch rows
        last_row = (len(self.page_widgets) - 1) // columns + 1
        for i in range(last_row, last_row + 5):
            self.thumbnails_layout.setRowStretch(i, 1)
        
        # Animate widgets to their new positions
        for i, widget in enumerate(self.page_widgets):
            if i in old_positions:
                start_pos = old_positions[i]
                end_pos = widget.pos()
                
                if start_pos != end_pos:
                    animation = QPropertyAnimation(widget, b"pos")
                    animation.setDuration(300)
                    animation.setStartValue(start_pos)
                    animation.setEndValue(end_pos)
                    animation.setEasingCurve(QEasingCurve.Type.OutCubic)
                    animation.start()
