# SPDX-FileCopyrightText: 2026 Tim Cocks for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
Expanded example demonstrating LVGL-format fonts with multiple bpp values.

This script shows font samples and labels for 8bpp, 4bpp, 2bpp, and 1bpp
fonts. Update the font filenames below to match what is on your CIRCUITPY
drive.
"""

import supervisor
import terminalio
from adafruit_bitmap_font import bitmap_font
from displayio import Bitmap, Group, Palette, TileGrid

from adafruit_display_text.bitmap_label import Label

display = supervisor.runtime.display

FONT_SAMPLES = [
    {
        "label": "8bpp",
        "font_file": "fonts/goudy_bookletter_1911_20px_8bit.bin",
        "bpp": 8,
    },
    {
        "label": "4bpp",
        "font_file": "fonts/goudy_bookletter_1911_20px_4bit.bin",
        "bpp": 4,
    },
    {
        "label": "2bpp",
        "font_file": "fonts/goudy_bookletter_1911_20px_2bit.bin",
        "bpp": 2,
    },
    {
        "label": "1bpp",
        "font_file": "fonts/goudy_bookletter_1911_20px_1bit.bin",
        "bpp": 1,
    },
]

SAMPLE_TEXT = "The quick brown fox 123"


def make_gradient_palette(start_color: int, end_color: int, count: int) -> Palette:
    if count <= 0:
        raise ValueError("count must be > 0")
    palette = Palette(count)

    sr, sg, sb = (start_color >> 16) & 0xFF, (start_color >> 8) & 0xFF, start_color & 0xFF
    er, eg, eb = (end_color >> 16) & 0xFF, (end_color >> 8) & 0xFF, end_color & 0xFF

    for i in range(count):
        if count == 1:
            r, g, b = sr, sg, sb
        else:
            t = i / (count - 1)
            r = int(sr + (er - sr) * t)
            g = int(sg + (eg - sg) * t)
            b = int(sb + (eb - sb) * t)
        palette[i] = (r << 16) | (g << 8) | b

    return palette


def load_font(font_file: str, label: str):
    font = bitmap_font.load_font(font_file)
    print(f"Loaded {label} font from {font_file}")
    return font


main_group = Group()

# white background
bg_group = Group(scale=8)
bg_bmp = Bitmap(display.width // 8, display.height // 8, 1)
bg_palette = Palette(1)
bg_palette[0] = 0xFFFFFF
bg_tg = TileGrid(bg_bmp, pixel_shader=bg_palette)
bg_group.append(bg_tg)
main_group.append(bg_group)

# font samples and labels
x_label = 10
x_sample = 70
y_cursor = 10
line_spacing = 8

for entry in FONT_SAMPLES:
    font = load_font(entry["font_file"], entry["label"])

    label = Label(terminalio.FONT, text=entry["label"], color=0x000000, scale=2)
    label.anchor_point = (0, 0)
    label.anchored_position = (x_label, y_cursor)
    main_group.append(label)

    if entry["bpp"] > 1:
        palette = make_gradient_palette(0xFFFFFF, 0x000000, 2 ** entry["bpp"])
        sample = Label(font, text=SAMPLE_TEXT, color_palette=palette)
    else:
        sample = Label(font, text=SAMPLE_TEXT, background_color=0xFFFFFF, color=0x000000)

    sample.anchor_point = (0, 0)
    sample.anchored_position = (x_sample, y_cursor)
    main_group.append(sample)

    try:
        _, bbox_height, _, _ = font.get_bounding_box()
        line_height = bbox_height
    except AttributeError:
        line_height = 24

    y_cursor += max(line_height, 20) + line_spacing


display.root_group = main_group

while True:
    pass
