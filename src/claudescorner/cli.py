"""Command-line interface: ``claudescorner`` or ``python -m claudescorner``."""

import sys
from typing import Optional, Sequence

from PIL import Image, ImageDraw

from . import __version__
from .colors import to_rgb_tuple, validate_color
from .glass import draw_text_with_glass

USAGE = """\
usage: claudescorner [COLOR]
       claudescorner --glass-demo [OUT.png]
       claudescorner (-h | --help | --version)

Check a color and print its RGB value, or render a demo card.

  COLOR          a 6-digit hex code ("#FF5733") or a decimal RGB tuple
                 ("255, 87, 51"); exits 0 if valid, 1 if not
  --glass-demo   draw a stand-in Bio card with glass bubbles behind the text
                 (writes glass_demo.png unless OUT.png is given)

With no arguments, runs the built-in color-validation demo.
"""


def _run_demo() -> None:
    test_cases = [
        "#FF5733", "FF5733",                              # valid: 6-digit hex
        "#f00", "abc",                                    # invalid: 3-digit short-form not accepted
        "(255, 87, 51)", "255, 87, 51", "0,0,0",          # valid: rgb tuple
        "(256, 0, 0)", "#12345", "#GG5733",               # invalid: range/format
        "(255, 87)", "(255, 87, 51", "not a color", "",   # invalid: malformed
    ]
    print(f"{'INPUT':<20}{'VALID':<8}{'FORMAT':<12}REASON")
    print("-" * 65)
    for case in test_cases:
        r = validate_color(case)
        print(f"{case!r:<20}{str(r.is_valid):<8}{(r.format_type or '-'):<12}{r.reason or ''}")

    print("\nto_rgb_tuple examples:")
    for case in ("#FF5733", "255, 87, 51"):
        print(f"  to_rgb_tuple({case!r}) -> {to_rgb_tuple(case)}")
    try:
        to_rgb_tuple("not a color")
    except ValueError as e:
        print(f"  to_rgb_tuple('not a color') -> raised ValueError: {e}")


def _run_glass_demo(out_path: str = "glass_demo.png") -> None:
    """Render a stand-in Bio card, so the glass can be tuned without the bot."""
    import textwrap

    from PIL import ImageFont

    def load(name: str, size: int):
        for path in (f"/usr/share/fonts/truetype/dejavu/{name}.ttf", name):
            try:
                return ImageFont.truetype(path, size=size)
            except OSError:
                continue
        return ImageFont.load_default(size=size)

    width, height = 539, 306
    card = Image.new(mode="RGBA", size=(width, height))
    stripes = ImageDraw.Draw(card)
    for x in range(width + height):
        stripes.line([(x, 0), (x - height, height)],
                     fill=(255 - x // 4, 70 + (x * 7) % 185, 130 + x // 6, 255))

    description = ("i make small tools, drink too much coffee, and think the "
                   "sky looks best right after it rains.")
    blocks = [
        ((22, 13), "about", load("DejaVuSans", 32)),
        ((116, 13), "claude", load("DejaVuSans-Bold", 32)),
        ((22, 50), textwrap.fill(description, width=27), load("DejaVuSans", 20)),
    ]
    draw_text_with_glass(card, blocks, fill=(255, 255, 255))
    card.save(out_path)
    print(f"wrote {out_path}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the command line; returns the process exit code."""
    args = list(sys.argv[1:] if argv is None else argv)

    if args and args[0] in ("-h", "--help"):
        print(USAGE, end="")
        return 0
    if args and args[0] == "--version":
        print(f"claudescorner {__version__}")
        return 0

    if args and args[0] == "--glass-demo":
        _run_glass_demo(args[1] if len(args) > 1 else "glass_demo.png")
        return 0

    if args:
        color_input = args[0]
        result = validate_color(color_input)
        if result.is_valid:
            print(f"'{color_input}' is a valid color ({result.format_type}) -> RGB {to_rgb_tuple(color_input)}")
        else:
            print(f"'{color_input}' is NOT valid: {result.reason}")
        return 0 if result.is_valid else 1

    _run_demo()
    return 0
