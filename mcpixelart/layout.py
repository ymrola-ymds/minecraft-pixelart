"""Placement layout and coordinate generation for Minecraft functions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from mcpixelart.errors import UsageError


def format_rel(offset: int) -> str:
    """Format relative coordinate offset.

    0 -> '~'
    positive N -> '~N'
    negative -N -> '~-N'
    """
    if offset == 0:
        return "~"
    return f"~{offset}"


@dataclass(frozen=True)
class Placement:
    """Placement specification."""

    orientation: Literal["floor", "wall"] = "wall"
    facing: Literal["south", "north", "east", "west"] = "south"
    coords: Literal["relative", "absolute"] = "relative"
    origin: tuple[int, int, int] | None = None

    def __post_init__(self) -> None:
        if self.orientation not in ("floor", "wall"):
            raise UsageError(f"不正な配置向きです: {self.orientation}")
        if self.facing not in ("south", "north", "east", "west"):
            raise UsageError(f"不正な正面方角です: {self.facing}")
        if self.coords not in ("relative", "absolute"):
            raise UsageError(f"不正な座標指定です: {self.coords}")
        if self.coords == "absolute" and self.origin is None:
            raise UsageError("絶対座標 (--coords absolute) の場合は --origin X Y Z が必須です。")


def get_cell_offsets(
    r: int,
    c: int,
    height: int,
    placement: Placement,
) -> tuple[int, int, int]:
    """Calculate (dx, dy, dz) offset from origin for grid cell (c, r).

    c is column index (0..W-1, left-to-right),
    r is row index (0..H-1, top-to-bottom).
    """
    if placement.orientation == "floor":
        return c, 0, r

    # Wall orientations: origin is bottom-left (0, height-1)
    dy = height - 1 - r
    if placement.facing == "south":
        return c, dy, 0
    elif placement.facing == "north":
        return -c, dy, 0
    elif placement.facing == "east":
        return 0, dy, -c
    elif placement.facing == "west":
        return 0, dy, c

    raise UsageError(f"未対応の配置です: {placement.orientation}, {placement.facing}")


def format_coords(
    dx: int,
    dy: int,
    dz: int,
    placement: Placement,
) -> str:
    """Format single (x, y, z) coordinate according to relative/absolute mode."""
    if placement.coords == "absolute":
        assert placement.origin is not None
        ox, oy, oz = placement.origin
        return f"{ox + dx} {oy + dy} {oz + dz}"
    else:
        return f"{format_rel(dx)} {format_rel(dy)} {format_rel(dz)}"


def get_setblock_coords(
    r: int,
    c: int,
    height: int,
    placement: Placement,
) -> str:
    """Get coordinate string for a single block at (c, r)."""
    dx, dy, dz = get_cell_offsets(r, c, height, placement)
    return format_coords(dx, dy, dz, placement)


def get_fill_coords(
    r: int,
    c_start: int,
    c_end: int,
    height: int,
    placement: Placement,
) -> str:
    """Get coordinate string for a fill range from c_start to c_end on row r."""
    dx1, dy1, dz1 = get_cell_offsets(r, c_start, height, placement)
    dx2, dy2, dz2 = get_cell_offsets(r, c_end, height, placement)
    return f"{format_coords(dx1, dy1, dz1, placement)} {format_coords(dx2, dy2, dz2, placement)}"
