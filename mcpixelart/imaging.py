"""Image loading, alpha handling, resizing with LANCZOS, and transformations."""

from __future__ import annotations

from pathlib import Path
import numpy as np
from PIL import Image

from mcpixelart.errors import ImageProcessError, UsageError


def process_image(
    image_path: str | Path,
    width: int,
    height: int,
    rotation: int = 0,
    mirror_horizontal: bool = False,
) -> tuple[np.ndarray, np.ndarray, tuple[int, int]]:
    """Load image, resize with premultiplied alpha LANCZOS, rotate, and mirror.

    Args:
        image_path: Path to input image.
        width: Target grid width before rotation.
        height: Target grid height before rotation.
        rotation: Clockwise rotation in degrees (0, 90, 180, 270).
        mirror_horizontal: Whether to flip horizontally after rotation.

    Returns:
        tuple of:
          - rgb: uint8 ndarray of shape (final_h, final_w, 3)
          - opaque: bool ndarray of shape (final_h, final_w), True where alpha > 0
          - orig_size: tuple (orig_w, orig_h)

    Raises:
        ImageProcessError: If image cannot be read or processed.
        UsageError: If dimensions or rotation angle are invalid.
    """
    if width <= 0 or height <= 0:
        raise UsageError("幅 (width) および高さ (height) は 1 以上の整数を指定してください。")

    if rotation not in (0, 90, 180, 270):
        raise UsageError(f"回転角 (rotation) は 0, 90, 180, 270 のいずれかを指定してください (指定値: {rotation})。")

    path = Path(image_path)
    if not path.exists():
        raise ImageProcessError(f"入力画像が見つかりません: {path}")

    try:
        with Image.open(path) as img:
            img_rgba = img.convert("RGBA")
            orig_size = img_rgba.size  # (orig_w, orig_h)
            arr = np.array(img_rgba, dtype=np.float32)
    except Exception as e:
        raise ImageProcessError(f"画像の読み込みに失敗しました: {e}") from e

    r = arr[..., 0]
    g = arr[..., 1]
    b = arr[..., 2]
    a = arr[..., 3]

    # Premultiplied alpha to prevent color bleeding at transparent boundaries
    alpha_norm = a / 255.0
    pr = r * alpha_norm
    pg = g * alpha_norm
    pb = b * alpha_norm

    pr_img = Image.fromarray(np.clip(pr, 0, 255).astype(np.uint8))
    pg_img = Image.fromarray(np.clip(pg, 0, 255).astype(np.uint8))
    pb_img = Image.fromarray(np.clip(pb, 0, 255).astype(np.uint8))
    a_img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

    resample_filter = Image.Resampling.LANCZOS
    pr_resized = np.array(pr_img.resize((width, height), resample_filter), dtype=np.float32)
    pg_resized = np.array(pg_img.resize((width, height), resample_filter), dtype=np.float32)
    pb_resized = np.array(pb_img.resize((width, height), resample_filter), dtype=np.float32)
    a_resized = np.array(a_img.resize((width, height), resample_filter), dtype=np.float32)

    opaque = a_resized > 0
    rgb_out = np.zeros((height, width, 3), dtype=np.uint8)

    # Demultiply alpha where alpha > 0
    if np.any(opaque):
        valid_alpha = a_resized[opaque] / 255.0
        r_rec = np.clip(pr_resized[opaque] / valid_alpha, 0, 255).astype(np.uint8)
        g_rec = np.clip(pg_resized[opaque] / valid_alpha, 0, 255).astype(np.uint8)
        b_rec = np.clip(pb_resized[opaque] / valid_alpha, 0, 255).astype(np.uint8)

        rgb_out[opaque, 0] = r_rec
        rgb_out[opaque, 1] = g_rec
        rgb_out[opaque, 2] = b_rec

    # Rotation (clockwise: 90, 180, 270)
    if rotation == 90:
        rgb_out = np.rot90(rgb_out, k=-1, axes=(0, 1))
        opaque = np.rot90(opaque, k=-1, axes=(0, 1))
    elif rotation == 180:
        rgb_out = np.rot90(rgb_out, k=2, axes=(0, 1))
        opaque = np.rot90(opaque, k=2, axes=(0, 1))
    elif rotation == 270:
        rgb_out = np.rot90(rgb_out, k=1, axes=(0, 1))
        opaque = np.rot90(opaque, k=1, axes=(0, 1))

    # Mirror horizontal (flip left/right)
    if mirror_horizontal:
        rgb_out = np.fliplr(rgb_out)
        opaque = np.fliplr(opaque)

    # Ensure contiguous array
    rgb_out = np.ascontiguousarray(rgb_out)
    opaque = np.ascontiguousarray(opaque)

    return rgb_out, opaque, orig_size
