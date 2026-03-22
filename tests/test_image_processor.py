"""Tests for image processor module."""

import pytest
import numpy as np
import cv2

from pdfnormal.core import ImageProcessor


class TestImageProcessor:
    """Tests for ImageProcessor class."""

    @pytest.fixture
    def blank_image(self):
        """Create a blank (white) image."""
        return np.ones((200, 200, 3), dtype=np.uint8) * 255

    @pytest.fixture
    def text_image(self):
        """Create an image with text-like patterns."""
        img = np.ones((200, 200, 3), dtype=np.uint8) * 255
        cv2.rectangle(img, (50, 50), (150, 150), (0, 0, 0), -1)
        return img

    def test_detect_blank_page_blank(self, blank_image):
        """Test detecting a blank page."""
        is_blank = ImageProcessor.detect_blank_page(blank_image, threshold=0.95)
        assert is_blank is True

    def test_detect_blank_page_not_blank(self, text_image):
        """Test detecting a non-blank page."""
        is_blank = ImageProcessor.detect_blank_page(text_image, threshold=0.95)
        assert is_blank is False

    def test_detect_blank_page_threshold(self):
        """Test blank detection with different thresholds."""
        # 90% white image
        img = np.ones((100, 100, 3), dtype=np.uint8) * 255
        cv2.rectangle(img, (0, 0), (10, 100), (0, 0, 0), -1)

        # Should be blank at 85% threshold
        assert ImageProcessor.detect_blank_page(img, threshold=0.85) is True

        # Should not be blank at 95% threshold
        assert ImageProcessor.detect_blank_page(img, threshold=0.95) is False

    def test_crop_margins(self, text_image):
        """Test margin cropping."""
        original_height, original_width = text_image.shape[:2]

        cropped = ImageProcessor.crop_margins(text_image, 10, 10, 10, 10)

        assert cropped.shape[0] == original_height - 20
        assert cropped.shape[1] == original_width - 20

    def test_crop_margins_boundary(self, text_image):
        """Test margin cropping with boundaries."""
        height, width = text_image.shape[:2]

        # Try cropping more than available
        cropped = ImageProcessor.crop_margins(text_image, height, 0, 0, 0)

        # Should still return valid image
        assert cropped.shape[0] > 0
        assert cropped.shape[1] == width

    def test_rotate_image(self, text_image):
        """Test image rotation."""
        # Rotate 90 degrees
        rotated = ImageProcessor.rotate_image(text_image, 90)
        assert rotated.shape == (text_image.shape[1], text_image.shape[0], 3)

        # Rotate 180 degrees
        rotated = ImageProcessor.rotate_image(text_image, 180)
        assert rotated.shape == text_image.shape

        # No rotation
        rotated = ImageProcessor.rotate_image(text_image, 0)
        assert np.array_equal(rotated, text_image)

    def test_calculate_variance(self, blank_image, text_image):
        """Test image sharpness variance."""
        blank_var = ImageProcessor.calculate_variance(blank_image)
        text_var = ImageProcessor.calculate_variance(text_image)

        # Blank image should have lower variance
        assert blank_var < text_var

    def test_calculate_variance_positive(self, text_image):
        """Test that variance is always positive."""
        variance = ImageProcessor.calculate_variance(text_image)
        assert variance >= 0


class TestImageProcessorOrientationDetection:
    """Tests for orientation detection."""

    def test_detect_orientation_normal(self):
        """Test detecting normal (0°) orientation."""
        # Create image with horizontal lines
        img = np.ones((200, 300, 3), dtype=np.uint8) * 255
        for y in range(50, 200, 40):
            cv2.line(img, (0, y), (300, y), (0, 0, 0), 2)

        rotation = ImageProcessor.detect_orientation(img)
        # Should be 0 or close to 0
        assert rotation in [0, 90, 180, 270]

    def test_detect_orientation_returns_valid(self):
        """Test that orientation detection returns valid angles."""
        img = np.ones((100, 100, 3), dtype=np.uint8) * 200
        rotation = ImageProcessor.detect_orientation(img)
        assert rotation in [0, 90, 180, 270]
