# SPDX-FileCopyrightText: 2020 Bryan Siepert, written for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
import board

from adafruit_tmp117 import TMP117, AverageCount

# First try the STEMMA_I2C on Feathers and QtPy among others
if hasattr(board, "STEMMA_I2C"):
    i2c = board.STEMMA_I2C()
else:
    i2c = board.I2C()  # uses board.SCL and board.SDA

tmp117 = TMP117(i2c)

# uncomment different options below to see how it affects the reported temperature
# and measurement time

# tmp117.averaged_measurements = AverageCount.AVERAGE_1X
# tmp117.averaged_measurements = AverageCount.AVERAGE_8X # Default
# tmp117.averaged_measurements = AverageCount.AVERAGE_32X
# tmp117.averaged_measurements = AverageCount.AVERAGE_64X

print(
    "Number of averaged samples per measurement:",
    AverageCount.string[tmp117.averaged_measurements],
)
print(
    "Reads should take approximately",
    AverageCount.string[tmp117.averaged_measurements] * 0.0155,
    "seconds",
)

while True:
    print(f"Single measurement: {tmp117.take_single_measurement():.2f} degrees C")
    # time.sleep(1)
