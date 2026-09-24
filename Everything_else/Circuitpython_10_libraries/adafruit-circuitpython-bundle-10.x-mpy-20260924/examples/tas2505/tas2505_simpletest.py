# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Play a sine wave out of the Class-D speaker amplifier.

Pin names are the Teenage Engineering SP-1's, the only board this driver has
been run on.
"""

import array
import math
import time

import audiobusio
import audiocore
import board
import digitalio

import adafruit_tas2505

RATE = 44100

DAC_VOLUME = 0  # digital, 0 to -63.5
SPEAKER_VOLUME = 0  # analog, 0 to -72.3
SPEAKER_GAIN = 6  # Class-D amplifier, 6 to 24

reset_pin = digitalio.DigitalInOut(board.TAS_RESET)
reset_pin.direction = digitalio.Direction.OUTPUT
reset_pin.value = False
time.sleep(0.01)
reset_pin.value = True
time.sleep(0.01)

dac = adafruit_tas2505.TAS2505(board.I2C())
dac.configure_clocks(sample_rate=RATE)

dac.speaker_output = True
dac.dac_volume = DAC_VOLUME
dac.speaker_volume = SPEAKER_VOLUME
dac.speaker_gain = SPEAKER_GAIN

audio = audiobusio.I2SOut(board.I2S_BIT_CLOCK, board.I2S_WORD_SELECT, board.I2S_DOUT)

# One cycle of a 440 Hz sine, played on a loop
length = RATE // 440
sine_wave = array.array("h", [0] * length)
for i in range(length):
    sine_wave[i] = int(math.sin(math.pi * 2 * i / length) * 0.5 * (2**15 - 1))
sine_wave_sample = audiocore.RawSample(sine_wave, sample_rate=RATE)

try:
    while True:
        audio.play(sine_wave_sample, loop=True)
        time.sleep(1)
        audio.stop()
        time.sleep(1)
finally:
    dac.speaker_output = False
    audio.stop()
    audio.deinit()
    reset_pin.deinit()
