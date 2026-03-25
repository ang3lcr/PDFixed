"""Page organizer screen for reordering pages."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QGridLayout, QProgressBar, QMessageBox, QFileDialog, QFrame, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PyQt6.QtGui import QFont, QCursor
from PyQt6 import sip
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
        
        # Create enhanced drop indicator with shadow effect (initially hidden)
        self._drag_state['drop_indicator'] = QFrame()
        self._drag_state['drop_indicator'].setFixedHeight(8)
        self._drag_state['drop_indicator'].setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0078d4,
                    stop:0.5 #005a9e,
                    stop:1 #0078d4);
                border: 2px solid #004578;
                border-radius: 4px;
            }
        """)
        self._drag_state['drop_indicator'].hide()
        
        # Create placeholder widget for drop position (shows empty space)
        self._drag_state['placeholder'] = QFrame()
        self._drag_state['placeholder'].setFixedSize(160, 200)
        self._drag_state['placeholder'].setStyleSheet("""
            QFrame {
                background-color: #e3f2fd;
                border: 3px dashed #0078d4;
                border-radius: 8px;
            }
        """)
        # Add drop icon/label to placeholder
        placeholder_layout = QVBoxLayout(self._drag_state['placeholder'])
        placeholder_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_label = QLabel("↓ Drop Here ↓")
        drop_label.setStyleSheet("""
            color: #0078d4;
            font-weight: bold;
            font-size: 14px;
            background: transparent;
        """)
        drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_layout.addWidget(drop_label)
        self._drag_state['placeholder'].hide()

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
        drop_indicator = self._drag_state.get("drop_indicator")
        placeholder = self._drag_state.get("placeholder")

        # Detach overlays from the grid layout before deleting other widgets.
        for w in (drop_indicator, placeholder):
            try:
                if w is not None and w.parent() == self.thumbnails_container:
                    self.thumbnails_layout.removeWidget(w)
            except RuntimeError:
                # Widget might already be deleted; ignore.
                pass

        while self.thumbnails_layout.count():
            item = self.thumbnails_layout.takeAt(0)
            if item.widget():
                w = item.widget()
                if w is drop_indicator or w is placeholder:
                    w.hide()
                    continue
                w.deleteLater()
        
        self.page_widgets.clear()

    def _ensure_drag_overlays(self) -> None:
        """Ensure drag overlay widgets exist (Qt may delete them)."""
        di = self._drag_state.get("drop_indicator")
        if di is None or sip.isdeleted(di):
            self._drag_state["drop_indicator"] = QFrame()
            self._drag_state["drop_indicator"].setFixedHeight(8)
            self._drag_state["drop_indicator"].setStyleSheet("""
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #0078d4,
                        stop:0.5 #005a9e,
                        stop:1 #0078d4);
                    border: 2px solid #004578;
                    border-radius: 4px;
                }
            """)
            self._drag_state["drop_indicator"].hide()

        ph = self._drag_state.get("placeholder")
        if ph is None or sip.isdeleted(ph):
            self._drag_state["placeholder"] = QFrame()
            self._drag_state["placeholder"].setFixedSize(160, 200)
            self._drag_state["placeholder"].setStyleSheet("""
                QFrame {
                    background-color: #e3f2fd;
                    border: 3px dashed #0078d4;
                    border-radius: 8px;
                }
            """)

            placeholder_layout = QVBoxLayout(self._drag_state["placeholder"])
            placeholder_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            drop_label = QLabel("↓ Drop Here ↓")
            drop_label.setStyleSheet("""
                color: #0078d4;
                font-weight: bold;
                font-size: 14px;
                background: transparent;
            """)
            drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder_layout.addWidget(drop_label)
            self._drag_state["placeholder"].hide()

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
                    # Store initial position for drag detection
                    self._drag_state['press_pos'] = event.globalPosition().toPoint()
                    self._drag_state['press_widget'] = obj
                    self._drag_state['press_index'] = widget_index
                    return True
                    
            elif event.type() == event.Type.MouseMove:
                if self._drag_state.get('press_pos') and not self._drag_state['is_dragging']:
                    # Check if moved enough to start drag
                    current_pos = event.globalPosition().toPoint()
                    drag_distance = (current_pos - self._drag_state['press_pos']).manhattanLength()
                    if drag_distance >= 10:  # 10 pixels threshold
                        # Start actual drag
                        self._start_drag(self._drag_state['press_index'], self._drag_state['press_widget'])
                        self._update_drag_visuals(current_pos)
                    return True
                elif self._drag_state['is_dragging']:
                    # Update drag position and show visual feedback
                    self._update_drag_visuals(event.globalPosition().toPoint())
                    return True
                    
            elif event.type() == event.Type.MouseButtonRelease:
                if event.button() == Qt.MouseButton.LeftButton:
                    if self._drag_state['is_dragging']:
                        # End drag operation
                        self._end_drag(widget_index)
                    else:
                        # Was just a click, not a drag
                        self._on_page_clicked(widget_index)
                    # Clear press state
                    self._drag_state['press_pos'] = None
                    self._drag_state['press_widget'] = None
                    self._drag_state['press_index'] = None
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
        self._drag_state['drag_start_pos'] = widget.mapToGlobal(widget.rect().center())
        
        # Store original position for animation
        self._drag_state['original_geometry'] = widget.geometry()
        
        # Apply visual effect to dragged widget (opacity reduction + slight scale)
        opacity_effect = QGraphicsOpacityEffect()
        opacity_effect.setOpacity(0.6)
        widget.setGraphicsEffect(opacity_effect)
        
        # Add shadow effect via stylesheet
        widget.setStyleSheet("""
            PageThumbnailWidget {
                background: white;
                border: 2px solid #0078d4;
                border-radius: 8px;
            }
        """)
        
        # Change cursor to indicate dragging
        from PyQt6.QtWidgets import QApplication
        QApplication.setOverrideCursor(Qt.CursorShape.ClosedHandCursor)
        
        logger.debug(f"Started dragging page {index + 1}")

    def _update_drag_visuals(self, global_pos: QPoint) -> None:
        """Update visual feedback during drag with improved precision."""
        self._ensure_drag_overlays()
        # Map global position to container coordinates
        local_pos = self.thumbnails_container.mapFromGlobal(global_pos)
        
        columns = 5
        spacing = 10
        widget_width = 160
        widget_height = 200
        
        # Calculate which grid cell the cursor is closest to
        total_width = self.thumbnails_container.width()
        margins = self.thumbnails_layout.contentsMargins()
        available_width = total_width - margins.left() - margins.right()
        cell_width = (available_width - (columns - 1) * spacing) // columns
        
        # Calculate grid position
        grid_x = local_pos.x() - margins.left()
        grid_y = local_pos.y() - margins.top()
        
        col = max(0, min(columns - 1, grid_x // (cell_width + spacing)))
        row = max(0, grid_y // (widget_height + spacing))
        
        # Calculate insert index based on grid position
        insert_index = row * columns + col
        insert_index = max(0, min(len(self.page_widgets), insert_index))
        
        source_index = self._drag_state['source_index']
        
        # Skip if trying to insert at same position as source
        if insert_index == source_index:
            di = self._drag_state.get("drop_indicator")
            ph = self._drag_state.get("placeholder")
            if di is not None and not sip.isdeleted(di):
                di.hide()
            if ph is not None and not sip.isdeleted(ph):
                ph.hide()
            return
        
        # Adjust for the removed source widget
        if source_index is not None and insert_index > source_index:
            effective_index = insert_index - 1
        else:
            effective_index = insert_index
        
        # Store the target index
        self._drag_state['drop_target_index'] = insert_index
        
        # Show preview at calculated position
        self._show_drop_preview_at_index(insert_index, effective_index)

    def _show_drop_preview_at_index(self, insert_index: int, effective_index: int) -> None:
        """Show drop preview at specific grid index."""
        self._ensure_drag_overlays()
        columns = 5
        
        # Calculate row and column for insert position
        row = insert_index // columns
        col = insert_index % columns
        
        # Show drop indicator at the row
        indicator = self._drag_state['drop_indicator']
        if indicator.parent():
            self.thumbnails_layout.removeWidget(indicator)
        
        # Add indicator spanning full row before the target row
        indicator_row = row if col == 0 else row + 1
        self.thumbnails_layout.addWidget(indicator, indicator_row, 0, 1, columns)
        indicator.show()
        indicator.raise_()
        
        # Show placeholder at specific position
        placeholder = self._drag_state['placeholder']
        if placeholder.parent():
            self.thumbnails_layout.removeWidget(placeholder)
        
        # Calculate actual row/col for placeholder (considering effective index)
        ph_row = effective_index // columns
        ph_col = effective_index % columns
        self.thumbnails_layout.addWidget(placeholder, ph_row, ph_col)
        placeholder.show()
        placeholder.raise_()

    def _show_drop_preview(self, index: int, before: bool = True) -> None:
        """Show drop preview with indicator line and placeholder space."""
        self._ensure_drag_overlays()
        if index < 0 or index >= len(self.page_widgets):
            return
        
        columns = 5
        target_widget = self.page_widgets[index]
        source_index = self._drag_state['source_index']
        
        # Calculate effective insert index considering the removed source widget
        effective_index = index
        if source_index < index:
            effective_index = index - 1 if before else index
        elif source_index == index:
            effective_index = index
        else:
            effective_index = index if before else index + 1
        
        # Calculate row and column for the placeholder
        row = effective_index // columns
        col = effective_index % columns
        
        # Show drop indicator line
        if self._drag_state['drop_indicator'].parent():
            self.thumbnails_layout.removeWidget(self._drag_state['drop_indicator'])
        
        # Position indicator based on insert direction
        if before:
            indicator_row = index // columns
        else:
            indicator_row = (index + 1) // columns
        
        self.thumbnails_layout.addWidget(
            self._drag_state['drop_indicator'],
            indicator_row, 0, 1, columns
        )
        self._drag_state['drop_indicator'].show()
        self._drag_state['drop_indicator'].raise_()
        
        # Show placeholder at drop position
        placeholder = self._drag_state['placeholder']
        if placeholder.parent():
            self.thumbnails_layout.removeWidget(placeholder)
        
        # Add placeholder to show where the page will be inserted
        self.thumbnails_layout.addWidget(placeholder, row, col)
        placeholder.show()
        placeholder.raise_()
        
        # Highlight target widget with subtle effect
        if not before:
            # When inserting after, highlight next widget if exists
            next_index = index + 1
            if next_index < len(self.page_widgets) and next_index != source_index:
                next_widget = self.page_widgets[next_index]
                next_widget.setStyleSheet("""
                    PageThumbnailWidget {
                        background: #f0f7ff;
                        border: 2px solid #90caf9;
                        border-radius: 8px;
                    }
                """)

    def _end_drag(self, release_index: int) -> None:
        """End drag operation and perform reordering if needed."""
        if not self._drag_state['is_dragging']:
            return

        self._ensure_drag_overlays()
            
        source_index = self._drag_state['source_index']
        target_index = self._drag_state['drop_target_index']
        
        # Hide drop indicator and placeholder
        di = self._drag_state.get("drop_indicator")
        ph = self._drag_state.get("placeholder")
        if di is not None and not sip.isdeleted(di):
            di.hide()
        if ph is not None and not sip.isdeleted(ph):
            ph.hide()
        
        # Restore dragged widget appearance
        if self._drag_state['dragged_widget']:
            self._drag_state['dragged_widget'].setGraphicsEffect(None)
            self._drag_state['dragged_widget'].setStyleSheet("""
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
        
        # Restore all other widgets' styles
        for widget in self.page_widgets:
            if widget != self._drag_state['dragged_widget']:
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
