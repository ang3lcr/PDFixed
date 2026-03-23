"""Custom GUI widgets."""

from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QScrollArea, QGridLayout, QSlider, QSpinBox, QGroupBox,
    QApplication, QFrame, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer, QPropertyAnimation, QRect, QMimeData, QParallelAnimationGroup
from PyQt6.QtGui import QPixmap, QImage, QFont, QColor, QIcon, QDrag, QCursor, QPainter, QPen
from PyQt6.QtCore import QThread
import numpy as np
import cv2
import logging

logger = logging.getLogger(__name__)


class PageThumbnailWidget(QWidget):
    """Widget displaying a single page thumbnail."""

    clicked = pyqtSignal(int)  # page_index
    right_clicked = pyqtSignal(int)  # page_index
    drag_started = pyqtSignal(int)  # page_index

    def __init__(self, page_index: int, parent=None):
        """Initialize thumbnail widget."""
        super().__init__(parent)
        self.page_index = page_index
        self.thumbnail_image = None
        self.is_selected = False
        self.is_drag_target = False  # For drop indication
        self.drop_position = None  # 'before' or 'after'

        self.setFixedSize(160, 200)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Image label
        self.image_label = QLabel()
        self.image_label.setFixedSize(150, 170)
        self.image_label.setStyleSheet("border: 1px solid #ccc; background: #f0f0f0;")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.image_label)

        # Page number label
        self.number_label = QLabel(f"Page {page_index + 1}")
        font = QFont()
        font.setPointSize(9)
        font.setBold(True)
        self.number_label.setFont(font)
        self.number_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.number_label)

        self.setStyleSheet("""
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

    def set_thumbnail(self, image_array: np.ndarray) -> None:
        """
        Set thumbnail image.

        Args:
            image_array: NumPy array in BGR format (CV2)
        """
        try:
            # Convert BGR to RGB
            rgb_array = cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB)
            height, width = rgb_array.shape[:2]

            # Create QImage
            bytes_per_line = 3 * width
            qt_image = QImage(
                rgb_array.data,
                width,
                height,
                bytes_per_line,
                QImage.Format.Format_RGB888,
            )

            # Scale to fit
            pixmap = QPixmap.fromImage(qt_image)
            scaled_pixmap = pixmap.scaledToHeight(
                170,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.image_label.setPixmap(scaled_pixmap)
            self.thumbnail_image = image_array
        except Exception as e:
            logger.error(f"Error setting thumbnail: {e}")
            self.image_label.setText("Failed to load")

    def set_selected(self, selected: bool) -> None:
        """Set selection state."""
        self.is_selected = selected
        if selected:
            self.setStyleSheet("""
                PageThumbnailWidget {
                    background: #e3f2fd;
                    border: 2px solid #0078d4;
                    border-radius: 4px;
                }
            """)
        else:
            self._update_normal_style()

    def set_drag_target(self, is_target: bool, position: str = None) -> None:
        """Set drag target indication."""
        self.is_drag_target = is_target
        self.drop_position = position
        self._update_normal_style()

    def _update_normal_style(self) -> None:
        """Update normal style based on drag state."""
        if self.is_drag_target:
            if self.drop_position == 'before':
                border_color = '#0078d4'  # Blue for before
                bg_color = '#e3f2fd'
                border_width = '3px'
                border_style = 'solid'
            elif self.drop_position == 'after':
                border_color = '#4caf50'  # Green for after  
                bg_color = '#e8f5e8'
                border_width = '3px'
                border_style = 'solid'
            else:
                border_color = '#ff6b35'  # Orange for general target
                bg_color = '#fff3e0'
                border_width = '3px'
                border_style = 'solid'
                
            self.setStyleSheet(f"""
                PageThumbnailWidget {{
                    background: {bg_color};
                    border: {border_width} {border_style} {border_color};
                    border-radius: 4px;
                }}
            """)
        else:
            self.setStyleSheet("""
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

    def paintEvent(self, event) -> None:
        """Paint event for additional visual effects."""
        super().paintEvent(event)
        
        if self.is_drag_target and self.drop_position:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Draw drop indicator arrow
            if self.drop_position == 'before':
                # Draw arrow at top
                pen = QPen(QColor('#ff6b35'), 3)
                painter.setPen(pen)
                painter.drawLine(10, 5, self.width() - 10, 5)
                # Arrow head
                painter.drawLine(15, 10, 10, 5)
                painter.drawLine(self.width() - 15, 10, self.width() - 10, 5)
                
            elif self.drop_position == 'after':
                # Draw arrow at bottom
                pen = QPen(QColor('#4caf50'), 3)
                painter.setPen(pen)
                painter.drawLine(10, self.height() - 5, self.width() - 10, self.height() - 5)
                # Arrow head
                painter.drawLine(15, self.height() - 10, 10, self.height() - 5)
                painter.drawLine(self.width() - 15, self.height() - 10, self.width() - 10, self.height() - 5)
            
            painter.end()

    def mousePressEvent(self, event):
        """Handle mouse press event."""
        # Let parent handle all mouse events for drag-and-drop
        event.ignore()
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.page_index)
        elif event.button() == Qt.MouseButton.RightButton:
            self.right_clicked.emit(self.page_index)

    def mouseMoveEvent(self, event):
        """Handle mouse move event for drag."""
        # Let parent handle all mouse events for drag-and-drop
        event.ignore()

    def mouseReleaseEvent(self, event):
        """Handle mouse release event."""
        # Let parent handle all mouse events for drag-and-drop
        event.ignore()

    def _start_drag(self):
        """Start drag operation."""
        drag = QDrag(self)
        mime_data = QMimeData()
        
        # Store page index as text
        mime_data.setText(str(self.page_index))
        drag.setMimeData(mime_data)

        # Create a pixmap for the drag visual
        if self.thumbnail_image is not None:
            # Use the actual thumbnail if available
            pixmap = QPixmap.fromImage(
                QImage(
                    self.thumbnail_image.data,
                    self.thumbnail_image.shape[1],
                    self.thumbnail_image.shape[0],
                    3 * self.thumbnail_image.shape[1],
                    QImage.Format.Format_BGR888
                )
            ).scaled(100, 130, Qt.AspectRatioMode.KeepAspectRatio)
            
            # Add semi-transparent overlay for drag effect
            painter = QPainter(pixmap)
            painter.fillRect(pixmap.rect(), QColor(0, 0, 0, 50))  # Semi-transparent black overlay
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, f"Page {self.page_index + 1}")
            painter.end()
        else:
            # Fallback to a styled rectangle
            pixmap = QPixmap(100, 130)
            pixmap.fill(QColor(100, 100, 100))
            painter = QPainter(pixmap)
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, f"Page {self.page_index + 1}")
            painter.end()

        # Set drag pixmap with transparency
        drag.setPixmap(pixmap)
        drag.setHotSpot(pixmap.rect().center())

        # Apply transparency effect to original widget during drag
        opacity_effect = QGraphicsOpacityEffect()
        opacity_effect.setOpacity(0.5)
        self.setGraphicsEffect(opacity_effect)

        # Execute the drag
        drop_action = drag.exec(Qt.DropAction.MoveAction)

        # Restore original widget appearance
        self.setGraphicsEffect(None)

    def mouseDoubleClickEvent(self, event):
        """Handle double click."""
        self.clicked.emit(self.page_index)


