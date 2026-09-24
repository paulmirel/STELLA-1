# SPDX-FileCopyrightText: Copyright (c) 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Adafruit TCS3448 spectral display for the ESP32-S2/S3 TFT Feather.
Displays a real-time spectral bar chart on the built-in TFT.
Each bar is colored to match the channel's wavelength."""

import time

import board
import digitalio
import displayio
import simpleio
import terminalio
import vectorio
from adafruit_display_text import bitmap_label

from adafruit_tcs3448 import TCS3448, Channel

display = board.DISPLAY
group = displayio.Group()
text_group = displayio.Group()
bar_group = displayio.Group()

i2c = board.STEMMA_I2C()
sensor = TCS3448(i2c)

palette0 = displayio.Palette(12)
palette0[0] = 0x7B007B
palette0[1] = 0x4200FF
palette0[2] = 0x0000FF
palette0[3] = 0x005DFF
palette0[4] = 0x00FF00
palette0[5] = 0xADFF00
palette0[6] = 0xFFFF00
palette0[7] = 0xFF8200
palette0[8] = 0xFF0000
palette0[9] = 0xC60000
palette0[10] = 0x840000
palette0[11] = 0x420000

color_dictionary = [
    {"channel": Channel.F1, "label": "F1", "color": 0},
    {"channel": Channel.F2, "label": "F2", "color": 1},
    {"channel": Channel.FZ, "label": "FZ", "color": 2},
    {"channel": Channel.F3, "label": "F3", "color": 3},
    {"channel": Channel.F4, "label": "F4", "color": 4},
    {"channel": Channel.F5, "label": "F5", "color": 5},
    {"channel": Channel.FY, "label": "FY", "color": 6},
    {"channel": Channel.FXL, "label": "FXL", "color": 7},
    {"channel": Channel.F6, "label": "F6", "color": 8},
    {"channel": Channel.F7, "label": "F7", "color": 9},
    {"channel": Channel.F8, "label": "F8", "color": 10},
    {"channel": Channel.NIR, "label": "NIR", "color": 11},
]

BAR_TOP = 18
BAR_BOTTOM = 118
BAR_LEFT = 4
BAR_WIDTH = 17
BAR_GAP = 3
MAX_READING = 1
CHART_HEIGHT = BAR_BOTTOM - BAR_TOP
for entry in color_dictionary:
    print(sensor.all_channels[entry["channel"]])
    x = BAR_LEFT + color_dictionary.index(entry) * (BAR_WIDTH + BAR_GAP)
    text = bitmap_label.Label(
        terminalio.FONT, text=entry["label"], x=x, y=BAR_BOTTOM, color=0xFFFFFF
    )
    text_group.append(text)
    rect = vectorio.Rectangle(
        pixel_shader=palette0,
        width=BAR_WIDTH,
        height=10,
        x=x,
        y=BAR_BOTTOM - 20,
        color_index=entry["color"],
    )
    bar_group.append(rect)

group.append(text_group)
group.append(bar_group)
display.root_group = group

while True:
    for entry in color_dictionary:
        index = color_dictionary.index(entry)
        reading = sensor.all_channels[entry["channel"]]
        mapped_height = simpleio.map_range(reading, 0, 1000, 0, CHART_HEIGHT)
        bar_group[index].y = BAR_BOTTOM - 10 - int(mapped_height)
        bar_group[index].height = int(mapped_height)
        time.sleep(0.001)
