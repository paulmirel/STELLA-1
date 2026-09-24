# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
# SPDX-License-Identifier: MIT

"""Interrupt example for TCS3430 XYZ Tristimulus Color Sensor.
Sets a high threshold -- shine a flashlight on the sensor to trigger!

Connect INT to board.D8. The Adafruit breakout has an open-drain inverter
on INT, so active-HIGH at MCU. Configure as input with pull-up."""

import time

import board
import digitalio

from adafruit_tcs3430 import TCS3430, ALSGain, InterruptPersistence

INT_PIN = board.D8

i2c = board.I2C()
tcs = TCS3430(i2c)

print("TCS3430 Interrupt Test")
print(f"Connect sensor INT to {INT_PIN}")
print()
print("TCS3430 found!")

int_pin = digitalio.DigitalInOut(INT_PIN)
int_pin.direction = digitalio.Direction.INPUT
int_pin.pull = digitalio.Pull.UP

# Setup sensor
tcs.als_gain = ALSGain.GAIN_16X
tcs.integration_time = 100.0
tcs.interrupt_persistence = InterruptPersistence.CYCLES_3  # require 3 consecutive

# Read current ambient to set threshold above it
time.sleep(0.2)
x, y, z, ir1 = tcs.channels

# Thresholds compare against CH0 (Z channel)
threshold = z * 2  # 2x above current ambient
threshold = max(threshold, z + 200)
threshold = min(threshold, 65000)

print(f"Current ambient Z: {z}")
print(f"Interrupt threshold (high): {threshold}")
print()
print("Shine a flashlight on the sensor to trigger!")
print("INT pin idle = LOW, active = HIGH (breakout inverter)")
print()

# Window: low=0, high=threshold
# Interrupt fires when Z exceeds threshold (outside window)
tcs.als_threshold_low = 0
tcs.als_threshold_high = threshold
tcs.interrupt_clear_on_read = False

# Clean start
tcs.als_interrupt_enabled = True
tcs.als_enabled = False
tcs.clear_als_interrupt()
tcs.als_enabled = True

print(f"INT pin: {'HIGH' if int_pin.value else 'LOW'}")

last_print = time.monotonic()

while True:
    # Check INT pin state
    if int_pin.value:
        # Read channels to see what triggered it
        x, y, z, ir1 = tcs.channels
        print(f"*** INTERRUPT! *** Z={z}  Y={y}  X={x}  IR1={ir1}")

        # Clear and wait for pin to go idle before checking again
        tcs.als_enabled = False
        tcs.clear_als_interrupt()
        tcs.als_enabled = True

        # Wait for INT to settle back to idle
        time.sleep(0.5)
        continue

    # Periodic ambient reading every 2 seconds
    now = time.monotonic()
    if now - last_print > 2.0:
        last_print = now
        x, y, z, ir1 = tcs.channels
        print(f"Z={z}  Y={y}  (waiting...)  INT={'HIGH' if int_pin.value else 'LOW'}")
