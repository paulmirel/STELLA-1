# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Play a one-octave scale out the headphone jack with synthio, output only.

There is no microphone capture here, so the codec only needs its DAC side
brought up. The one ordering rule that still applies is the clock one: the FLL
locks to the incoming bit clock, so BCLK has to be running before
``configure_clocks`` is called. Playing the synth is what starts BCLK, so it
goes first; the codec is silent until ``headphone_output`` is enabled a few
lines later, which is why starting playback before configuring is harmless.

Pin names are the Teenage Engineering EP-2350's; adjust for other boards.
"""

import time

import audiobusio
import board
import synthio

import adafruit_nau88l21

RATE = 48000  # frame rate on the wire; also what the codec's FLL locks to

# DAC digital gain, dB. Raising this does not reliably make the jack louder:
# the analog output stage runs out of headroom first, so extra digital gain
# turns into distortion. Measure before trusting a larger number.
DAC_VOLUME = 0
# Headphone analog volume, dB. Only 0, -3, -6 and -9 exist.
HEADPHONE_VOLUME = 0

# MIDI note numbers for a C-major scale, C4 up to C5.
SCALE = (60, 62, 64, 65, 67, 69, 71, 72)
NOTE_SECONDS = 0.4

# CAUTION: this drives the headphone amplifier. Take the headphones off before
# the first run and confirm the level is comfortable before wearing them.

i2s = audiobusio.I2SOut(board.I2S_BIT_CLOCK, board.I2S_WORD_SELECT, board.I2S_DOUT)

synth = synthio.Synthesizer(sample_rate=RATE)

# Playing the synth starts BCLK, which the codec's FLL needs before it can lock.
# The synth streams silence until a note is pressed, so nothing is audible yet.
i2s.play(synth)

codec = adafruit_nau88l21.NAU88L21(board.I2C())
codec.configure_clocks()

# headphone_output is a quickstart that deliberately ends quiet, at -20 dB DAC
# and -9 dB headphone. Set both volumes afterward rather than leaving the defaults
codec.headphone_output = True
codec.dac_volume = DAC_VOLUME
codec.headphone_volume = HEADPHONE_VOLUME

print("playing scale")
try:
    while True:
        for note in SCALE:
            synth.press(note)
            time.sleep(0.25)
            synth.release(note)
            time.sleep(0.125)
finally:
    i2s.stop()
    i2s.deinit()
