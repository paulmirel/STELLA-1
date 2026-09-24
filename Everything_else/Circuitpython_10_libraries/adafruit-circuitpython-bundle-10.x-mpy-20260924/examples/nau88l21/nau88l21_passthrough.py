# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Mic -> headphone passthrough for the EP-2350, with a DSP chain in between.
"""

import time

import audiobusio
import audiodelays
import audiofilters
import audioi2sin
import board
import synthio

import adafruit_nau88l21

RATE = 48000  # frame rate on the wire; also what the codec's FLL expects

# --- Hardware effects config ---

# Analog mic gain, dB, -1 .. 36.
MIC_GAIN = 24
# ADC digital gain, dB.
ADC_VOLUME = 0
# DAC digital gain, dB.
DAC_VOLUME = 6
# Headphone analog volume, dB. Only 0/-3/-6/-9 exist.
HEADPHONE_VOLUME = 0

# --- Software effects config ---

# Gain of the software stage, in dB.
PRE_GAIN = 4.0
# High-pass corner, Hz.
HPF_HZ = 120


# The internal clock mode object has to exist first: it generates BCLK/WS, and
# everything in external clock mode syncs to the WS edges it sees. Constructing
# it starts BCLK, which the codec's FLL then has something to lock to.
i2s = audiobusio.I2SOut(board.I2S_BIT_CLOCK, board.I2S_WORD_SELECT, board.I2S_DOUT)

codec = adafruit_nau88l21.NAU88L21(board.I2C())
codec.configure_clocks()

# enable headphone output and set hardware volume
codec.headphone_output = True
codec.dac_volume = DAC_VOLUME
codec.headphone_volume = HEADPHONE_VOLUME

codec.configure_microphone_input(gain_db=MIC_GAIN)
codec.adc_volume = ADC_VOLUME

mic = audioi2sin.I2SIn(
    board.I2S_BIT_CLOCK,
    board.I2S_WORD_SELECT,
    board.I2S_DIN,
    sample_rate=RATE,
    bit_depth=16,
    mono=True,
    external_clock=True,
    left_justified=False,
)

common = dict(
    buffer_size=1024, sample_rate=RATE, bits_per_sample=16, samples_signed=True, channel_count=1
)
hpf = audiofilters.Filter(
    filter=synthio.Biquad(synthio.FilterMode.HIGH_PASS, frequency=HPF_HZ, Q=0.7), mix=1.0, **common
)
amp = audiofilters.Distortion(
    pre_gain=PRE_GAIN,
    drive=0.0,
    mode=audiofilters.DistortionMode.LOFI,
    soft_clip=True,
    mix=1.0,
    **common,
)

# WIRING ORDER MATTERS. Work from the output backwards, so the call that
# hands the mic to something is the LAST one:
#
#     i2s.play(amp) -> amp.play(hpf) -> hpf.play(mic)
#
# i2s.play() restarts the internal clock mode state machine, which knocks the
# external clock mode I2SIn off the frame it locked to. The firmware re-syncs
# that I2SIn from its reset_buffer(), which only runs when something
# calls play() *on the mic*. The effects do not propagate reset_buffer() down
# to their own source. So wiring the mic in first (hpf.play(mic) before
# i2s.play(amp)) syncs the mic and then immediately de-syncs it,
# the output is silence or hiss.

i2s.play(amp, loop=True)
amp.play(hpf)
hpf.play(mic)

print(
    f"passthrough running: mic gain {codec.mic_gain:.0f} dB, +{PRE_GAIN:.1f} dB, HPF {HPF_HZ:d} Hz"
)

try:
    while True:
        time.sleep(1)
        # Reading .overflow clears it. It trips if the playback side falls
        # behind the mic, which should not happen here -- both run off the
        # same BCLK -- so a report means something is wrong.
        if mic.overflow:
            print("overflow")
except KeyboardInterrupt:
    i2s.stop()
    i2s.deinit()
    mic.deinit()
