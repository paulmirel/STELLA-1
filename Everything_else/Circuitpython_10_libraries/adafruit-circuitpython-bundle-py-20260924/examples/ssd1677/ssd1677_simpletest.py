# SPDX-FileCopyrightText: Copyright (c) 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""Simple demo for the SSD1677 ePaper driver"""

import time

import board
import displayio
import fourwire

import adafruit_ssd1677

displayio.release_displays()

# This pinout works on the Xteink X4 eReader
spi = board.SPI()
epd_cs = board.EPD_CS
epd_dc = board.EPD_DC
epd_reset = board.EPD_RESET
epd_busy = board.EPD_BUSY

display_bus = fourwire.FourWire(
    spi, command=epd_dc, chip_select=epd_cs, reset=epd_reset, baudrate=1000000
)
time.sleep(1)

display = adafruit_ssd1677.SSD1677(
    display_bus,
    width=800,
    height=480,
    busy_pin=epd_busy,
    rotation=0,
)

g = displayio.Group()

pic = displayio.OnDiskBitmap("/display-ruler-720p.bmp")
t = displayio.TileGrid(pic, pixel_shader=pic.pixel_shader)

g.append(t)

display.root_group = g

display.refresh()
print("refreshed")

time.sleep(120)
