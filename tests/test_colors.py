import pytest

from claudescorner import (
    ColorValidationResult,
    is_valid_color,
    is_valid_hex_color,
    is_valid_rgb_tuple,
    to_rgb_tuple,
    validate_color,
)

VALID_HEX = ["#FF5733", "FF5733", "#ff5733", "  #FF5733  ", "000000", "#ffffff"]
VALID_RGB = ["(255, 87, 51)", "255, 87, 51", "0,0,0", " ( 1 , 2 , 3 ) ", "(255,255,255)"]
OUT_OF_RANGE = ["(256, 0, 0)", "0, 999, 0", "0, 0, 256"]
# 3-digit shorthand is deliberately not accepted.
NOT_A_COLOR = [
    "#f00", "abc", "#12345", "#GG5733", "#FF57330", "##FF5733",
    "(255, 87)", "(255, 87, 51", "255, 87, 51)", "1,2,3,4", "-1, 0, 0",
    "(a, b, c)", "1000, 0, 0", "not a color", "", "   ",
]


@pytest.mark.parametrize("value", VALID_HEX)
def test_valid_hex(value):
    assert is_valid_hex_color(value)
    assert not is_valid_rgb_tuple(value)
    assert is_valid_color(value)
    assert validate_color(value) == ColorValidationResult(True, "hex")


@pytest.mark.parametrize("value", VALID_RGB)
def test_valid_rgb_tuple(value):
    assert is_valid_rgb_tuple(value)
    assert not is_valid_hex_color(value)
    assert is_valid_color(value)
    assert validate_color(value) == ColorValidationResult(True, "rgb_tuple")


@pytest.mark.parametrize("value", OUT_OF_RANGE)
def test_channels_above_255_are_rejected(value):
    assert not is_valid_rgb_tuple(value)
    assert not is_valid_color(value)
    assert validate_color(value) == ColorValidationResult(
        False, None, "RGB values must each be between 0 and 255"
    )


@pytest.mark.parametrize("value", NOT_A_COLOR)
def test_unrecognised_strings(value):
    result = validate_color(value)
    assert result.is_valid is False
    assert result.format_type is None
    assert result.reason
    assert not is_valid_color(value)


def test_reasons():
    assert validate_color("").reason == "empty string"
    assert validate_color("   ").reason == "empty string"
    assert validate_color("nope").reason == "not a recognized hex code or RGB tuple"


@pytest.mark.parametrize(
    "value, expected",
    [
        ("#FF5733", (255, 87, 51)),
        ("ff5733", (255, 87, 51)),
        ("  #000000 ", (0, 0, 0)),
        ("255, 87, 51", (255, 87, 51)),
        ("(0,0,0)", (0, 0, 0)),
        (" ( 1 , 2 , 3 ) ", (1, 2, 3)),
    ],
)
def test_to_rgb_tuple(value, expected):
    assert to_rgb_tuple(value) == expected


@pytest.mark.parametrize("value", ["not a color", "", "(256, 0, 0)", "#f00"])
def test_to_rgb_tuple_rejects_invalid_input(value):
    with pytest.raises(ValueError, match="cannot convert"):
        to_rgb_tuple(value)
