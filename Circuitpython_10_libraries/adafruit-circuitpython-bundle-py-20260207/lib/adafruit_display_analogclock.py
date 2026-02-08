# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2025 Tim C for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_display_analogclock`
================================================================================

Draw a traditional 12-hour analog clock face with
hour and minute hands. Allows you to provide graphics
to customize the clock.


* Author(s): Tim C

Implementation Notes
--------------------

**Hardware:**

Any CircuitPython device with displayio support

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

"""

# imports
import math

import adafruit_imageload
import bitmaptools
import terminalio
from adafruit_anchored_tilegrid import AnchoredTileGrid
from adafruit_display_text.bitmap_label import Label
from displayio import Bitmap, Group, OnDiskBitmap, Palette, TileGrid

__version__ = "1.0.1"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_Display_AnalogClock.git"


class AnalogClock(Group):
    def __init__(  # noqa: PLR0913, PLR0917, Too many args, Too many positional args
        self,
        hour_hand_file,
        minute_hand_file,
        center_xy,
        number_label_radius,
        number_label_scale=1,
        number_label_color=0x000000,
        hand_transparency_index=0,
        background_color=None,
        background_size=None,
        background_img_file=None,
        background_img_anchor_point=None,
        background_img_anchored_position=None,
        scale=1,
        x=0,
        y=0,
    ):
        super().__init__(scale=scale, x=x, y=y)
        self.center_xy = center_xy

        if background_size is None:
            self.background_size = center_xy[0] * 2
        else:
            self.background_size = background_size

        self.minute_hand_bmp, self.minute_hand_palette = adafruit_imageload.load(minute_hand_file)
        self.hour_hand_bmp, self.hour_hand_palette = adafruit_imageload.load(hour_hand_file)
        self.hand_transparency_index = hand_transparency_index
        self.rotating_hands_canvas_bmp = Bitmap(
            self.background_size, self.background_size, len(self.minute_hand_palette) + 1
        )
        self.rotating_hands_canvas_palette = Palette(len(self.minute_hand_palette) + 1)

        if background_color is not None:
            self.bg_group = Group(scale=1)
            self.bg_bmp = Bitmap(self.background_size, self.background_size, 1)
            self.bg_palette = Palette(1)
            self.bg_palette[0] = background_color
            self.bg_tilegrid = TileGrid(bitmap=self.bg_bmp, pixel_shader=self.bg_palette)
            self.bg_group.append(self.bg_tilegrid)
            self.append(self.bg_group)

        for i in range(len(self.minute_hand_palette)):
            self.rotating_hands_canvas_palette[i] = self.minute_hand_palette[i]
        self.rotating_hands_canvas_palette.make_transparent(self.hand_transparency_index)
        self.rotating_hands_canvas_bmp.fill(self.hand_transparency_index)

        self.rotating_hands_canvas_tilegrid = TileGrid(
            self.rotating_hands_canvas_bmp, pixel_shader=self.rotating_hands_canvas_palette
        )

        if background_img_file is not None:
            self.background_img_bmp = OnDiskBitmap(background_img_file)
            self.background_img_tilegrid = AnchoredTileGrid(
                bitmap=self.background_img_bmp, pixel_shader=self.background_img_bmp.pixel_shader
            )

            self.background_img_tilegrid.anchor_point = (
                background_img_anchor_point
                if background_img_anchor_point is not None
                else (0.5, 0.5)
            )

            self.background_img_tilegrid.anchored_position = (
                background_img_anchored_position
                if background_img_anchored_position is not None
                else center_xy
            )

            self.append(self.background_img_tilegrid)
            # print("added background img tilegrid")

        self.append(self.rotating_hands_canvas_tilegrid)
        # print("appended canvas tilegrid")
        _clock_label_points = AnalogClock.points_around_circle(
            center_xy[0] + 2, center_xy[1], number_label_radius, 12
        )
        for i, point in enumerate(_clock_label_points):
            # +2 because the points start at the right of the circle in the 3-oclock position
            # +1 because we want to move from 0 based loop var to 1 based clock labels
            hour_lbl = Label(
                terminalio.FONT,
                text=str(((i + 2) % 12) + 1),
                anchor_point=(0.5, 0.5),
                anchored_position=(point[0], point[1]),
                color=number_label_color,
                scale=number_label_scale,
            )
            self.append(hour_lbl)
        # print(f"appended clock labels at: {_clock_label_points}")

    def set_time(self, hour, minute):
        """
        Set the hour and minute hands to the appropriate angles
        based on the given time.

        :param hour: The hour to set 0-23
        :param minute: The minute to set 0-59
        :return: None
        """
        minute_hand_angle = minute * 6
        hour_hand_angle = hour * 30 + (30 * minute / 60)
        print(f"minute angle: {minute_hand_angle}")
        print(f"hour angle: {hour_hand_angle}")
        self.rotating_hands_canvas_bmp.fill(self.hand_transparency_index)
        bitmaptools.rotozoom(
            self.rotating_hands_canvas_bmp,
            self.minute_hand_bmp,
            ox=self.center_xy[0],
            oy=self.center_xy[1],
            px=self.minute_hand_bmp.width // 2,
            py=self.minute_hand_bmp.height,
            angle=minute_hand_angle * math.pi / 180,
            skip_index=self.hand_transparency_index,
        )

        bitmaptools.rotozoom(
            self.rotating_hands_canvas_bmp,
            self.hour_hand_bmp,
            ox=self.center_xy[0],
            oy=self.center_xy[1],
            px=self.hour_hand_bmp.width // 2,
            py=self.hour_hand_bmp.height,
            angle=hour_hand_angle * math.pi / 180,
            skip_index=self.hand_transparency_index,
        )

    @staticmethod
    def points_around_circle(circle_x, circle_y, r, point_count):
        """
        Return a list containing x,y points around a circle with
        the given parameters.

        :param circle_x: Center x coordinate
        :param circle_y: Center y coordinate
        :param r: Radius of the circle
        :param point_count: How many points
        :return List: A list containing (x,y) points around the circle
        """
        points = []
        for i in range(point_count):
            x = circle_x + r * math.cos(2 * math.pi * i / point_count)
            y = circle_y + r * math.sin(2 * math.pi * i / point_count)
            points.append((x, y))
        return points
