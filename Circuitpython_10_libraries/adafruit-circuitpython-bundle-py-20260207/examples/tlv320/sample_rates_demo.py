# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: Copyright 2025 Sam Blenny
#
# WAV file beep demo for Fruit Jam (adjust pins as needed for other boards)
#
import time

import audiocore
from audiobusio import I2SOut
from board import I2C, I2S_BCLK, I2S_DIN, I2S_MCLK, I2S_WS
from digitalio import DigitalInOut, Direction, Pull
from micropython import const
from pwmio import PWMOut

from adafruit_tlv320 import TLV320DAC3100

# I2S MCLK clock frequency
MCLK_HZ = const(15_000_000)


def configure_dac(i2c, sample_rate, mclk_hz):
    # Configure TLV320DAC.
    # When mclk_hz is not None, you must provide a 15 MHz PWMOut clock to the
    # DAC's MCLK pin.

    # 1. Initialize DAC (this includes a soft reset and sets minimum volumes)
    dac = TLV320DAC3100(i2c)

    # 2. Configure headphone/speaker routing and volumes (order matters here)
    #
    #    CAUTION: The TLV320 includes a DSP oversampling filter in the signal
    #    chain before the dac.dac_volume setting is applied. The filter may
    #    boost the gain of loud samples (near 0 dBfs) to the point that they
    #    clip and distort if you have dac.dac_volume set too high. To prevent
    #    clipping, it's best to set dac.dac_volume to no more than -3 or -6 dB.
    #    If you want more gain without distortion, you can turn up the analog
    #    headphone amplifiers with dac.headphone_volume. For line level, try
    #    dac.dac_volume = -3 and dac.headphone_volume = 0.
    #
    dac.speaker_output = False
    dac.headphone_output = True
    dac.dac_volume = -3  # Keep this below 0 to avoid DSP filter clipping
    dac.headphone_volume = 0  # CAUTION! Line level. Too loud for headphones!

    # 3. Configure the right PLL and CODEC settings for our sample rate
    dac.configure_clocks(sample_rate=sample_rate, mclk_freq=MCLK_HZ)

    # 4. Wait for power-on volume ramp-up to finish
    time.sleep(0.35)
    return dac


# Set up I2C and I2S buses
i2c = I2C()
audio = I2SOut(bit_clock=I2S_BCLK, word_select=I2S_WS, data=I2S_DIN)

# To hear how MCLK improves audio when even using PLL_CLKIN=BCLK, uncomment
# the next line and comment out the `if mclk_hz_:` blocks in the loop below.
# mclk_pwm = PWMOut(I2S_MCLK, frequency=MCLK_HZ, duty_cycle=2**15)

# Loop through all the sample rate and clock source options
mclk_rates = (
    (8000, "sinewave_8kHz.wav", 2),  # 8000 gets 2 beeps
    (11025, "sinewave_11kHz.wav", 3),  # 11025 gets 3 beeps
    (22050, "sinewave_22kHz.wav", 4),  # 4 beeps
    (44100, "sinewave_44kHz.wav", 5),  # ...
    (48000, "sinewave_48kHz.wav", 6),
)
while True:
    # First do MCLK = 15 MHz, then do MCLK = None (meaning use BCLK)
    for mclk_hz_ in (MCLK_HZ, None):
        if mclk_hz_:
            # Set up 15 MHz MCLK PWM clock output for less hiss and distortion
            mclk_pwm = PWMOut(I2S_MCLK, frequency=MCLK_HZ, duty_cycle=2**15)

        # Play beeps at all supported sample rates
        print(f"Using MCLK = {mclk_hz_}:")
        for (
            sample_rate,
            filename,
            beeps,
        ) in mclk_rates:
            # Reset and re-configure DAC for the current sample rate
            dac = configure_dac(i2c, sample_rate, mclk_hz_)

            # Load wav file with 650 Hz beep at this sample rate
            sample = audiocore.WaveFile(filename)

            # Play beeps
            print(f" sample rate {sample_rate} Hz: {beeps} beeps...")
            for _ in range(beeps):
                audio.play(sample)
                time.sleep(0.19)

            # Pause before switching to next sample rate
            time.sleep(0.7)

            # Mute before next loop iteration resets DAC (reduce popping noise)
            dac.headphone_left_mute = True
            dac.headphone_right_mute = True
            time.sleep(0.1)

        if mclk_hz_:
            # When switching to BCLK, stop sending the PWM clock signal to MCLK
            mclk_pwm.deinit()

        # Pause before next clock source
        time.sleep(0.8)

    # Pause before starting over
    print()
    time.sleep(3)
