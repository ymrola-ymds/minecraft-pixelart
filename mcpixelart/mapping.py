"""Mapping RGB grid to palette block indices."""

from __future__ import annotations

import numpy as np

from mcpixelart.palette import Palette, find_closest_indices


def map_pixels_to_blocks(
    rgb: np.ndarray,
    opaque: np.ndarray,
    palette: Palette,
) -> np.ndarray:
    """Map RGB pixel grid to block indices in Palette.

    Air cells (where opaque is False) are assigned -1.

    Args:
        rgb: uint8 ndarray of shape (H, W, 3).
        opaque: bool ndarray of shape (H, W).
        palette: Filtered block Palette.

    Returns:
        int32 ndarray of shape (H, W) where values are indices into palette.ids or -1 for air.
    """
    h, w = opaque.shape
    grid = np.full((h, w), -1, dtype=np.int32)

    if np.any(opaque):
        opaque_rgb = rgb[opaque]
        indices = find_closest_indices(opaque_rgb, palette.rgb)
        grid[opaque] = indices

    return grid
