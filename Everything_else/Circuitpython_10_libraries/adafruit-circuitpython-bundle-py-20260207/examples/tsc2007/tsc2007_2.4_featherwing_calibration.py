# SPDX-FileCopyrightText: 2022 Cedar Grove Maker Studios
# SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
tsc2007_2.4_featherwing_calibration.py

Author(s): JG for Cedar Grove Maker Studios, Tim Cocks

On-screen touchscreen calibrator for 2.4" TFT Featherwing

When the test screen appears, use a stylus to swipe to the four edges
of the visible display area. As the screen is calibrated, the small red
square tracks the stylus tip (REPL_ONLY=False). Minimum and maximum
calibration values will display on the screen and in the REPL. The calibration
tuple can be copied and pasted into the calling code's touchscreen
instantiation statement.

DISPLAY_ROTATION: Display rotation value in degrees. Only values of
None, 0, 90, 180, and 270 degrees are accepted. Defaults to None, the
previous orientation of the display.

REPL_ONLY: If False, calibration values are shown graphically on the screen
and printed to the REPL. If True, the values are only printed to the REPL.
Default value is False.
"""

import time

import adafruit_ili9341
import board
import displayio
import fourwire
import terminalio
import vectorio
from adafruit_display_text.label import Label
from adafruit_simplemath import map_range

import adafruit_tsc2007

# Operational parameters:
DISPLAY_ROTATION = 0  # Specify 0, 90, 180, or 270 degrees
TOUCH_SWAP_XY = True
TOUCH_INVERT_X = True
TOUCH_INVERT_Y = False
REPL_ONLY = False  # True to disable graphics


class Colors:
    """A collection of colors used for graphic objects."""

    BLUE_DK = 0x000060  # Screen fill
    RED = 0xFF0000  # Boundary
    WHITE = 0xFFFFFF  # Text


displayio.release_displays()

# Use Hardware SPI
spi = board.SPI()

tft_cs = board.D9
tft_dc = board.D10

display_width = 320
display_height = 240

display_bus = fourwire.FourWire(spi, command=tft_dc, chip_select=tft_cs)
display = adafruit_ili9341.ILI9341(display_bus, width=display_width, height=display_height)
i2c = board.STEMMA_I2C()
irq_dio = None
tsc = adafruit_tsc2007.TSC2007(
    i2c, irq=irq_dio, swap_xy=TOUCH_SWAP_XY, invert_x=TOUCH_INVERT_X, invert_y=TOUCH_INVERT_Y
)

# Check rotation value and update display.
# Always set rotation before instantiating the touchscreen.
if DISPLAY_ROTATION is not None and DISPLAY_ROTATION in {0, 90, 180, 270}:
    display.rotation = DISPLAY_ROTATION
else:
    print("Warning: invalid rotation value -- defaulting to zero")
    display.rotation = 0
    time.sleep(1)

# Activate the display graphics unless REPL_ONLY=True
if not REPL_ONLY:
    display_group = displayio.Group()
    display.root_group = display_group

# Define the graphic objects if REPL_ONLY = False
if not REPL_ONLY:
    # Define the text graphic objects
    font_0 = terminalio.FONT

    coordinates = Label(
        font=font_0,
        text="calib: ((x_min, x_max), (y_min, y_max))",
        color=Colors.WHITE,
    )
    coordinates.anchor_point = (0.5, 0.5)
    coordinates.anchored_position = (
        display.width // 2,
        display.height // 4,
    )

    display_rotation = Label(
        font=font_0,
        text="rotation: " + str(display.rotation),
        color=Colors.WHITE,
    )
    display_rotation.anchor_point = (0.5, 0.5)
    display_rotation.anchored_position = (
        display.width // 2,
        display.height // 4 - 30,
    )

    # Define graphic objects for the screen fill, boundary, and touch pen
    target_palette = displayio.Palette(1)
    target_palette[0] = Colors.BLUE_DK
    screen_fill = vectorio.Rectangle(
        pixel_shader=target_palette,
        x=2,
        y=2,
        width=display.width - 4,
        height=display.height - 4,
    )

    target_palette = displayio.Palette(1)
    target_palette[0] = Colors.RED
    boundary = vectorio.Rectangle(
        pixel_shader=target_palette,
        x=0,
        y=0,
        width=display.width,
        height=display.height,
    )

    pen = vectorio.Rectangle(
        pixel_shader=target_palette,
        x=display.width // 2,
        y=display.height // 2,
        width=10,
        height=10,
    )

    display_group.append(boundary)
    display_group.append(screen_fill)
    display_group.append(pen)
    display_group.append(coordinates)
    display_group.append(display_rotation)

# Reset x and y values to raw touchscreen mid-point before measurement
x_min = x_max = y_min = y_max = 4095 // 2

print("Touchscreen Calibrator")
print("  Use a stylus to swipe slightly beyond the")
print("  four edges of the visible display area.")
print(" ")
print(f"  display rotation: {display.rotation} degrees")
print("  Calibration values follow:")
print(" ")

while True:
    time.sleep(0.100)

    if tsc.touched:
        touch = tsc.touch
        # Remember minimum and maximum values for the calibration tuple
        x_min = min(x_min, touch["x"])
        x_max = max(x_max, touch["x"])
        y_min = min(y_min, touch["y"])
        y_max = max(y_max, touch["y"])

        # Show the calibration tuple.
        print(f"(({x_min}, {x_max}), ({y_min}, {y_max}))")
        if not REPL_ONLY:
            pen.x = int(map_range(touch["x"], x_min, x_max, 0, display.width)) - 5
            pen.y = int(map_range(touch["y"], y_min, y_max, 0, display.height)) - 5
            coordinates.text = f"calib: (({x_min}, {x_max}), ({y_min}, {y_max}))"
