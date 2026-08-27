"""Preview PNG generation with mapped block colors."""

from __future__ import annotations

from pathlib import Path
import numpy as np
from PIL import Image

from mcpixelart.errors import ImageProcessError
from mcpixelart.palette import Palette


def save_preview(
    grid: np.ndarray,
    palette: Palette,
    preview_path: str | Path,
) -> Path:
    """Save mapped block grid as RGBA PNG (1 pixel per block).

    Air cells (-1) are fully transparent. Mapped blocks use palette RGB + 255 alpha.

    Args:
        grid: int32 ndarray of shape (H, W).
        palette: Block Palette.
        preview_path: Output file path for preview.

    Returns:
        Resolved Path to saved preview image.

    Raises:
        ImageProcessError: If saving preview fails.
    """
    path = Path(preview_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)

        height, width = grid.shape
        rgba_img = np.zeros((height, width, 4), dtype=np.uint8)

        opaque_mask = grid >= 0
        if np.any(opaque_mask):
            block_indices = grid[opaque_mask]
            rgb_vals = np.clip(palette.rgb[block_indices], 0, 255).astype(np.uint8)

            rgba_img[opaque_mask, :3] = rgb_vals
            rgba_img[opaque_mask, 3] = 255

        img = Image.fromarray(rgba_img, mode="RGBA")
        img.save(path, format="PNG")
        return path

    except Exception as e:
        raise ImageProcessError(f"プレビュー画像の保存に失敗しました: {e}") from e
