"""PDF geometry helpers for safe cropping.

Margin values come from the UI and may not always be compatible with the
target page's actual size. PyMuPDF can fail when given an invalid crop
rectangle (e.g. negative width/height), so we defensively clamp.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional
import math

import fitz  # PyMuPDF


def compute_safe_cropbox(
    rect: fitz.Rect,
    margins: Mapping[str, Any],
    *,
    epsilon: float = 0.5,
    clamp_rect: Optional[fitz.Rect] = None,
) -> Optional[fitz.Rect]:
    """Compute a cropbox that is always valid for PyMuPDF.

    Args:
        rect: The base page rectangle (typically `page.rect`).
        margins: Dict with keys `top`, `bottom`, `left`, `right`.
        epsilon: Minimum crop size guard to ensure width/height > 0.
        clamp_rect: Rectangle to enforce final cropbox bounds against.
            When PyMuPDF raises "CropBox not in MediaBox", clamping against
            `page.mediabox` is the most reliable fix.

    Returns:
        A safe `fitz.Rect` to pass to `set_cropbox`, or `None` if the
        resulting crop would be effectively the same as the input rect.
    """
    clamp_rect = clamp_rect or rect

    # PyMuPDF uses float page coords; margins may come from UI as ints.
    width = float(rect.width)
    height = float(rect.height)
    if width <= 0 or height <= 0:
        return None

    def _safe_margin(name: str) -> float:
        v = float(margins.get(name, 0) or 0)
        # Guard against NaN/inf which can create invalid cropboxes.
        if not math.isfinite(v):
            return 0.0
        return max(0.0, v)

    left = _safe_margin("left")
    right = _safe_margin("right")
    top = _safe_margin("top")
    bottom = _safe_margin("bottom")

    desired_x0 = float(rect.x0) + left
    desired_x1 = float(rect.x1) - right
    # UI semantics: `top` means trimming from the visual top edge.
    # PyMuPDF coordinates: y increases upwards from the bottom-left.
    # Therefore:
    # - trim visual `bottom` by moving y0 up
    # - trim visual `top` by moving y1 down
    desired_y0 = float(rect.y0) + bottom
    desired_y1 = float(rect.y1) - top

    # Clamp to the page rect with a minimum crop size.
    crop_x0 = min(max(desired_x0, float(rect.x0)), float(rect.x1) - epsilon)
    crop_x1 = max(min(desired_x1, float(rect.x1)), crop_x0 + epsilon)

    crop_y0 = min(max(desired_y0, float(rect.y0)), float(rect.y1) - epsilon)
    crop_y1 = max(min(desired_y1, float(rect.y1)), crop_y0 + epsilon)

    crop_rect = fitz.Rect(crop_x0, crop_y0, crop_x1, crop_y1)

    # Ensure cropbox is also within the MediaBox (or whatever clamp_rect is).
    clamped_x0 = max(crop_rect.x0, float(clamp_rect.x0))
    clamped_y0 = max(crop_rect.y0, float(clamp_rect.y0))
    clamped_x1 = min(crop_rect.x1, float(clamp_rect.x1))
    clamped_y1 = min(crop_rect.y1, float(clamp_rect.y1))

    # Must keep a minimum size; otherwise PyMuPDF can reject it.
    if clamped_x1 <= clamped_x0 + epsilon or clamped_y1 <= clamped_y0 + epsilon:
        return None

    final_crop = fitz.Rect(clamped_x0, clamped_y0, clamped_x1, clamped_y1)

    # If clamping effectively produced the original rect, don't apply crop.
    if (
        abs(final_crop.x0 - rect.x0) < epsilon
        and abs(final_crop.y0 - rect.y0) < epsilon
        and abs(final_crop.x1 - rect.x1) < epsilon
        and abs(final_crop.y1 - rect.y1) < epsilon
    ):
        return None

    return final_crop

