"""Error classes for minecraft-pixelart."""


class PixelArtError(Exception):
    """Base exception for all minecraft-pixelart errors."""

    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code


class UsageError(PixelArtError):
    """Raised when command-line arguments are invalid (exit code 2)."""

    def __init__(self, message: str) -> None:
        super().__init__(message, exit_code=2)


class DataPackError(PixelArtError):
    """Raised when datapack generation fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message, exit_code=1)


class PaletteError(PixelArtError):
    """Raised when palette loading or processing fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message, exit_code=1)


class ImageProcessError(PixelArtError):
    """Raised when image reading or processing fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message, exit_code=1)
