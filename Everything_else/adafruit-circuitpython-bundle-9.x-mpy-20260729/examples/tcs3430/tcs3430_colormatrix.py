# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
# SPDX-License-Identifier: MIT

"""Color matrix example for TCS3430 XYZ Tristimulus Color Sensor.

Applies a 3x4 color matrix to raw channels and computes CIE x,y, lux, and CCT.

IMPORTANT:
- The color matrix (CM) depends on the optical stack (diffuser, cover glass, housing, etc.).
- These example matrices are from ams AN000571 and may not match your hardware.
- For accurate results, derive your own CM per the app note procedure (https://cdn-learn.adafruit.com/assets/assets/000/143/027/original/TCS3430_colormatrix_calibration.pdf?1773691943).
- Low IR matrix is intended for LED/CFL sources; High IR is for incandescent/halogen.

Low IR matrix (used below):
X' = -0.28837*X + 0.58484*Y + 1.55207*Z + -1.21521*IR
Y' = -0.30518*X + 0.60817*Y + 1.62203*Z + -1.25651*IR
Z' = -0.23132*X + 0.46517*Y + 1.22896*Z + -0.95905*IR

High IR matrix (comment only):
X' =  0.582690*X + -0.183675*Y + -1.583206*Z + 0.082557*IR
Y' =  0.529610*X + -0.178553*Y + -1.416517*Z + 0.076360*IR
Z' =  0.188025*X + -0.057204*Y + -0.506941*Z + 0.025853*IR
"""

import time

import board

from adafruit_tcs3430 import TCS3430, ALSGain

i2c = board.I2C()
tcs = TCS3430(i2c)

print("TCS3430 Color Matrix Example")
print("TCS3430 found!")

COLOR_MATRIX = (
    (-0.28837, 0.58484, 1.55207, -1.21521),
    (-0.30518, 0.60817, 1.62203, -1.25651),
    (-0.23132, 0.46517, 1.22896, -0.95905),
)

GAIN_VALUES = {
    ALSGain.GAIN_1X: 1.0,
    ALSGain.GAIN_4X: 4.0,
    ALSGain.GAIN_16X: 16.0,
    ALSGain.GAIN_64X: 66.0,
    ALSGain.GAIN_128X: 137.0,
}

# --- Tweak these settings for your environment ---
tcs.als_gain = ALSGain.GAIN_64X  # 1X, 4X, 16X, 64X, or 128X
tcs.integration_time = 100.0  # 2.78ms to 711ms

while True:
    x, y, z, ir1 = tcs.channels

    cm = COLOR_MATRIX
    cie_X = cm[0][0] * x + cm[0][1] * y + cm[0][2] * z + cm[0][3] * ir1
    cie_Y = cm[1][0] * x + cm[1][1] * y + cm[1][2] * z + cm[1][3] * ir1
    cie_Z = cm[2][0] * x + cm[2][1] * y + cm[2][2] * z + cm[2][3] * ir1

    total = cie_X + cie_Y + cie_Z
    cie_x = cie_X / total if total > 0 else 0.0
    cie_y = cie_Y / total if total > 0 else 0.0

    cct = 0.0
    if total > 0 and (0.1858 - cie_y) != 0.0:
        n = (cie_x - 0.3320) / (0.1858 - cie_y)
        cct = (449.0 * n * n * n) + (3525.0 * n * n) + (6823.3 * n) + 5520.33

    gain = GAIN_VALUES.get(tcs.als_gain, 1.0)
    integration_ms = tcs.integration_time
    lux = cie_Y * (16.0 / gain) * (100.0 / integration_ms) if integration_ms > 0 else 0.0

    print(f"X: {x}  Y: {y}  Z: {z}  IR1: {ir1}")
    print(f"  CIE x: {cie_x:.4f}  y: {cie_y:.4f}  Lux: {lux:.1f}  CCT: {cct:.0f} K")

    time.sleep(1.0)
