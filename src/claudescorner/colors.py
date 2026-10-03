"""
Color-string validation and conversion.

Validates whether a string represents a color as either:
  1. A 6-digit hex color code   e.g. "#FF5733", "FF5733"
  2. A decimal RGB tuple         e.g. "(255, 87, 51)", "255, 87, 51"
     (each channel must be a valid 8-bit value: 0-255)

Use to_rgb_tuple(value) to convert a valid input into an (r, g, b) int tuple.
"""

import re
from typing import NamedTuple, Optional, Tuple

HEX_COLOR_RE = re.compile(r'^#?[0-9A-Fa-f]{6}$')
RGB_INNER_RE = re.compile(r'^(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})$')


class ColorValidationResult(NamedTuple):
    is_valid: bool
    format_type: Optional[str]    # "hex", "rgb_tuple", or None
    reason: Optional[str] = None  # set when is_valid is False


def is_valid_hex_color(value: str) -> bool:
    """True if `value` is a 6-digit hex color, with an optional leading '#'."""
    return bool(HEX_COLOR_RE.match(value.strip()))


def _parse_rgb_tuple(value: str) -> Optional[Tuple[int, int, int]]:
    """Parse `value` as an (r, g, b) int tuple structurally, ignoring range."""
    s = value.strip()
    if s.startswith('(') and s.endswith(')'):
        s = s[1:-1].strip()
    elif s.startswith('(') != s.endswith(')'):
        return None  # unmatched parenthesis
    match = RGB_INNER_RE.match(s)
    return tuple(int(x) for x in match.groups()) if match else None


def is_valid_rgb_tuple(value: str) -> bool:
    """True if `value` is a decimal RGB tuple string with each channel in [0, 255]."""
    channels = _parse_rgb_tuple(value)
    return channels is not None and all(0 <= c <= 255 for c in channels)


def is_valid_color(value: str) -> bool:
    """True if `value` is a valid 6-digit hex code or an 8-bit decimal RGB tuple."""
    return is_valid_hex_color(value) or is_valid_rgb_tuple(value)


def validate_color(value: str) -> ColorValidationResult:
    """Validate `value`, returning (is_valid, format_type, reason-if-invalid)."""
    if not value.strip():
        return ColorValidationResult(False, None, "empty string")

    if is_valid_hex_color(value):
        return ColorValidationResult(True, "hex")

    channels = _parse_rgb_tuple(value)
    if channels is not None:
        if all(0 <= c <= 255 for c in channels):
            return ColorValidationResult(True, "rgb_tuple")
        return ColorValidationResult(False, None, "RGB values must each be between 0 and 255")

    return ColorValidationResult(False, None, "not a recognized hex code or RGB tuple")


def to_rgb_tuple(value: str) -> Tuple[int, int, int]:
    """
    Convert a valid hex color code or RGB tuple string into an (r, g, b) tuple.
    Raises ValueError if `value` is not a valid color.
    """
    result = validate_color(value)
    if not result.is_valid:
        raise ValueError(f"cannot convert {value!r} to RGB: {result.reason}")

    if result.format_type == "hex":
        s = value.strip()
        if s.startswith('#'):
            s = s[1:]
        return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))

    return _parse_rgb_tuple(value)
