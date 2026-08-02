# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Buttons and manual display refresh demo"""

from adafruit_yoto import Yoto

yoto = Yoto(
    default_bg="/sd/blinka240x240.bmp",
    rotation=0,
    debug=False,
    auto_refresh=False,
)
yoto.graphics.refresh()

btn1_state = False
btn2_state = False

while True:
    btn1 = yoto.peripherals.encoder_left_button
    btn2 = yoto.peripherals.encoder_right_button
    if not btn1 and not btn1_state:
        print("button 1 pressed!")
        yoto.set_background("/sd/blinka240x240.bmp")
        yoto.graphics.refresh()
        btn1_state = True
    if btn1 and btn1_state:
        btn1_state = False

    if not btn2 and not btn2_state:
        print("button 2 pressed!")
        yoto.set_background("/sd/blinka_round.bmp")
        yoto.graphics.refresh()
        btn2_state = True
    if btn2 and btn2_state:
        btn2_state = False
