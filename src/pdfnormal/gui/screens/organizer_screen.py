"""Page organizer screen for reordering pages."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QGridLayout, QProgressBar, QMessageBox, QFileDialog, QAbstractItemView, QFrame, QApplication, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QRect, QParallelAnimationGroup, QEasingCurve, QPoint
from PyQt6.QtGui import QFont, QDrag, QCursor, QColor, QPainter, QPen, QPixmap
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
        self.drag_start_index = None
        self.current_processor = None  # Store processor reference
        self.drag_target_widget = None
        self.drop_indicator_animation = None
        
        # Enhanced drag state (inspired from normalize_pdf_gui.py)
        self.dragging = False
        self.drag_widget = None
        self.drag_pixmap = None
        self.drag_offset = QPoint()
        self.hover_index = None
        self.original_widget_style = None
        
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

        # Enable drag and drop on the container
        self.thumbnails_container.setAcceptDrops(True)
        self.thumbnails_container.setMouseTracking(True)  # Enable mouse tracking
        self.thumbnails_container.dragEnterEvent = self._drag_enter_event
        self.thumbnails_container.dragMoveEvent = self._drag_move_event
        self.thumbnails_container.dropEvent = self._drop_event
        self.thumbnails_container.dragLeaveEvent = self._drag_leave_event
        self.thumbnails_container.mouseMoveEvent = self._container_mouse_move
        self.thumbnails_container.mousePressEvent = self._container_mouse_press
        self.thumbnails_container.mouseReleaseEvent = self._container_mouse_release

        # Create drop indicator line (initially hidden)
        self.drop_indicator = QFrame()
        self.drop_indicator.setFixedHeight(4)
        self.drop_indicator.setStyleSheet("""
            QFrame {
                background-color: #0078d4;
                border-radius: 2px;
            }
        """)
        self.drop_indicator.hide()

        scroll_area.setWidget(self.thumbnails_container)
        scroll_area.setAcceptDrops(True)
        scroll_area.setMouseTracking(True)  # Enable mouse tracking on scroll area too
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
        self.current_processor = processor  # Store reference for thumbnail loading

        # Clear existing widgets
        while self.thumbnails_layout.count():
            item = self.thumbnails_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.page_widgets.clear()

        # Create thumbnail widgets
        columns = 5
        for page_idx in range(len(pages_info)):
            page_info = pages_info[page_idx]

            widget = PageThumbnailWidget(page_idx)
            widget.clicked.connect(self._on_page_clicked)
            widget.right_clicked.connect(self._on_page_right_clicked)
            widget.drag_started.connect(self._on_drag_started)
            self.page_widgets.append(widget)

            row = page_idx // columns
            col = page_idx % columns
            self.thumbnails_layout.addWidget(widget, row, col)

            # Load thumbnail in background
            try:
                thumbnail = processor.get_page_thumbnail(page_idx, size=150)
                widget.set_thumbnail(thumbnail)
            except Exception as e:
                logger.error(f"Error loading thumbnail {page_idx}: {e}")

        # Add stretch rows after the last row
        last_row = (len(pages_info) - 1) // columns + 1
        for i in range(last_row, last_row + 5):
            self.thumbnails_layout.setRowStretch(i, 1)

    def _on_page_clicked(self, page_index: int) -> None:
        """Handle page click."""
        # Update selection
        if self.selected_page_index is not None:
            self.page_widgets[self.selected_page_index].set_selected(False)

        self.selected_page_index = page_index
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

    def _on_drag_started(self, page_index: int) -> None:
        """Handle drag started from a thumbnail."""
        # This method is now handled by the new drag system
        pass

    def _container_mouse_press(self, event) -> None:
        """Handle mouse press on container."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Find which widget was clicked
            pos = event.position().toPoint()
            child_widget = self.thumbnails_container.childAt(pos)
            
            # Find the parent PageThumbnailWidget
            widget = child_widget
            while widget and widget not in self.page_widgets and widget.parent():
                widget = widget.parent()
            
            if widget and widget in self.page_widgets:
                self.drag_start_index = self.page_widgets.index(widget)
                self.drag_widget = widget
                self.drag_offset = widget.mapFromParent(pos)
                self.original_widget_style = widget.styleSheet()
                
                # Store original position for animation
                self.drag_original_pos = widget.pos()
                self.dragging = True

    def _container_mouse_move(self, event) -> None:
        """Handle mouse move on container."""
        if not self.dragging or not self.drag_widget:
            return

        # Check if we've moved enough to start drag
        if not hasattr(self, 'drag_started'):
            drag_distance = (event.position().toPoint() - self.drag_offset).manhattanLength()
            if drag_distance < QApplication.startDragDistance():
                return
            self.drag_started = True

        # Update hover state
        self._update_hover_state(event.position().toPoint())

    def _container_mouse_release(self, event) -> None:
        """Handle mouse release on container."""
        if not self.dragging or not self.drag_widget:
            return

        try:
            if hasattr(self, 'drag_started') and self.drag_started:
                # Find target position
                pos = event.position().toPoint()
                child_widget = self.thumbnails_container.childAt(pos)
                
                # Find the parent PageThumbnailWidget
                target_widget = child_widget
                while target_widget and target_widget not in self.page_widgets and target_widget.parent():
                    target_widget = target_widget.parent()
                
                if target_widget and target_widget in self.page_widgets:
                    target_index = self.page_widgets.index(target_widget)
                    
                    # Determine if drop should be before or after
                    widget_rect = target_widget.geometry()
                    widget_center = widget_rect.center()
                    cursor_pos = target_widget.mapFromParent(pos)
                    
                    if cursor_pos.y() < widget_center.y():
                        final_target_index = target_index
                    else:
                        final_target_index = target_index + 1
                    
                    # Adjust if source is before target
                    if self.drag_start_index < final_target_index:
                        final_target_index -= 1
                    
                    # Perform reordering if different
                    if (self.drag_start_index != final_target_index and 
                        0 <= final_target_index < len(self.page_widgets)):
                        self._reorder_pages_with_animation(
                            self.drag_start_index, final_target_index
                        )
        finally:
            self._cleanup_drag()

    def _cleanup_drag(self) -> None:
        """Clean up drag state."""
        self.dragging = False
        self.drag_widget = None
        self.drag_pixmap = None
        self.drag_start_index = None
        self.drag_offset = QPoint()
        self.original_widget_style = None
        self.hover_index = None
        
        # Clear all visual indicators
        self._clear_drag_indicators()
        
        # Reset drag_started flag
        if hasattr(self, 'drag_started'):
            delattr(self, 'drag_started')

    def _update_hover_state(self, pos: QPoint) -> None:
        """Update hover state for visual feedback."""
        # Clear previous hover
        if self.hover_index is not None and self.hover_index < len(self.page_widgets):
            widget = self.page_widgets[self.hover_index]
            widget.setStyleSheet(self.original_widget_style or "")

        # Find new hover target
        child_widget = self.thumbnails_container.childAt(pos)
        
        # Find the parent PageThumbnailWidget
        target_widget = child_widget
        while target_widget and target_widget not in self.page_widgets and target_widget.parent():
            target_widget = target_widget.parent()
        
        if target_widget and target_widget in self.page_widgets:
            target_index = self.page_widgets.index(target_widget)
            self.hover_index = target_index
            
            # Apply hover effect
            widget_rect = target_widget.geometry()
            widget_center = widget_rect.center()
            cursor_pos = target_widget.mapFromParent(pos)
            
            if cursor_pos.y() < widget_center.y():
                # Hover before - blue highlight
                target_widget.setStyleSheet("""
                    PageThumbnailWidget {
                        background: #e3f2fd;
                        border: 3px solid #0078d4;
                        border-radius: 4px;
                    }
                """)
                self._show_drop_indicator(target_index, show_above=True)
            else:
                # Hover after - green highlight
                target_widget.setStyleSheet("""
                    PageThumbnailWidget {
                        background: #e8f5e8;
                        border: 3px solid #4caf50;
                        border-radius: 4px;
                    }
                """)
                self._show_drop_indicator(target_index, show_above=False)
        else:
            # No target - hide indicator
            self.hover_index = None
            self.drop_indicator.hide()

    def _clear_drag_indicators(self) -> None:
        """Clear all drag indicators."""
        for widget in self.page_widgets:
            # Restore original style if available
            if hasattr(widget, '_original_style'):
                widget.setStyleSheet(widget._original_style)
            else:
                widget.setStyleSheet("""
                    PageThumbnailWidget {
                        background: white;
                        border: 2px solid transparent;
                        border-radius: 4px;
                    }
                    PageThumbnailWidget:hover {
                        border: 2px solid #0078d4;
                        background: #f5f5f5;
                    }
                """)
        self.drag_target_widget = None
        self.drop_indicator.hide()

    def _show_drop_indicator(self, position: int, show_above: bool = True) -> None:
        """Show drop indicator at specific position."""
        if position < 0 or position > len(self.page_widgets):
            self.drop_indicator.hide()
            return

        columns = 5
        
        if show_above:
            # Show above the target widget
            if position == 0:
                row = 0  # First row
            else:
                row = position // columns
        else:
            # Show below the target widget  
            if position >= len(self.page_widgets):
                # Show at the very end
                last_widget_row = (len(self.page_widgets) - 1) // columns
                row = last_widget_row + 1
            else:
                row = position // columns + 1
        
        # Check if drop indicator is already in layout and remove it safely
        if self.drop_indicator.parent():
            self.thumbnails_layout.removeWidget(self.drop_indicator)
        
        # Add drop indicator to new position
        self.thumbnails_layout.addWidget(self.drop_indicator, row, 0, 1, 5)
        
        self.drop_indicator.show()
        self.drop_indicator.raise_()  # Bring to front

    def _drag_enter_event(self, event) -> None:
        """Handle drag enter event."""
        # Not used in new system
        pass

    def _drag_move_event(self, event) -> None:
        """Handle drag move event."""
        # Not used in new system
        pass

    def _drag_leave_event(self, event) -> None:
        """Handle drag leave event."""
        self._cleanup_drag()

    def _update_drop_indicators(self, position) -> None:
        """Update visual drop indicators."""
        # Not used in new system
        pass

    def _drop_event(self, event) -> None:
        """Handle drop event."""
        # Not used in new system
        pass

    def _reorder_pages_with_animation(self, source_index: int, target_index: int) -> None:
        """Reorder pages with smooth animation and visual feedback."""
        if not self.pages_info or source_index >= len(self.pages_info):
            return

        # Store original positions for animation
        source_widget = self.page_widgets[source_index]
        original_pos = source_widget.pos()
        
        # Perform the actual reordering
        self._reorder_pages(source_index, target_index)
        
        # Animate the widget to its new position
        target_widget = self.page_widgets[target_index]
        new_pos = target_widget.pos()
        
        # Create animation
        self._animate_widget_movement(source_widget, original_pos, new_pos)
        
        # Pulse effect on destination (inspired from normalize_pdf_gui.py)
        self._pulse_destination(target_index)

    def _pulse_destination(self, index: int, pulses: int = 4) -> None:
        """Create pulse animation at destination position."""
        if index < 0 or index >= len(self.page_widgets):
            return
        
        widget = self.page_widgets[index]
        
        def animate_step(step: int):
            if step >= pulses:
                # Restore normal style
                widget.setStyleSheet("""
                    PageThumbnailWidget {
                        background: white;
                        border: 2px solid transparent;
                        border-radius: 4px;
                    }
                    PageThumbnailWidget:hover {
                        border: 2px solid #0078d4;
                        background: #f5f5f5;
                    }
                """)
                return
            
            # Alternate between highlight and normal
            if step % 2 == 0:
                widget.setStyleSheet("""
                    PageThumbnailWidget {
                        background: #e3f2fd;
                        border: 3px solid #0078d4;
                        border-radius: 4px;
                    }
                """)
            else:
                widget.setStyleSheet("""
                    PageThumbnailWidget {
                        background: white;
                        border: 2px solid transparent;
                        border-radius: 4px;
                    }
                """)
            
            # Schedule next step
            QTimer.singleShot(100, lambda: animate_step(step + 1))
        
        animate_step(0)

    def _animate_widget_movement(self, widget, start_pos, end_pos) -> None:
        """Animate widget movement from start_pos to end_pos."""
        # Create position animation
        pos_animation = QPropertyAnimation(widget, b"pos")
        pos_animation.setDuration(300)  # 300ms animation
        pos_animation.setStartValue(start_pos)
        pos_animation.setEndValue(end_pos)
        pos_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Create fade effect
        opacity_effect = QGraphicsOpacityEffect()
        widget.setGraphicsEffect(opacity_effect)
        
        opacity_animation = QPropertyAnimation(opacity_effect, b"opacity")
        opacity_animation.setDuration(150)
        opacity_animation.setStartValue(0.7)
        opacity_animation.setEndValue(1.0)
        
        # Run animations in parallel
        animation_group = QParallelAnimationGroup()
        animation_group.addAnimation(pos_animation)
        animation_group.addAnimation(opacity_animation)
        
        # Clean up after animation
        animation_group.finished.connect(
            lambda: self._cleanup_animation(widget, opacity_effect)
        )
        
        animation_group.start()

    def _cleanup_animation(self, widget, opacity_effect) -> None:
        """Clean up animation effects."""
        widget.setGraphicsEffect(None)
        # Refresh layout to ensure proper positioning
        self._refresh_layout()

    def _reorder_pages(self, source_index: int, target_index: int) -> None:
        """Reorder pages from source_index to target_index."""
        if not self.pages_info or source_index >= len(self.pages_info):
            return

        # Reorder the pages_info list
        page_info = self.pages_info.pop(source_index)
        self.pages_info.insert(target_index, page_info)

        # Reorder the page_widgets list
        widget = self.page_widgets.pop(source_index)
        self.page_widgets.insert(target_index, widget)

        # Update page indices in widgets
        for i, widget in enumerate(self.page_widgets):
            widget.page_index = i
            widget.number_label.setText(f"Page {i + 1}")

        # Refresh the layout
        self._refresh_layout()

        logger.info(f"Reordered page {source_index + 1} to position {target_index + 1}")

    def _refresh_layout(self) -> None:
        """Refresh the grid layout with current page order."""
        # Clear layout
        while self.thumbnails_layout.count():
            item = self.thumbnails_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        # Re-add widgets in new order (drop indicator will be added dynamically)
        columns = 5
        for i, widget in enumerate(self.page_widgets):
            row = i // columns
            col = i % columns
            self.thumbnails_layout.addWidget(widget, row, col)

        # Add stretch rows after the last row
        last_row = (len(self.page_widgets) - 1) // columns + 1
        for i in range(last_row, last_row + 5):
            self.thumbnails_layout.setRowStretch(i, 1)
