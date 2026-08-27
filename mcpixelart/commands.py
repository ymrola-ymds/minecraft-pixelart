"""Run-length compression and Minecraft command generation."""

from __future__ import annotations

import numpy as np

from mcpixelart.layout import Placement, get_fill_coords, get_setblock_coords
from mcpixelart.palette import Palette


def generate_commands(
    grid: np.ndarray,
    palette: Palette,
    placement: Placement,
) -> list[str]:
    """Generate run-length compressed Minecraft setblock / fill commands.

    Compresses consecutive identical blocks along rows (horizontal runs).
    Air cells (-1) are omitted.

    Args:
        grid: int32 ndarray of shape (H, W) with palette indices (-1 for air).
        palette: Block Palette.
        placement: Placement specification.

    Returns:
        List of command strings (without trailing newlines).
    """
    height, width = grid.shape
    commands: list[str] = []

    for r in range(height):
        c_start = 0
        while c_start < width:
            block_idx = int(grid[r, c_start])
            if block_idx == -1:
                c_start += 1
                continue

            c_end = c_start
            while c_end + 1 < width and grid[r, c_end + 1] == block_idx:
                c_end += 1

            block_id = palette.ids[block_idx]
            run_len = c_end - c_start + 1

            if run_len == 1:
                coords = get_setblock_coords(r, c_start, height, placement)
                commands.append(f"setblock {coords} {block_id}")
            else:
                coords = get_fill_coords(r, c_start, c_end, height, placement)
                commands.append(f"fill {coords} {block_id}")

            c_start = c_end + 1

    return commands
