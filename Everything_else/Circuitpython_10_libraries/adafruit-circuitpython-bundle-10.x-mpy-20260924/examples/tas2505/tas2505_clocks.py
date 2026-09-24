# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Print the PLL and divider settings the driver solves for each sample rate.
"""

import time

import board
import digitalio

import adafruit_tas2505

RATES = (8000, 11025, 16000, 22050, 32000, 44100, 48000)

# Set this to the MCLK frequency your board supplies, or leave it None to run
# everything from the I2S bit clock.
MCLK = None

reset_pin = digitalio.DigitalInOut(board.TAS_RESET)
reset_pin.direction = digitalio.Direction.OUTPUT
reset_pin.value = False
time.sleep(0.01)
reset_pin.value = True
time.sleep(0.01)

dac = adafruit_tas2505.TAS2505(board.I2C())

for rate in RATES:
    try:
        config = dac.configure_clocks(sample_rate=rate, mclk_freq=MCLK)
    except ValueError as error:
        print(f"{rate:6d} Hz: {error}")
        continue
    pll_out = config["p"], config["r"], config["j"], config["d"]
    print(
        f"{rate:6d} Hz: CODEC_CLKIN {config['codec_clkin'] / 1e6:8.4f} MHz  "
        f"P={pll_out[0]} R={pll_out[1]} J={pll_out[2]} D={pll_out[3]}  "
        f"NDAC={config['ndac']} MDAC={config['mdac']} DOSR={config['dosr']}"
    )

# Leave the chip on a sensible setting
dac.configure_clocks(sample_rate=44100, mclk_freq=MCLK)
reset_pin.deinit()
