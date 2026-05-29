# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Simple demo for the Yoto Mini Player"""

from adafruit_yoto import Yoto

yoto = Yoto(
    default_bg=0x000000,
    rotation=0,
    debug=False,
    auto_refresh=True,
)

title_index = yoto.add_text(
    text="Hello World!",
    text_position=(yoto.display.width // 2, yoto.display.height // 2),
    text_color=0xFFFFFF,
    text_scale=3,
    text_anchor_point=(0.5, 0.5),
    is_data=False,
)

if yoto.peripherals.nfc:
    print(f"NFC: {yoto.peripherals.nfc.device_name}")
if yoto.peripherals.dac:
    print(f"DAC: ES8156 (Chip ID: {yoto.peripherals.dac.chip_id:04X})")
if yoto.peripherals.battery:
    part = yoto.peripherals.battery.part_info
    print(f"Battery: {part['part_number']}")
if yoto.peripherals.rtc:
    print(f"RTC: {'Valid' if yoto.peripherals.rtc_valid else 'Needs Set'}")

while True:
    pass
