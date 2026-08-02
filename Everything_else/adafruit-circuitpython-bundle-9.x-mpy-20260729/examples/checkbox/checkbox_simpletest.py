# SPDX-FileCopyrightText: Copyright (c) 2025 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Basic checkbox example that uses a USB Host mouse to allow clicking on the CheckBox
"""

import time

import supervisor
import terminalio
from adafruit_display_text.bitmap_label import Label
from adafruit_usb_host_mouse import find_and_init_boot_mouse
from displayio import Group

from adafruit_checkbox import CheckBox

display = supervisor.runtime.display

# group to hold visual elements
main_group = Group()

# make the group visible on the display
display.root_group = main_group

# set up USB host mouse
mouse = find_and_init_boot_mouse()
if mouse is None:
    raise RuntimeError("No mouse found connected to USB Host")

# timestamp of last increment
last_count_time = 0
# counter variable
i = 0

# initialize and show a CheckBox
keep_counting_checkbox = CheckBox(terminalio.FONT, text="Keep Counting", checked=True)
keep_counting_checkbox.anchor_point = (0, 0)
keep_counting_checkbox.anchored_position = (2, 2)
main_group.append(keep_counting_checkbox)

# label to hold the current count
count_label = Label(terminalio.FONT, text=str(i), color=0xFFFFFF)
count_label.anchor_point = (0, 0)
count_label.anchored_position = (2, 20)
main_group.append(count_label)

# add the mouse cursor to the main group
main_group.append(mouse.tilegrid)
while True:
    # update mouse
    pressed_btns = mouse.update()

    # if the checkbox was left clicked
    if pressed_btns is not None and "left" in pressed_btns:
        if keep_counting_checkbox.contains((mouse.x, mouse.y)):
            # toggle the checked state
            keep_counting_checkbox.checked = not keep_counting_checkbox.checked

    if keep_counting_checkbox.checked:
        # increment the counter ever 0.5 seconds and update the label
        if time.monotonic() > last_count_time + 0.5:
            last_count_time = time.monotonic()
            i += 1
            count_label.text = str(i)
