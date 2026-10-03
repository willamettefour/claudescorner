"""
Liquid-glass text backing.

draw_text_with_glass(image, blocks, fill) measures every text block, groups the
ones that would touch, paints a frosted glass bubble behind each group, then
draws the text on top.  A bubble is only ever the text's own bounding box plus a
little padding, so it can only cover the whole background if the text already
did.
"""

from typing import Iterable, List, NamedTuple, Optional, Sequence, Tuple

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageStat

Box = Tuple[int, int, int, int]
TextBlock = Tuple[Tuple[int, int], str, object]  # ((x, y), text, PIL font)


class GlassStyle(NamedTuple):
    """
    Appearance of one glass bubble.  All alphas are 0-255.

    tint        flat colour laid over the frosted backdrop (the glass itself)
    saturation  colour boost applied to the frost, so it doesn't go muddy
    sheen       strength of the specular gradient down from the top edge
    bounce      light pooling back up from the bottom edge
    edge        colour + alpha of the rim highlight
    shadow      alpha of the drop shadow, 0 to disable
    refraction  width of the lensed rim as a fraction of the corner radius
    blur        frost radius, in pixels
    contrast    WCAG contrast ratio to hold between the text and the glass;
                the tint alpha is raised (never past `tint_ceiling`) over
                backdrops that would otherwise swallow the text
    tint_ceiling  hard limit on that alpha, so the glass stays see-through
    """
    tint: Tuple[int, int, int, int] = (255, 255, 255, 94)
    saturation: float = 1.5
    sheen: int = 66
    bounce: int = 30
    edge: Tuple[int, int, int, int] = (255, 255, 255, 170)
    shadow: int = 46
    refraction: float = 0.85
    blur: float = 9.0
    contrast: float = 4.5
    tint_ceiling: int = 196


#: Frosted white glass, for dark text.
GLASS_LIGHT = GlassStyle()

#: Smoked glass, for light text.
GLASS_DARK = GlassStyle(
    tint=(10, 12, 20, 96),
    saturation=1.45,
    sheen=46,
    bounce=20,
    edge=(255, 255, 255, 112),
    shadow=72,
)


