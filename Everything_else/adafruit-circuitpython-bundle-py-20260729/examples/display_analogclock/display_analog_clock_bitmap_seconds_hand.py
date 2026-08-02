# SPDX-FileCopyrightText: 2026 EeBbHh
# SPDX-License-Identifier: MIT
import math
import time

import adafruit_gc9a01a
import adafruit_imageload
import bitmaptools
import board
import busio
import displayio
import fourwire

from adafruit_display_analogclock import AnalogClock

displayio.release_displays()

spi = busio.SPI(clock=board.SCK, MOSI=board.MOSI)
tft_cs = board.TX
tft_dc = board.RX
display_bus = fourwire.FourWire(spi, command=tft_dc, chip_select=tft_cs, reset=None)
display = adafruit_gc9a01a.GC9A01A(display_bus, width=240, height=240, rotation=0)
clock = AnalogClock(
    "green_hour_hand.bmp",
    "green_minute_hand.bmp",
    (120, 120),
    106,
    number_label_scale=2,
    number_label_color=0x00FF00,
)

# Load the seconds hand BMP
sec_bmp, sec_palette = adafruit_imageload.load("red_second_hand.bmp")

canvas = displayio.Bitmap(240, 240, 2)

canvas_palette = displayio.Palette(2)
canvas_palette[0] = 0xFF00FF  # magenta = transparent
canvas_palette[1] = 0xFF2200  # red-orange
canvas_palette.make_transparent(0)

canvas_tilegrid = displayio.TileGrid(canvas, pixel_shader=canvas_palette)

clock_with_seconds = displayio.Group()
clock_with_seconds.append(clock)
clock_with_seconds.append(canvas_tilegrid)


def draw_seconds_hand(seconds):
    canvas.fill(0)
    angle = math.radians(seconds * 6.0)
    bitmaptools.rotozoom(
        canvas,
        sec_bmp,
        ox=120,  # clock centre x
        oy=120,  # clock centre y
        px=6,  # pivot x: centre of 12px wide BMP
        py=79,  # pivot y: bottom of 60px tall BMP
        angle=angle,
    )


t = time.localtime()
clock.set_time(t.tm_hour, t.tm_min)
draw_seconds_hand(t.tm_sec)
last_hour = t.tm_hour
last_min = t.tm_min
last_sec = t.tm_sec

display.root_group = clock_with_seconds

while True:
    t = time.localtime()
    if t.tm_hour != last_hour or t.tm_min != last_min:
        clock.set_time(t.tm_hour, t.tm_min)
        last_hour = t.tm_hour
        last_min = t.tm_min
    if t.tm_sec != last_sec:
        draw_seconds_hand(t.tm_sec)
        last_sec = t.tm_sec
    time.sleep(0.05)
