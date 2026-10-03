import pytest
from PIL import Image, ImageDraw, ImageFont

from claudescorner import (
    GLASS_DARK,
    GLASS_LIGHT,
    draw_glass_panel,
    draw_text_with_glass,
    glass_boxes_for_text,
    glass_style_for,
)

BLUE = (40, 90, 160, 255)
WHITE = (255, 255, 255)


@pytest.fixture(scope="module")
def font():
    return ImageFont.load_default(size=24)


def canvas(size=(320, 160), color=BLUE):
    return Image.new("RGBA", size, color)


def luminance(rgb):
    """WCAG relative luminance, written out independently of the library."""
    def channel(v):
        c = v / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(v) for v in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(first, second):
    hi, lo = sorted((luminance(first), luminance(second)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def inside_left_padding(box):
    """A pixel well inside the bubble but left of any text."""
    x0, y0, _, y1 = box
    return (x0 + 8, (y0 + y1) // 2)


# --------------------------------------------------------------------------- #
# Style selection and geometry
# --------------------------------------------------------------------------- #

def test_glass_style_follows_text_brightness():
    assert glass_style_for((255, 255, 255)) is GLASS_DARK   # light text -> smoked glass
    assert glass_style_for((0, 0, 0)) is GLASS_LIGHT        # dark text  -> frosted glass


def test_bubble_is_the_text_box_plus_padding(font):
    image = canvas()
    ink = ImageDraw.Draw(image).textbbox((40, 40), "hello", font=font)
    (box,) = glass_boxes_for_text(image, [((40, 40), "hello", font)], pad=(16, 10))
    assert box[0] == ink[0] - 16
    assert box[2] == ink[2] + 16
    assert box[1] <= ink[1] - 10
    assert box[3] >= ink[3] + 10


def test_bubble_boxes_are_clipped_to_the_image(font):
    image = canvas((100, 60))
    (box,) = glass_boxes_for_text(image, [((2, 2), "a wide piece of text", font)])
    assert box[0] == 0 and box[1] == 0
    assert box[2] == image.width


def test_touching_blocks_share_one_bubble(font):
    image = canvas((400, 200))
    blocks = [((20, 20), "about", font), ((25, 22), "claude", font)]
    assert len(glass_boxes_for_text(image, blocks)) == 1


def test_distant_blocks_get_their_own_bubbles(font):
    image = canvas((400, 200))
    blocks = [((10, 10), "top", font), ((10, 150), "bottom", font)]
    assert len(glass_boxes_for_text(image, blocks)) == 2


def test_multiline_text_makes_a_taller_bubble(font):
    image = canvas((400, 200))
    (one,) = glass_boxes_for_text(image, [((20, 20), "one line", font)])
    (two,) = glass_boxes_for_text(image, [((20, 20), "two\nlines", font)])
    assert (two[3] - two[1]) > (one[3] - one[1])


def test_blank_and_none_text_gets_no_bubble(font):
    image = canvas()
    blocks = [((10, 10), "", font), ((10, 40), "   ", font), ((10, 70), None, font)]
    assert glass_boxes_for_text(image, blocks) == []
    assert draw_text_with_glass(image, blocks, fill=WHITE) == []


# --------------------------------------------------------------------------- #
# Painting
# --------------------------------------------------------------------------- #

def test_bubble_is_painted_and_far_pixels_are_untouched(font):
    backdrop = canvas()
    image = backdrop.copy()
    boxes = draw_text_with_glass(image, [((60, 50), "hello", font)], fill=WHITE)
    assert len(boxes) == 1
    spot = inside_left_padding(boxes[0])
    assert image.getpixel(spot) != backdrop.getpixel(spot)
    for corner in [(0, 0), (image.width - 1, image.height - 1)]:
        assert image.getpixel(corner) == backdrop.getpixel(corner)


def test_glass_can_be_switched_off(font):
    blocks = [((60, 50), "hello", font)]
    backdrop = canvas()
    (box,) = glass_boxes_for_text(backdrop, blocks)
    spot = inside_left_padding(box)

    image = backdrop.copy()
    assert draw_text_with_glass(image, blocks, fill=WHITE, glass=False) == []
    assert image.getpixel(spot) == backdrop.getpixel(spot)  # text only, no bubble
    assert image.tobytes() != backdrop.tobytes()  # ...but the text itself was drawn


def test_rgb_images_are_supported(font):
    image = Image.new("RGB", (200, 100), (200, 30, 30))
    boxes = draw_text_with_glass(image, [((20, 20), "hi", font)], fill=WHITE)
    assert boxes
    assert image.mode == "RGB"


def test_bubble_paints_on_a_fully_transparent_backdrop(font):
    image = Image.new("RGBA", (200, 100), (0, 0, 0, 0))
    (box,) = draw_text_with_glass(image, [((30, 30), "hi", font)], fill=WHITE)
    assert image.getpixel(inside_left_padding(box))[3] > 0  # the glass carries its own alpha


def test_tiny_panels_are_ignored():
    image = canvas()
    before = image.tobytes()
    draw_glass_panel(image, (5, 5, 7, 7))
    draw_glass_panel(image, (10, 10, 200, 13))
    assert image.tobytes() == before
    draw_glass_panel(image, (10, 10, 200, 60))  # control: a normal panel does paint
    assert image.tobytes() != before


# --------------------------------------------------------------------------- #
# The readability promise
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    "backdrop, fill",
    [
        ((255, 255, 255, 255), (255, 255, 255)),   # white text on white
        ((255, 240, 0, 255), (255, 255, 255)),     # white text on yellow
        ((140, 140, 140, 255), (255, 255, 255)),   # white text on mid grey
        ((0, 0, 0, 255), (0, 0, 0)),               # black text on black
        ((10, 10, 90, 255), (10, 10, 30)),         # dark text on navy
    ],
)
def test_text_keeps_its_contrast_over_awkward_backdrops(font, backdrop, fill):
    image = canvas(color=backdrop)
    (box,) = draw_text_with_glass(image, [((60, 50), "hello", font)], fill=fill)
    x0, y0, x1, y1 = box
    for spot in [inside_left_padding(box), (x0 + 12, y0 + 12), ((x0 + x1) // 2, y1 - 6)]:
        # 4.5 is the default target; leave a little room for rounding.
        assert contrast(image.getpixel(spot), fill) >= 4.4, spot


def test_tint_only_firms_up_when_text_colour_is_given():
    box = (40, 40, 240, 120)
    loose, firm = canvas(color=(255, 255, 255, 255)), canvas(color=(255, 255, 255, 255))
    draw_glass_panel(loose, box, style=GLASS_DARK)
    draw_glass_panel(firm, box, style=GLASS_DARK, text_color=WHITE)
    spot = (box[0] + 8, (box[1] + box[3]) // 2)
    assert contrast(loose.getpixel(spot), WHITE) < 4.0
    assert contrast(firm.getpixel(spot), WHITE) >= 4.4
