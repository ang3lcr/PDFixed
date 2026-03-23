"""Image processing utilities for PDF pages."""

import cv2
import numpy as np
from typing import Tuple
from PIL import Image
import logging

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Utilities for image processing and analysis."""

    @staticmethod
    def detect_blank_page(image_array: np.ndarray, threshold: float = 0.01) -> bool:
        """
        Detect if a page image is blank using Otsu binarization.
        
        Uses advanced algorithm from normalize_pdf.py with automatic thresholding
        via Otsu method for robust blank page detection.

        Args:
            image_array: CV2 image array (BGR)
            threshold: Maximum percentage of dark pixels to consider blank (0.0-1.0)

        Returns:
            True if page is considered blank
        """
        try:
            # Convert to grayscale if necessary
            if len(image_array.shape) == 3:
                if image_array.shape[2] == 3:
                    gray = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
                else:
                    gray = cv2.cvtColor(image_array, cv2.COLOR_BGRA2GRAY)
            else:
                gray = image_array

            # Binarize using Otsu's method (automatic threshold)
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Count dark (non-white) pixels
            non_white = np.count_nonzero(binary == 0)
            total = binary.size
            ratio = non_white / float(total)
            
            # Page is blank if less than threshold% of pixels are dark/content
            is_blank = ratio < threshold
            
            logger.debug(
                f"Blank detection: dark_pixels={non_white} total={total} "
                f"ratio={ratio:.5f} threshold={threshold:.4f} result={is_blank}"
            )
            return is_blank

        except Exception as e:
            logger.error(f"Error detecting blank page: {e}")
            return False

    @staticmethod
    def detect_orientation(image_array: np.ndarray) -> int:
        """
        Detect page orientation using robust edge and content analysis.

        Optimized for scanned documents that are usually landscape.
        Only rotates if orientation is clearly wrong (conservative approach).

        Args:
            image_array: CV2 image array (BGR)

        Returns:
            Rotation angle: 0, 90, 180, or 270 degrees
        """
        try:
            if len(image_array.shape) == 3:
                gray = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
            else:
                gray = image_array

            height, width = gray.shape
            aspect_ratio = width / height if height > 0 else 1

            # If image is already landscape (width > height), default to no rotation
            # Most scanned documents are naturally landscape
            if aspect_ratio > 1.2:  # Already landscape
                logger.debug(f"Page is landscape (aspect {aspect_ratio:.2f}), assuming correct orientation")
                return 0

            # Apply aggressive edge detection for better contours
            edges = cv2.Canny(gray, 50, 150)
            
            # Dilate edges to connect broken lines
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            edges = cv2.dilate(edges, kernel, iterations=2)

            # Detect lines using Hough transform with higher threshold
            lines = cv2.HoughLines(edges, 1, np.pi / 180, 150)  # Increased threshold from 100 to 150

            if lines is None or len(lines) < 10:  # Need more lines for confidence
                logger.debug("Not enough lines detected for orientation")
                return 0

            # Extract angles from detected lines
            angles = []
            for line in lines:
                rho, theta = line[0]
                angle = np.degrees(theta)
                
                # Normalize angle: convert to -45 to 45 range
                if angle > 90:
                    angle = angle - 180
                if angle > 45:
                    angle = angle - 90
                    
                angles.append(angle)

            # Calculate statistics
            angles = np.array(angles)
            median_angle = np.median(angles)
            std_angle = np.std(angles)

            logger.debug(
                f"Orientation detection: median_angle={median_angle:.1f}°, "
                f"std={std_angle:.1f}°, n_lines={len(lines)}"
            )

            # Conservative threshold: only rotate if angle is very clear
            # Increased from 22.5 to 35 degrees for conservative rotation
            threshold = 35

            # Check if the angle is consistent (low std deviation)
            if std_angle > 25:  # Inconsistent angles indicate no clear rotation
                logger.debug(f"Angle is inconsistent (std={std_angle:.1f}), assuming no rotation")
                return 0

            # Determine closest 90-degree rotation only if very clear
            if abs(median_angle) < threshold:
                return 0
            elif abs(median_angle - 90) < threshold:
                return 90
            elif abs(median_angle - (-90)) < threshold:
                return 270
            elif abs(median_angle) > (180 - threshold):
                return 180
            else:
                return 0

        except Exception as e:
            logger.error(f"Error detecting orientation: {e}")
            return 0

    @staticmethod
    def rotate_image(image_array: np.ndarray, angle: int) -> np.ndarray:
        """
        Rotate image by specified angle.

        Args:
            image_array: CV2 image array (BGR)
            angle: Rotation angle (90, 180, 270, or 0)

        Returns:
            Rotated image array
        """
        if angle == 0:
            return image_array
        elif angle == 90:
            return cv2.rotate(image_array, cv2.ROTATE_90_CLOCKWISE)
        elif angle == 180:
            return cv2.rotate(image_array, cv2.ROTATE_180)
        elif angle == 270:
            return cv2.rotate(image_array, cv2.ROTATE_90_COUNTERCLOCKWISE)
        else:
            return image_array

    @staticmethod
    def crop_margins(
        image_array: np.ndarray, top: int, bottom: int, left: int, right: int
    ) -> np.ndarray:
        """
        Crop margins from an image.

        Args:
            image_array: CV2 image array (BGR)
            top, bottom, left, right: Pixels to remove from each side

        Returns:
            Cropped image array
        """
        height, width = image_array.shape[:2]

        # Ensure crop values don't exceed image boundaries
        top = max(0, min(top, height - 1))
        bottom = max(0, min(bottom, height - top - 1))
        left = max(0, min(left, width - 1))
        right = max(0, min(right, width - left - 1))

        return image_array[top : height - bottom, left : width - right]

    @staticmethod
    def calculate_variance(image_array: np.ndarray) -> float:
        """
        Calculate Laplacian variance for image sharpness.

        Args:
            image_array: CV2 image array (BGR)

        Returns:
            Variance value (higher = sharper)
        """
        if len(image_array.shape) == 3:
            gray = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
        else:
            gray = image_array

        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        variance = laplacian.var()
        return float(variance)
