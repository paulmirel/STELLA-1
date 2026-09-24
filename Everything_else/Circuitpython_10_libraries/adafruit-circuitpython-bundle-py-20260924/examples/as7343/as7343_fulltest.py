# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Full test example for AS7343 14-Channel Multi-Spectral Sensor.

Displays chip information, configuration, and continuous spectral readings.

Written by Tim Cocks with assistance from Claude Code for Adafruit Industries.
"""

import time

import board

from adafruit_as7343 import AS7343, Channel, Gain, SmuxMode

#  Initialise sensor
i2c = board.I2C()

print("AS7343 Full Test")
print("================")

try:
    sensor = AS7343(i2c)
except RuntimeError as e:
    print(f"Couldn't find AS7343 chip: {e}")
    raise SystemExit

print("AS7343 found!")

#  Chip information
print("\n--- Chip Information ---")
print(f"Part ID:     0x{sensor.part_id:02X}")
print(f"Revision ID: 0x{sensor.revision_id:02X}")
print(f"Aux ID:      0x{sensor.aux_id:02X}")

#  Spectral engine configuration
print("\n--- Spectral Configuration ---")

sensor.gain = Gain.X64
gain_names = {
    Gain.X0_5: "0.5x",
    Gain.X1: "1x",
    Gain.X2: "2x",
    Gain.X4: "4x",
    Gain.X8: "8x",
    Gain.X16: "16x",
    Gain.X32: "32x",
    Gain.X64: "64x",
    Gain.X128: "128x",
    Gain.X256: "256x",
    Gain.X512: "512x",
    Gain.X1024: "1024x",
    Gain.X2048: "2048x",
}
print(f"Gain: {gain_names.get(sensor.gain, 'Unknown')}")

sensor.atime = 29
print(f"ATIME: {sensor.atime}")

sensor.astep = 599
print(f"ASTEP: {sensor.astep}")

print(f"Integration Time: {sensor.integration_time_ms:.2f} ms")

#  SMUX configuration
print("\n--- SMUX Configuration ---")

sensor.smux_mode = SmuxMode.CH18
smux_names = {
    SmuxMode.CH6: "6 channels",
    SmuxMode.CH12: "12 channels (2 cycles)",
    SmuxMode.CH18: "18 channels (3 cycles)",
}
print(f"Mode: {smux_names.get(sensor.smux_mode, 'Unknown')}")

#  Wait time configuration
print("\n--- Wait Time Configuration ---")

sensor.wtime = 100
print(f"Wait Time: {sensor.wtime} (disabled by default)")

#  Interrupt configuration
print("\n--- Interrupt Configuration ---")

sensor.persistence = 4
print(f"Persistence: {sensor.persistence}")

# NOTE: Threshold channel register r/w works but has no observed effect
# on threshold comparison - comparison is always on CH0 regardless.
sensor.threshold_channel = 0
print(f"Threshold Channel: {sensor.threshold_channel}")

sensor.spectral_threshold_low = 100
print(f"Low Threshold: {sensor.spectral_threshold_low}")

sensor.spectral_threshold_high = 60000
print(f"High Threshold: {sensor.spectral_threshold_high}")

#  LED driver configuration
print("\n--- LED Driver Configuration ---")

sensor.led_current_ma = 20
print(f"LED Current: {sensor.led_current_ma} mA")
print("LED: Off (use sensor.led_enabled = True to turn on)")

#  Continuous spectral readings
print("\n--- Spectral Readings ---")
print("Channel wavelengths: F1=405nm, F2=425nm, FZ=450nm, F3=475nm, F4=515nm, F5=550nm,")
print("FY=555nm, FXL=600nm, F6=640nm, F7=690nm, F8=745nm, NIR=855nm\n")

time.sleep(0.2)  # Let sensor stabilise

while True:
    try:
        readings = sensor.all_channels
    except TimeoutError:
        print("Read failed!")
        time.sleep(0.5)
        continue

    # Print in wavelength order for easier reading
    print(
        f"F1:{readings[Channel.F1]}"
        f"\tF2:{readings[Channel.F2]}"
        f"\tFZ:{readings[Channel.FZ]}"
        f"\tF3:{readings[Channel.F3]}"
        f"\tF4:{readings[Channel.F4]}"
        f"\tF5:{readings[Channel.F5]}"
        f"\tFY:{readings[Channel.FY]}"
        f"\tFXL:{readings[Channel.FXL]}"
        f"\tF6:{readings[Channel.F6]}"
        f"\tF7:{readings[Channel.F7]}"
        f"\tF8:{readings[Channel.F8]}"
        f"\tNIR:{readings[Channel.NIR]}"
    )

    time.sleep(1.0)
