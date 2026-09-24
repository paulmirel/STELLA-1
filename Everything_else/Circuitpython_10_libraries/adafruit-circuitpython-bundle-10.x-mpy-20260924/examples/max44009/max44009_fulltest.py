# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
MAX44009 Full Test

Full configuration and reading example for MAX44009
ambient light sensor.

Displays all configuration settings with human-readable names,
then continuously prints sensor readings.
"""

import time

import board

from adafruit_max44009 import MAX44009, IntegrationTime, Mode

print("MAX44009 Full Test")
print("==================")

sensor = MAX44009(board.I2C())
print("MAX44009 Found!")

# === Mode Configuration ===
print("\n--- Mode Configuration ---")

sensor.mode = Mode.CONTINUOUS
mode_names = {
    Mode.DEFAULT: "Default (auto, 800ms cycle)",
    Mode.CONTINUOUS: "Continuous (auto, fast updates)",
    Mode.MANUAL: "Manual (800ms cycle)",
    Mode.MANUAL_CONTINUOUS: "Manual Continuous (fast)",
}
print(f"Mode: {mode_names.get(sensor.mode, 'Unknown')}")

# === Integration Time ===
print("\n--- Integration Time ---")

sensor.integration_time = IntegrationTime.MS_100
it_names = {
    IntegrationTime.MS_800: "800ms (best low-light)",
    IntegrationTime.MS_400: "400ms",
    IntegrationTime.MS_200: "200ms",
    IntegrationTime.MS_100: "100ms (best high-bright)",
    IntegrationTime.MS_50: "50ms (manual mode only)",
    IntegrationTime.MS_25: "25ms (manual mode only)",
    IntegrationTime.MS_12_5: "12.5ms (manual mode only)",
    IntegrationTime.MS_6_25: "6.25ms (manual mode only)",
}
print(f"Integration Time: {it_names.get(sensor.integration_time, 'Unknown')}")

# === Current Division Ratio ===
print("\n--- Current Division Ratio ---")

sensor.current_division_ratio = False
print(f"CDR: {'1/8 (extended range)' if sensor.current_division_ratio else 'Full (normal)'}")

# === Interrupt Configuration ===
print("\n--- Interrupt Configuration ---")

sensor.interrupt_enabled = False
print(f"Interrupt: {'Enabled' if sensor.interrupt_enabled else 'Disabled'}")

sensor.upper_threshold = 1000.0
print(f"Upper Threshold: {sensor.upper_threshold:.2f} lux")

sensor.lower_threshold = 10.0
print(f"Lower Threshold: {sensor.lower_threshold:.2f} lux")

sensor.threshold_timer = 0
print(f"Threshold Timer: {sensor.threshold_timer} (x100ms persist delay)")

# === Start continuous reading ===
print("\n--- Sensor Readings ---\n")

time.sleep(0.2)  # Let sensor stabilize

while True:
    lux = sensor.lux
    if sensor.overrange:
        print("Lux: OVERRANGE")
    else:
        print(f"Lux: {lux:.2f}")

    if sensor.interrupt_status:
        print("  ** Interrupt triggered **")

    time.sleep(1.0)
