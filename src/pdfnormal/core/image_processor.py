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
        Detect page orientation using rotation angle analysis.

        Uses image moments to detect if text is rotated.

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

            # Apply Canny edge detection
            edges = cv2.Canny(gray, 100, 200)

            # Detect lines using Hough transform
            lines = cv2.HoughLines(edges, 1, np.pi / 180, 100)

            if lines is None or len(lines) < 5:
                return 0  # Default to no rotation

            # Extract angles from detected lines
            angles = []
            for line in lines:
                rho, theta = line[0]
                angle = np.degrees(theta)
                # Normalize angle to 0-90 degrees
                if angle > 90:
                    angle = 180 - angle
                if angle > 45:
                    angle = 90 - angle
                angles.append(angle)

            # Calculate average angle
            avg_angle = np.mean(angles)

            # Determine closest 90-degree rotation
            if abs(avg_angle) < 22.5:
                return 0
            elif avg_angle < 0 and abs(avg_angle) >= 22.5:
                return 270
            elif avg_angle > 0 and abs(avg_angle) >= 22.5:
                return 90
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
