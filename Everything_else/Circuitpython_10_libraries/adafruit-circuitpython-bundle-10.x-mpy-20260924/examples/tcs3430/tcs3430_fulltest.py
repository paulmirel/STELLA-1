# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
# SPDX-License-Identifier: MIT

"""Full test for TCS3430 Color and ALS Sensor.
Exercises all configuration options and reads channels in a loop."""

import time

import board

from adafruit_tcs3430 import TCS3430, ALSGain, InterruptPersistence

i2c = board.I2C()
tcs = TCS3430(i2c)

print("TCS3430 Color and ALS Sensor Test")
print("TCS3430 found!")

print(f"Power on: {tcs.power_on}")
print(f"ALS enabled: {tcs.als_enabled}")

tcs.wait_enabled = False
print(f"Wait enabled: {tcs.wait_enabled}")

tcs.integration_cycles = 64
print(f"Integration cycles: {tcs.integration_cycles}")
print(f"Integration time: {tcs.integration_time} ms")

tcs.wait_time = 50.0
print(f"Wait cycles: {tcs.wait_cycles}")
print(f"Wait time: {tcs.wait_time} ms")

tcs.als_threshold_low = 100
tcs.als_threshold_high = 5000
print(f"ALS threshold low: {tcs.als_threshold_low}")
print(f"ALS threshold high: {tcs.als_threshold_high}")

tcs.interrupt_persistence = InterruptPersistence.CYCLES_5
PERS_NAMES = {
    InterruptPersistence.EVERY: "Every ALS cycle",
    InterruptPersistence.CYCLES_1: "1 consecutive",
    InterruptPersistence.CYCLES_2: "2 consecutive",
    InterruptPersistence.CYCLES_3: "3 consecutive",
    InterruptPersistence.CYCLES_5: "5 consecutive",
    InterruptPersistence.CYCLES_10: "10 consecutive",
    InterruptPersistence.CYCLES_15: "15 consecutive",
    InterruptPersistence.CYCLES_20: "20 consecutive",
    InterruptPersistence.CYCLES_25: "25 consecutive",
    InterruptPersistence.CYCLES_30: "30 consecutive",
    InterruptPersistence.CYCLES_35: "35 consecutive",
    InterruptPersistence.CYCLES_40: "40 consecutive",
    InterruptPersistence.CYCLES_45: "45 consecutive",
    InterruptPersistence.CYCLES_50: "50 consecutive",
    InterruptPersistence.CYCLES_55: "55 consecutive",
    InterruptPersistence.CYCLES_60: "60 consecutive",
}
print(f"Interrupt persistence: {PERS_NAMES.get(tcs.interrupt_persistence, 'Unknown')}")

tcs.wait_long = True
print(f"Wait long: {'enabled (12x multiplier)' if tcs.wait_long else 'disabled'}")

tcs.als_mux_ir2 = False
print(f"ALS MUX: {'IR2 channel' if tcs.als_mux_ir2 else 'X channel'}")

tcs.als_gain = ALSGain.GAIN_16X
GAIN_NAMES = {
    ALSGain.GAIN_1X: "1x",
    ALSGain.GAIN_4X: "4x",
    ALSGain.GAIN_16X: "16x",
    ALSGain.GAIN_64X: "64x",
    ALSGain.GAIN_128X: "128x",
}
print(f"ALS gain: {GAIN_NAMES.get(tcs.als_gain, 'Unknown')}")

tcs.interrupt_clear_on_read = False
print(f"Interrupt clear on read: {'enabled' if tcs.interrupt_clear_on_read else 'disabled'}")

tcs.sleep_after_interrupt = False
print(f"Sleep after interrupt: {'enabled' if tcs.sleep_after_interrupt else 'disabled'}")

tcs.auto_zero_mode = False
print(f"Auto-zero mode: {'enabled' if tcs.auto_zero_mode else 'disabled'}")

tcs.auto_zero_nth = 7
print(f"Run auto-zero every N: {tcs.auto_zero_nth}")

tcs.als_interrupt_enabled = True
tcs.saturation_interrupt_enabled = True
print("ALS and saturation interrupts enabled")

while True:
    if tcs.als_saturated:
        print("ALS saturated - clearing")
        tcs.clear_als_saturated()

    if tcs.als_interrupt:
        print("ALS interrupt - clearing")
        tcs.clear_als_interrupt()

    x, y, z, ir1 = tcs.channels
    print(f"X: {x}, Y: {y}, Z: {z}, IR1: {ir1}")

    time.sleep(1.0)
