"""minecraft-pixelart: Convert images to Minecraft datapacks."""

__version__ = "1.0.0"

from mcpixelart.errors import PixelArtError, UsageError, DataPackError, PaletteError, ImageProcessError
from mcpixelart.palette import Palette, load_palette, find_closest_indices
from mcpixelart.imaging import process_image
from mcpixelart.layout import Placement
from mcpixelart.mapping import map_pixels_to_blocks
from mcpixelart.commands import generate_commands
from mcpixelart.datapack import write_datapack
from mcpixelart.preview import save_preview
from mcpixelart.cli import main

__all__ = [
    "PixelArtError",
    "UsageError",
    "DataPackError",
    "PaletteError",
    "ImageProcessError",
    "Palette",
    "load_palette",
    "find_closest_indices",
    "process_image",
    "Placement",
    "map_pixels_to_blocks",
    "generate_commands",
    "write_datapack",
    "save_preview",
    "main",
]