def _relative_luminance(rgb: Sequence[int]) -> float:
    """WCAG relative luminance, 0.0 (black) to 1.0 (white)."""
    def channel(value: int) -> float:
        c = value / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in tuple(rgb)[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def glass_style_for(font_color: Sequence[int]) -> GlassStyle:
    """Pick smoked or frosted glass, whichever `font_color` reads better against."""
    return GLASS_DARK if _relative_luminance(font_color) > 0.45 else GLASS_LIGHT


def _supersample_for(width: int, height: int, requested: int, budget: int = 8_000_000) -> int:
    """Clamp the supersampling factor so masks stay within a pixel budget."""
    affordable = int((budget / max(1, width * height)) ** 0.5)
    return max(1, min(requested, affordable))


def _rounded_mask(size: Tuple[int, int], radius: float, inset: float = 0.0,
                  supersample: int = 4) -> Image.Image:
    """An antialiased rounded-rectangle mask, optionally shrunk by `inset` px."""
    width, height = size
    scale = _supersample_for(width, height, supersample)
    mask = Image.new(mode="L", size=(width * scale, height * scale), color=0)
    offset = inset * scale
    right, bottom = width * scale - 1 - offset, height * scale - 1 - offset
    if right > offset and bottom > offset:
        ImageDraw.Draw(mask).rounded_rectangle(
            [(offset, offset), (right, bottom)],
            radius=max(0.0, radius - inset) * scale,
            fill=255,
        )
    return mask.resize(size, Image.Resampling.LANCZOS)


def _contrast_ratio(first: float, second: float) -> float:
    """WCAG contrast ratio between two relative luminances."""
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def _tint_alpha_for(frost: Image.Image, style: GlassStyle, text_color: Sequence[int]) -> int:
    """
    How opaque the tint has to be for `text_color` to stay readable on `frost`.

    Judged against the bright (or dark) end of the backdrop rather than its
    average, since text fails over the worst patch, not the typical one.  Where
    the backdrop is transparent there is nothing to measure, so the glass
    assumes the least helpful client theme and stands on its own.
    """
    text_luma = _relative_luminance(text_color)
    text_is_light = text_luma > 0.45
    stat = ImageStat.Stat(frost.convert(mode="L"))
    extreme = stat.mean[0] + (1.1 * stat.stddev[0] if text_is_light else -1.1 * stat.stddev[0])

    opacity = ImageStat.Stat(frost.getchannel("A")).mean[0] / 255
    extreme = extreme * opacity + (255 if text_is_light else 0) * (1 - opacity)
    extreme = min(255.0, max(0.0, extreme))

    # The sheen goes on after the tint and only ever brightens, so it counts
    # against light text and is simply absent from the worst spot for dark text.
    lit = max(style.sheen, style.bounce) / 255 if text_is_light else 0.0

    floor, ceiling = style.tint[3], max(style.tint[3], style.tint_ceiling)
    for _ in range(10):  # bisect on alpha; the gamma makes a closed form ugly
        middle = (floor + ceiling) / 2
        surface = [(extreme * (1 - middle / 255) + tint * (middle / 255)) * (1 - lit) + 255 * lit
                   for tint in style.tint[:3]]
        if _contrast_ratio(text_luma, _relative_luminance(surface)) >= style.contrast:
            ceiling = middle
        else:
            floor = middle
    return int(round(ceiling))


def _sheen(size: Tuple[int, int], style: GlassStyle) -> Image.Image:
    """A white gradient: bright under the top edge, with a little bounce at the bottom."""
    width, height = size
    layer = Image.new(mode="RGBA", size=size, color=(255, 255, 255, 0))
    draw = ImageDraw.Draw(layer)
    top_run = max(1, int(height * 0.55))
    bottom_run = max(1, int(height * 0.28))
    for y in range(height):
        top = style.sheen * (1 - y / top_run) ** 1.7 if y < top_run else 0.0
        depth = height - 1 - y
        bounce = style.bounce * (1 - depth / bottom_run) ** 2.2 if depth < bottom_run else 0.0
        alpha = round(max(top, bounce))
        if alpha > 0:
            draw.line([(0, y), (width, y)], fill=(255, 255, 255, alpha))
    return layer


def draw_glass_panel(image: Image.Image, box: Box, radius: Optional[float] = None,
                     style: Optional[GlassStyle] = None, text_color: Optional[Sequence[int]] = None,
                     supersample: int = 4) -> None:
    """
    Paint a liquid-glass bubble over `box` = (x0, y0, x1, y1) of `image`, in place.

    The backdrop inside the box is frosted, bent through the curved rim, tinted,
    then lit from the top edge.  `image` should be RGBA; the bubble carries its
    own alpha, so it stays visible even where the background behind it is
    transparent.  Pass `text_color` to have the tint firm up automatically over
    backdrops that would otherwise swallow the text.
    """
    style = style or GLASS_LIGHT
    x0, y0, x1, y1 = (int(round(v)) for v in box)
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(image.width, x1), min(image.height, y1)
    width, height = x1 - x0, y1 - y0
    if width < 4 or height < 4:
        return

    if radius is None:
        radius = min(24, min(width, height) / 2)
    radius = max(0.0, min(radius, min(width, height) / 2))

    outline = _rounded_mask((width, height), radius, supersample=supersample)
    glass = image.crop((x0, y0, x1, y1)).convert(mode="RGBA")
    glass = glass.filter(ImageFilter.GaussianBlur(style.blur))
    if style.saturation != 1.0:
        glass = ImageEnhance.Color(glass).enhance(style.saturation)

    # A real bubble bends what is *outside* it into its rim, so the rim samples a
    # wider crop squeezed down to size rather than the frost already computed.
    rim_width = max(2.0, min(radius, min(width, height) / 5) * style.refraction)
    if rim_width >= 2:
        rim = ImageChops.subtract(
            outline, _rounded_mask((width, height), radius, rim_width, supersample)
        ).filter(ImageFilter.GaussianBlur(rim_width / 3.5))
        bleed = int(round(rim_width * 1.6))
        lensed = image.crop((max(0, x0 - bleed), max(0, y0 - bleed),
                             min(image.width, x1 + bleed),
                             min(image.height, y1 + bleed))).convert(mode="RGBA")
        lensed = lensed.resize((width, height), Image.Resampling.LANCZOS)
        lensed = lensed.filter(ImageFilter.GaussianBlur(style.blur / 3))
        lensed = ImageEnhance.Brightness(
            ImageEnhance.Color(lensed).enhance(style.saturation)
        ).enhance(1.12)
        glass = Image.composite(lensed, glass, rim)

    tint = style.tint
    if text_color is not None:
        tint = tuple(style.tint[:3]) + (_tint_alpha_for(glass, style, text_color),)
    glass = Image.alpha_composite(glass, Image.new("RGBA", (width, height), tint))
    glass = Image.alpha_composite(glass, _sheen((width, height), style))

    rim_light = Image.new(mode="RGBA", size=(width, height), color=tuple(style.edge[:3]) + (0,))
    rim_light.putalpha(
        ImageChops.subtract(
            outline, _rounded_mask((width, height), radius, 1.25, supersample)
        ).point(lambda v: v * style.edge[3] // 255)
    )
    glass = Image.alpha_composite(glass, rim_light)

    if style.shadow > 0 and image.mode == "RGBA":
        spread = max(3, int(style.blur))
        shadow = Image.new(mode="RGBA", size=image.size, color=(0, 0, 0, 0))
        shadow.paste((0, 0, 0, style.shadow), (x0, y0 + max(1, spread // 3)), outline)
        shadow = shadow.filter(ImageFilter.GaussianBlur(spread / 1.5))
        # A shadow only lands where there is something to catch it, which also
        # keeps it out of the card's own rounded corners.
        shadow.putalpha(ImageChops.multiply(shadow.getchannel("A"), image.getchannel("A")))
        image.alpha_composite(shadow)

    image.paste(glass.convert(image.mode), (x0, y0), outline)


def _block_box(draw: ImageDraw.ImageDraw, xy: Tuple[int, int], text: str,
               font, spacing: int = 4) -> Box:
    """
    Bounding box of one text block: tight horizontally, but using the font's own
    ascent and descent vertically, so bubbles don't change height depending on
    which glyphs a member happens to have in their name.
    """
    if "\n" in text:
        ink = draw.multiline_textbbox(xy, text, font=font, spacing=spacing)
    else:
        ink = draw.textbbox(xy, text, font=font)
    try:
        ascent, descent = font.getmetrics()
        advance = draw.textbbox((0, 0), "A", font=font)[3] + spacing
    except (AttributeError, TypeError):
        return ink
    lines = text.count("\n") + 1
    return (ink[0], min(xy[1], ink[1]),
            ink[2], max(xy[1] + (lines - 1) * advance + ascent + descent, ink[3]))


def _merge_touching(boxes: Iterable[Box], gap: int = 2) -> List[Box]:
    """Union any boxes that overlap, so bubbles never stack up on each other."""
    result = [tuple(box) for box in boxes]
    changed = True
    while changed:
        changed, merged = False, []
        for box in result:
            for i, other in enumerate(merged):
                if (box[0] - gap < other[2] and other[0] - gap < box[2]
                        and box[1] - gap < other[3] and other[1] - gap < box[3]):
                    merged[i] = (min(box[0], other[0]), min(box[1], other[1]),
                                 max(box[2], other[2]), max(box[3], other[3]))
                    changed = True
                    break
            else:
                merged.append(box)
        result = merged
    return result


def glass_boxes_for_text(image: Image.Image, blocks: Sequence[TextBlock],
                         pad: Tuple[int, int] = (16, 10)) -> List[Box]:
    """Where the bubbles for `blocks` go: padded text boxes, merged and clipped."""
    draw = ImageDraw.Draw(image)
    boxes = []
    for xy, text, font in blocks:
        if text is None or not str(text).strip():
            continue
        x0, y0, x1, y1 = _block_box(draw, xy, str(text), font)
        boxes.append((max(0, x0 - pad[0]), max(0, y0 - pad[1]),
                      min(image.width, x1 + pad[0]), min(image.height, y1 + pad[1])))
    return _merge_touching(boxes)


def draw_text_with_glass(image: Image.Image, blocks: Sequence[TextBlock], fill,
                         pad: Tuple[int, int] = (16, 10), radius: Optional[float] = None,
                         style: Optional[GlassStyle] = None, glass: bool = True) -> List[Box]:
    """
    Draw `blocks` -- a sequence of ((x, y), text, font) -- onto `image` in place,
    each sitting on a liquid-glass bubble.  Blocks close enough to touch share a
    single bubble.  Returns the boxes that were painted.

    `style` defaults to smoked or frosted glass depending on `fill`, so the text
    keeps its contrast whatever colour the member picked.
    """
    if style is None:
        style = glass_style_for(fill)
    boxes = glass_boxes_for_text(image, blocks, pad) if glass else []
    for box in boxes:
        draw_glass_panel(image, box, radius=radius, style=style, text_color=fill)
    draw = ImageDraw.Draw(image)
    for xy, text, font in blocks:
        if text is None:
            continue
        draw.text(xy=xy, text=str(text), fill=fill, font=font)
    return boxes
