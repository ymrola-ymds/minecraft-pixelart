"""Palette loading and color matching using vectorized redmean."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
import numpy as np

from mcpixelart.errors import PaletteError

DEFAULT_EXCLUDE_TAGS = {
    "liquid",
    "functional",
    "non_full_cube",
    "ice",
    "slime",
    "honey",
    "leaves",
}


@dataclass(frozen=True)
class Palette:
    """Minecraft block palette."""

    ids: list[str]
    rgb: np.ndarray  # shape (N, 3), float32
    version: str


def load_palette(
    palette_path: str | Path,
    use_gravity_blocks: bool = False,
) -> Palette:
    """Load palette JSON and filter blocks according to tag rules.

    Args:
        palette_path: Path to palette JSON file.
        use_gravity_blocks: Whether to include gravity-affected blocks.

    Returns:
        Palette instance containing filtered blocks.

    Raises:
        PaletteError: If file not found, schema invalid, or 0 blocks remain.
    """
    path = Path(palette_path)
    if not path.exists():
        raise PaletteError(f"パレットファイルが見つかりません: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        raise PaletteError(f"パレット JSON の読み込みに失敗しました: {e}") from e

    version = data.get("minecraft_version", "unknown")
    blocks = data.get("blocks", [])
    if not isinstance(blocks, list):
        raise PaletteError("パレット JSON の 'blocks' フィールドが不正です。")

    exclude_tags = set(DEFAULT_EXCLUDE_TAGS)
    if not use_gravity_blocks:
        exclude_tags.add("gravity")

    valid_ids: list[str] = []
    valid_rgbs: list[list[float]] = []

    for item in blocks:
        block_id = item.get("id")
        rgb = item.get("rgb")
        tags = set(item.get("tags", []))

        if not block_id or not isinstance(rgb, (list, tuple)) or len(rgb) != 3:
            continue

        # Check if block has any excluded tag
        if tags & exclude_tags:
            continue

        valid_ids.append(block_id)
        valid_rgbs.append([float(c) for c in rgb])

    if not valid_ids:
        raise PaletteError("有効なパレット候補ブロックが 0 件になりました。")

    rgb_array = np.array(valid_rgbs, dtype=np.float32)
    return Palette(ids=valid_ids, rgb=rgb_array, version=version)


def find_closest_indices(
    rgb_pixels: np.ndarray,
    palette_rgb: np.ndarray,
    chunk_size: int = 4096,
) -> np.ndarray:
    """Find closest palette block index for each pixel using redmean color distance.

    Memory efficient: uses np.unique and evaluates distances in chunks.

    Args:
        rgb_pixels: Input RGB pixels, shape (..., 3), dtype convertible to float32.
        palette_rgb: Palette RGB colors, shape (N, 3), dtype float32.
        chunk_size: Number of unique colors to process per chunk.

    Returns:
        Array of indices into palette, shape matching rgb_pixels.shape[:-1], dtype int32.
    """
    orig_shape = rgb_pixels.shape[:-1]
    flat_pixels = rgb_pixels.reshape(-1, 3).astype(np.float32)

    unique_colors, inverse_indices = np.unique(flat_pixels, axis=0, return_inverse=True)
    num_uniques = len(unique_colors)
    unique_best = np.empty(num_uniques, dtype=np.int32)

    palette_r = palette_rgb[:, 0]
    palette_g = palette_rgb[:, 1]
    palette_b = palette_rgb[:, 2]

    for start in range(0, num_uniques, chunk_size):
        end = min(start + chunk_size, num_uniques)
        chunk = unique_colors[start:end]

        r1 = chunk[:, 0:1]  # (B, 1)
        g1 = chunk[:, 1:2]
        b1 = chunk[:, 2:3]

        r2 = palette_r[None, :]  # (1, N)
        g2 = palette_g[None, :]
        b2 = palette_b[None, :]

        r_mean = (r1 + r2) / 2.0
        dr = r1 - r2
        dg = g1 - g2
        db = b1 - b2

        dist = (
            (2.0 + r_mean / 256.0) * (dr**2)
            + 4.0 * (dg**2)
            + (2.0 + (255.0 - r_mean) / 256.0) * (db**2)
        )
        unique_best[start:end] = np.argmin(dist, axis=1)

    result = unique_best[inverse_indices].reshape(orig_shape).astype(np.int32)
    return result