class MarginAdjustmentWidget(QWidget):
    """Widget for adjusting page margins interactively."""

    margins_changed = pyqtSignal(dict)  # {"top": int, "bottom": int, "left": int, "right": int}

    def __init__(self, parent=None):
        """Initialize margin adjustment widget."""
        super().__init__(parent)
        self.image_array = None
        self.margins = {"top": 0, "bottom": 0, "left": 0, "right": 0}
        self.dragging_edge = None

        self.image_label = QLabel()
        self.image_label.setStyleSheet("background: #f0f0f0;")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Margin control sliders
        controls_group = QGroupBox("Adjust Margins (pixels)")
        controls_layout = QGridLayout()

        # Top margin
        controls_layout.addWidget(QLabel("Top:"), 0, 0)
        self.top_slider = QSlider(Qt.Orientation.Horizontal)
        self.top_slider.setRange(0, 200)
        self.top_slider.setValue(0)
        self.top_slider.valueChanged.connect(self._on_margin_changed)
        controls_layout.addWidget(self.top_slider, 0, 1)
        self.top_label = QLabel("0px")
        controls_layout.addWidget(self.top_label, 0, 2)

        # Bottom margin
        controls_layout.addWidget(QLabel("Bottom:"), 1, 0)
        self.bottom_slider = QSlider(Qt.Orientation.Horizontal)
        self.bottom_slider.setRange(0, 200)
        self.bottom_slider.setValue(0)
        self.bottom_slider.valueChanged.connect(self._on_margin_changed)
        controls_layout.addWidget(self.bottom_slider, 1, 1)
        self.bottom_label = QLabel("0px")
        controls_layout.addWidget(self.bottom_label, 1, 2)

        # Left margin
        controls_layout.addWidget(QLabel("Left:"), 2, 0)
        self.left_slider = QSlider(Qt.Orientation.Horizontal)
        self.left_slider.setRange(0, 200)
        self.left_slider.setValue(0)
        self.left_slider.valueChanged.connect(self._on_margin_changed)
        controls_layout.addWidget(self.left_slider, 2, 1)
        self.left_label = QLabel("0px")
        controls_layout.addWidget(self.left_label, 2, 2)

        # Right margin
        controls_layout.addWidget(QLabel("Right:"), 3, 0)
        self.right_slider = QSlider(Qt.Orientation.Horizontal)
        self.right_slider.setRange(0, 200)
        self.right_slider.setValue(0)
        self.right_slider.valueChanged.connect(self._on_margin_changed)
        controls_layout.addWidget(self.right_slider, 3, 1)
        self.right_label = QLabel("0px")
        controls_layout.addWidget(self.right_label, 3, 2)

        controls_group.setLayout(controls_layout)

        # Main layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.image_label, 1)
        layout.addWidget(controls_group)

    def set_page_image(self, image_array: np.ndarray) -> None:
        """Set the page image to adjust margins for."""
        self.image_array = image_array
        self._update_preview()

    def _on_margin_changed(self) -> None:
        """Handle margin value changes."""
        self.margins = {
            "top": self.top_slider.value(),
            "bottom": self.bottom_slider.value(),
            "left": self.left_slider.value(),
            "right": self.right_slider.value(),
        }

        self.top_label.setText(f"{self.margins['top']}px")
        self.bottom_label.setText(f"{self.margins['bottom']}px")
        self.left_label.setText(f"{self.margins['left']}px")
        self.right_label.setText(f"{self.margins['right']}px")

        self._update_preview()
        self.margins_changed.emit(self.margins)

    def _update_preview(self) -> None:
        """Update preview with margin visualization."""
        if self.image_array is None:
            return

        try:
            # Create a copy for preview
            preview = self.image_array.copy()
            height, width = preview.shape[:2]

            # Draw margin areas (semi-transparent red)
            alpha = preview.copy()
            cv2.rectangle(alpha, (0, 0), (width, self.margins["top"]), (0, 0, 255), -1)
            cv2.rectangle(
                alpha,
                (0, height - self.margins["bottom"]),
                (width, height),
                (0, 0, 255),
                -1,
            )
            cv2.rectangle(alpha, (0, 0), (self.margins["left"], height), (0, 0, 255), -1)
            cv2.rectangle(
                alpha,
                (width - self.margins["right"], 0),
                (width, height),
                (0, 0, 255),
                -1,
            )

            cv2.addWeighted(alpha, 0.3, preview, 0.7, 0, preview)

            # Convert to QImage and display
            rgb = cv2.cvtColor(preview, cv2.COLOR_BGR2RGB)
            h, w = rgb.shape[:2]
            qt_image = QImage(
                rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888
            )
            pixmap = QPixmap.fromImage(qt_image)
            scaled = pixmap.scaledToHeight(
                400, Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(scaled)
        except Exception as e:
            logger.error(f"Error updating margin preview: {e}")

    def get_margins(self) -> dict:
        """Get current margin values."""
        return self.margins

    def reset_margins(self) -> None:
        """Reset all margins to zero."""
        self.top_slider.setValue(0)
        self.bottom_slider.setValue(0)
        self.left_slider.setValue(0)
        self.right_slider.setValue(0)
