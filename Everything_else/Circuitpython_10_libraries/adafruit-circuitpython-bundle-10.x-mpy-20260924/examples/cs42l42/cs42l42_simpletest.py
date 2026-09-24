# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Play a one-octave scale out the headphone jack with synthio.

Pin names are the Teenage Engineering SP-1's, the only board this driver has
been run on.

Two ordering rules matter, and between them they fix the whole shape of this
example:

* **Reset before I2C.** The SP-1 holds both codec RESET lines low at the start
  of every VM run, and a codec in reset does not ACK. Handing the driver the
  pin as ``reset_pin`` is what deals with that: ``__init__`` pulses RESET
  before it touches the bus, so the codec is answering by the time the address
  is probed.
* **Clocks before the codec.** Out of reset the codec runs from an internal RC
  oscillator that is good for I2C and nothing else, and ``configure_clocks`` is
  the handover to the incoming bit clock. Playing the synth is what starts that
  bit clock, so it goes first.

``board.OSC_EN`` gates the SP-1's audio oscillator and has to be on.
"""

import time

import audiobusio
import board
import digitalio
import synthio

import adafruit_cs42l42

RATE = 48000
# CircuitPython sends 32 bit clocks per stereo frame, so the bit clock the
# codec sees -- and the number configure_clocks wants -- is 32 x the rate.
SCLK = RATE * 32

# Mixer attenuation, dB. 0 is full scale; the quickstart starts at -20.
DAC_VOLUME = -20

# MIDI note numbers for a C-major scale, C4 up to C5.
SCALE = (60, 62, 64, 65, 67, 69, 71, 72)

# CAUTION: this drives a headphone amplifier. Take the headphones off before
# the first run and confirm the level is comfortable before wearing them.

oscillator = digitalio.DigitalInOut(board.OSC_EN)
oscillator.direction = digitalio.Direction.OUTPUT
oscillator.value = True

reset = digitalio.DigitalInOut(board.CS42_RESET)
reset.direction = digitalio.Direction.OUTPUT
reset.value = False  # active low: hold the codec in reset while clocks start

i2s = audiobusio.I2SOut(board.I2S_BIT_CLOCK, board.I2S_WORD_SELECT, board.I2S_DOUT)

synth = synthio.Synthesizer(sample_rate=RATE)

# Playing the synth starts the bit clock, which the codec needs before it can
# switch off its own oscillator. The synth streams silence until a note is
# pressed, so nothing is audible yet.
i2s.play(synth)

# Constructing the driver releases the reset
codec = adafruit_cs42l42.CS42L42(board.I2C(), reset_pin=reset)
codec.configure_clocks(sclk_hz=SCLK)
codec.configure_asp(sample_rate=RATE, bit_depth=16)

codec.headphone_output = True
codec.dac_volume = DAC_VOLUME

print("playing scale")
try:
    while True:
        for note in SCALE:
            synth.press(note)
            time.sleep(0.25)
            synth.release(note)
            time.sleep(0.125)
finally:
    codec.muted = True
    i2s.stop()
    i2s.deinit()
    reset.value = False
    reset.deinit()
    oscillator.value = False
    oscillator.deinit()
