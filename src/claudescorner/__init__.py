"""
claudescorner -- helper routines for the Bio cog.

Colour parsing
--------------
Validates whether a string represents a color as either:
  1. A 6-digit hex color code   e.g. "#FF5733", "FF5733"
  2. A decimal RGB tuple         e.g. "(255, 87, 51)", "255, 87, 51"
     (each channel must be a valid 8-bit value: 0-255)

Use to_rgb_tuple(value) to convert a valid input into an (r, g, b) int tuple.

Liquid-glass text backing
-------------------------
draw_text_with_glass(image, blocks, fill) measures every text block, groups the
ones that would touch, paints a frosted glass bubble behind each group, then
draws the text on top.  A bubble is only ever the text's own bounding box plus a
little padding, so it can only cover the whole background if the text already
did.

Command line:
    claudescorner "#FF5733"
    claudescorner "255, 87, 51"
    claudescorner --glass-demo [out.png]
    claudescorner              # runs built-in demo

(``python -m claudescorner`` works too.)
"""

from importlib.metadata import PackageNotFoundError, version as _version

from .colors import (
    HEX_COLOR_RE,
    RGB_INNER_RE,
    ColorValidationResult,
    is_valid_color,
    is_valid_hex_color,
    is_valid_rgb_tuple,
    to_rgb_tuple,
    validate_color,
)
from .glass import (
    GLASS_DARK,
    GLASS_LIGHT,
    Box,
    GlassStyle,
    TextBlock,
    draw_glass_panel,
    draw_text_with_glass,
    glass_boxes_for_text,
    glass_style_for,
)

try:
    __version__ = _version("claudescorner")
except PackageNotFoundError:  # running from a source checkout that isn't pip-installed
    __version__ = "0+unknown"

__all__ = [
    "__version__",
    # colors
    "HEX_COLOR_RE",
    "RGB_INNER_RE",
    "ColorValidationResult",
    "is_valid_color",
    "is_valid_hex_color",
    "is_valid_rgb_tuple",
    "to_rgb_tuple",
    "validate_color",
    # glass
    "Box",
    "GLASS_DARK",
    "GLASS_LIGHT",
    "GlassStyle",
    "TextBlock",
    "draw_glass_panel",
    "draw_text_with_glass",
    "glass_boxes_for_text",
    "glass_style_for",
]
