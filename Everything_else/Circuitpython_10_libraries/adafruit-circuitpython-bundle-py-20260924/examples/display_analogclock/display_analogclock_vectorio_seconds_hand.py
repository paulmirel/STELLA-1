# SPDX-FileCopyrightText: 2026 EeBbHh
# SPDX-License-Identifier: MIT
import math
import time

import adafruit_gc9a01a
import board
import busio
import displayio
import fourwire
import vectorio

from adafruit_display_analogclock import AnalogClock

displayio.release_displays()

spi = busio.SPI(clock=board.SCK, MOSI=board.MOSI)
tft_cs = board.TX
tft_dc = board.RX
display_bus = fourwire.FourWire(spi, command=tft_dc, chip_select=tft_cs, reset=None)
display = adafruit_gc9a01a.GC9A01A(display_bus, width=240, height=240, rotation=0)

# Load the clock (hour + minute hands)
clock = AnalogClock(
    "green_hour_hand.bmp",
    "green_minute_hand.bmp",
    (120, 120),
    106,
    number_label_scale=2,
    number_label_color=0x00FF00,
)

# Seconds hand
CENTER_X = 120
CENTER_Y = 120
HAND_LENGTH = 85
TAIL_LENGTH = 15

sec_palette = displayio.Palette(1)
sec_palette[0] = 0xFF2200


def hand_polygon(seconds):
    angle_rad = math.radians(seconds * 6.0 - 90.0)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    tx = int(CENTER_X + HAND_LENGTH * cos_a)
    ty = int(CENTER_Y + HAND_LENGTH * sin_a)
    bx = int(CENTER_X - TAIL_LENGTH * cos_a)
    by = int(CENTER_Y - TAIL_LENGTH * sin_a)
    px = int(1.5 * (-sin_a))
    py = int(1.5 * cos_a)
    return [(tx, ty), (CENTER_X + px, CENTER_Y + py), (bx, by), (CENTER_X - px, CENTER_Y - py)]


sec_hand_poly = vectorio.Polygon(pixel_shader=sec_palette, points=hand_polygon(0), x=0, y=0)

clock_with_seconds = displayio.Group()
clock_with_seconds.append(clock)
clock_with_seconds.append(sec_hand_poly)

# Set initial time
t = time.localtime()
clock.set_time(t.tm_hour, t.tm_min)
sec_hand_poly.points = hand_polygon(t.tm_sec)
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
        sec_hand_poly.points = hand_polygon(t.tm_sec)
        last_sec = t.tm_sec
    time.sleep(0.05)
