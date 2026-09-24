# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time

import board

from adafruit_ina260 import INA260, Mode

i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
ina260 = INA260(i2c)

# trigger a sample
ina260.mode = Mode.TRIGGERED
print(f"Current (one shot #1): {ina260.current:.2f}")
print(f"Voltage (one shot #1): {ina260.voltage:.2f}")
print(f"Power   (one shot #1): {ina260.power:.2f}")

# print it again to show it will return the same value
# until triggered again
print(f"Current (one shot #1 redux): {ina260.current:.2f}")
print(f"Voltage (one shot #1 redux): {ina260.voltage:.2f}")
print(f"Power   (one shot #1 redux): {ina260.power:.2f}")

# trigger a second sample
ina260.mode = Mode.TRIGGERED
print(f"Current (one shot #2): {ina260.current:.2f}")
print(f"Voltage (one shot #2): {ina260.voltage:.2f}")
print(f"Power   (one shot #2): {ina260.power:.2f}")

# put the sensor in power-down mode. It will return
# the previous value until a new mode is chosen
ina260.mode = Mode.SHUTDOWN
print(f"Current (shutdown): {ina260.current:.2f}")
print(f"Voltage (shutdown): {ina260.voltage:.2f}")
print(f"Power   (shutdown): {ina260.power:.2f}")

# return the sensor to the default continuous mode
ina260.mode = Mode.CONTINUOUS
while True:
    print(f"Current (continuous): {ina260.current:.2f}")
    print(f"Voltage (continuous): {ina260.voltage:.2f}")
    print(f"Power   (continuous): {ina260.power:.2f}")
    time.sleep(1)
