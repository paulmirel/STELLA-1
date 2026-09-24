# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_tas2505`
================================================================================

CircuitPython driver library for TI TAS2505 audio amplifier


* Author(s): Tim Cocks

Implementation Notes
--------------------

**Hardware:**

* The TAS2505 is a mono I2S DAC with two output stages: a Class-D speaker
  amplifier (SPKP/SPKM) and a headphone driver (HPOUT). Both are fed from the
  same mono DAC, so they play the same audio; each has its own analog volume
  attenuator and its own output gain stage.

* Because the DAC is mono, one of the two I2S channels has to be picked (or
  the two mixed down) with ``dac_path``. The default is the left channel.

* The signal chain for each output is DAC -> digital volume (``dac_volume``)
  -> Mixer P -> analog attenuator (``speaker_volume`` / ``headphone_volume``)
  -> output amplifier gain (``speaker_gain`` / ``headphone_gain``). You can
  ignore most of that and use ``speaker_output = True`` or
  ``headphone_output = True``, which load a full set of quiet defaults.

* **CAUTION**: The Class-D amplifier can put ~2 W into a 8-Ohm speaker and the
  headphone driver goes to +29 dB of gain, which is far more than headphones
  or your hearing want. Start low and come up slowly. That is why the defaults
  loaded by ``speaker_output`` and ``headphone_output`` are quiet ones.

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice

Usage Examples
--------------

Speaker
^^^^^^^

The DAC takes its clocks from the bus here: it recovers everything it needs
from the I2S bit clock, so no MCLK signal is required. ``configure_clocks``
works out the PLL and divider settings for the sample rate you ask for.

::

    dac = TAS2505(board.I2C())
    dac.configure_clocks(sample_rate=44100)
    dac.speaker_output = True             # set defaults for the speaker
    dac.dac_volume = dac.dac_volume + 1   # increase volume by 1 dB

    audio = audiobusio.I2SOut(bit_clock=board.I2S_BCLK, word_select=board.I2S_WS,
        data=board.I2S_DIN)

Headphones
^^^^^^^^^^

::

    dac = TAS2505(board.I2C())
    dac.configure_clocks(sample_rate=44100)
    dac.speaker_output = False            # make sure the Class-D amp is off
    dac.headphone_output = True           # set defaults for headphones
    dac.headphone_volume = -20            # CAUTION: start quiet, come up slowly

Using an MCLK
^^^^^^^^^^^^^

If the board supplies an MCLK signal, hand its frequency to
``configure_clocks`` and the PLL locks to that instead of to the bit clock.
This is worth doing when the bit clock is jittery, and it is the only option
below 16 kHz, where a 32x bit clock falls under the PLL's 512 kHz input
minimum.

::

    mclk_out = pwmio.PWMOut(board.I2S_MCLK, frequency=12_288_000, duty_cycle=2**15)
    dac = TAS2505(board.I2C())
    dac.configure_clocks(sample_rate=8000, mclk_freq=12_288_000)

Non-CircuitPython bit clocks
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

CircuitPython's I2S output sends 16-bit stereo, so its bit clock is 32x the
sample rate, which is what ``configure_clocks`` assumes. If something else on
the board is generating the frame -- another codec driving the I2S clocks, say
-- pass the real ratio and word length:

::

    # 24-bit words in 32-bit slots, stereo: BCLK is 64x the sample rate
    dac.configure_clocks(sample_rate=48000, bit_depth=24, bclk_ratio=64)

API
---
"""

import time

from adafruit_bus_device.i2c_device import I2CDevice
from micropython import const

try:
    from typing import Dict, Optional, Tuple

    from busio import I2C
except ImportError:
    pass

__version__ = "1.0.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_TAS2505.git"

# Page 0 registers
_PAGE_SELECT = const(0x00)
_RESET = const(0x01)
_CLOCK_MUX1 = const(0x04)
_PLL_PROG_PR = const(0x05)
_PLL_PROG_J = const(0x06)
_PLL_PROG_D_MSB = const(0x07)
_PLL_PROG_D_LSB = const(0x08)
_NDAC = const(0x0B)
_MDAC = const(0x0C)
_DOSR_MSB = const(0x0D)
_DOSR_LSB = const(0x0E)
_CODEC_IF_CTRL1 = const(0x1B)
_DATA_OFFSET = const(0x1C)
_CODEC_IF_CTRL2 = const(0x1D)
_DAC_FLAG = const(0x25)
_DAC_FLAG2 = const(0x26)
_STICKY_FLAG1 = const(0x2A)
_INT_FLAG1 = const(0x2B)
_STICKY_FLAG2 = const(0x2C)
_INT_FLAG2 = const(0x2E)
_INT1_CTRL = const(0x30)
_INT2_CTRL = const(0x31)
_DAC_PRB = const(0x3C)
_DAC_SETUP1 = const(0x3F)
_DAC_SETUP2 = const(0x40)
_DAC_VOL = const(0x41)

# Page 1 registers
_REF_POR_LDO = const(0x01)
_LDO_CTRL = const(0x02)
_PLAYBACK_CFG = const(0x03)
_DAC_PGA_CTRL = const(0x08)
_OUT_DRIVERS = const(0x09)
_COMMON_MODE = const(0x0A)
_HP_OCP = const(0x0B)
_HP_ROUTING = const(0x0C)
_HP_DRIVER_GAIN = const(0x10)
_HP_STARTUP = const(0x14)
_HP_VOL = const(0x16)
_AINL_VOL = const(0x18)
_AINR_VOL = const(0x19)
_SPK_AMP_CTRL = const(0x2D)
_SPK_VOL = const(0x2E)
_SPK_DRIVER = const(0x30)
_ANALOG_GAIN_FLAG = const(0x3F)
_SPK_DELAY = const(0x51)
_REF_PWRUP_DELAY = const(0x7A)

# Default I2C address
I2C_ADDR_DEFAULT = const(0x18)

# Data format for the I2S interface
FORMAT_I2S = const(0b00)  # I2S format
FORMAT_DSP = const(0b01)  # DSP format
FORMAT_RJF = const(0b10)  # Right justified format
FORMAT_LJF = const(0b11)  # Left justified format

# Data length for the I2S interface
DATA_LEN_16 = const(0b00)  # 16 bits
DATA_LEN_20 = const(0b01)  # 20 bits
DATA_LEN_24 = const(0b10)  # 24 bits
DATA_LEN_32 = const(0b11)  # 32 bits

# A word length can be given either as one of the codes above or as a plain bit
# count, which is what ``configure_clocks`` takes. The two sets do not overlap,
# so accepting both is unambiguous -- and it stops a ``24`` meant as a bit count
# from silently masking down to DATA_LEN_16.
_DATA_LEN_FOR_BITS = {16: DATA_LEN_16, 20: DATA_LEN_20, 24: DATA_LEN_24, 32: DATA_LEN_32}
_DATA_LEN_CODES = (DATA_LEN_16, DATA_LEN_20, DATA_LEN_24, DATA_LEN_32)


def _data_len_code(data_len):
    """Normalize a word length given as a bit count or a DATA_LEN_* code."""
    if data_len in _DATA_LEN_FOR_BITS:
        return _DATA_LEN_FOR_BITS[data_len]
    if data_len in _DATA_LEN_CODES:
        return data_len
    raise ValueError(
        f"data_len must be a bit count (16, 20, 24, 32) or a DATA_LEN_* code, not {data_len!r}"
    )


# DAC data path options. The DAC is mono, so this picks which half of the
# stereo I2S frame it plays.
#: DAC data path option: DAC data path off
DAC_PATH_OFF = const(0b00)
#: DAC data path option: play the left channel of the audio interface
DAC_PATH_LEFT = const(0b01)
#: DAC data path option: play the right channel of the audio interface
DAC_PATH_RIGHT = const(0b10)
#: DAC data path option: play a mono mix of the left and right channels
DAC_PATH_MONO_MIX = const(0b11)

# DAC volume control soft stepping options
#: DAC volume control soft stepping option: one step per DAC word clock
VOLUME_STEP_1SAMPLE = const(0b00)
#: DAC volume control soft stepping option: one step per two DAC word clocks
VOLUME_STEP_2SAMPLE = const(0b01)
#: DAC volume control soft stepping option: soft stepping disabled
VOLUME_STEP_DISABLED = const(0b10)

# DAC output routing options
#: DAC output routing option: DAC not routed to either output driver
DAC_ROUTE_NONE = const(0b00)
#: DAC output routing option: DAC routed through Mixer P and the analog
#: attenuators. This is the routing the speaker driver needs, and the one that
#: gives the headphone output its ``headphone_volume`` control.
DAC_ROUTE_MIXER = const(0b01)
#: DAC output routing option: DAC routed straight to the headphone driver,
#: bypassing the headphone attenuator (so ``headphone_volume`` does nothing)
DAC_ROUTE_HP = const(0b10)

# Class-D speaker amplifier gain options
#: Speaker amplifier gain option: driver muted
SPK_GAIN_MUTE = const(0b000)
#: Speaker amplifier gain option: 6 dB
SPK_GAIN_6DB = const(0b001)
#: Speaker amplifier gain option: 12 dB
SPK_GAIN_12DB = const(0b010)
#: Speaker amplifier gain option: 18 dB
SPK_GAIN_18DB = const(0b011)
#: Speaker amplifier gain option: 24 dB
SPK_GAIN_24DB = const(0b100)
#: Speaker amplifier gain option: 32 dB
SPK_GAIN_32DB = const(0b101)

# DAC PowerTune modes, which trade power against noise performance
#: PowerTune mode: PTM_P3/PTM_P4, the best performing and hungriest
PTM_P3P4 = const(0b000)
#: PowerTune mode: PTM_P2
PTM_P2 = const(0b001)
#: PowerTune mode: PTM_P1, the lowest power
PTM_P1 = const(0b010)

# DAC signal processing blocks. See datasheet Table 3-3.
#: Processing block PRB_P1: interpolation filter A, IIR, 6 biquads
PRB_P1 = const(0x01)
#: Processing block PRB_P2: interpolation filter A, no IIR, 3 biquads
PRB_P2 = const(0x02)
#: Processing block PRB_P3: interpolation filter B, IIR, 6 biquads
PRB_P3 = const(0x03)

# Full chip common mode voltage options
#: Common mode voltage option: 0.9 V
CM_0_9V = const(0b0)
#: Common mode voltage option: 0.75 V
CM_0_75V = const(0b1)

# AVDD LDO output voltage options
#: AVDD LDO output option: 1.8 V
LDO_1_8V = const(0b00)
#: AVDD LDO output option: 1.6 V
LDO_1_6V = const(0b01)
#: AVDD LDO output option: 1.7 V
LDO_1_7V = const(0b10)
#: AVDD LDO output option: 1.5 V
LDO_1_5V = const(0b11)

# Headphone over current detection debounce options
#: Headphone over current debounce option: no debounce
OCP_DEBOUNCE_0MS = const(0b000)
#: Headphone over current debounce option: 8 ms
OCP_DEBOUNCE_8MS = const(0b001)
#: Headphone over current debounce option: 16 ms
OCP_DEBOUNCE_16MS = const(0b010)
#: Headphone over current debounce option: 32 ms
OCP_DEBOUNCE_32MS = const(0b011)
#: Headphone over current debounce option: 64 ms
OCP_DEBOUNCE_64MS = const(0b100)
#: Headphone over current debounce option: 128 ms
OCP_DEBOUNCE_128MS = const(0b101)
#: Headphone over current debounce option: 256 ms
OCP_DEBOUNCE_256MS = const(0b110)
#: Headphone over current debounce option: 512 ms
OCP_DEBOUNCE_512MS = const(0b111)

# Headphone driver soft-routing step time options
#: Headphone soft-routing step time option: 0 ms
HP_ROUTING_STEP_0MS = const(0b00)
#: Headphone soft-routing step time option: 50 ms
HP_ROUTING_STEP_50MS = const(0b01)
#: Headphone soft-routing step time option: 100 ms
HP_ROUTING_STEP_100MS = const(0b10)
#: Headphone soft-routing step time option: 200 ms
HP_ROUTING_STEP_200MS = const(0b11)

# Speaker amplifier power-on delay options
#: Speaker power-on delay option: 512 ramp cycles
SPK_DELAY_512 = const(0b00)
#: Speaker power-on delay option: 1024 ramp cycles
SPK_DELAY_1024 = const(0b01)
#: Speaker power-on delay option: 256 ramp cycles
SPK_DELAY_256 = const(0b10)
#: Speaker power-on delay option: 16 ramp cycles
SPK_DELAY_16 = const(0b11)

# ruff: noqa: PLR0904, PLR0912, PLR0913, PLR0915, PLR0917

# Lookup table for the analog attenuators: speaker_volume, headphone_volume
# and the AINL/AINR volume controls all share this scale. These values are the
# ones tabulated for Page 1 / Register 46 (the speaker volume control) in the
# TAS2505 Application Reference Guide, SLAU472C.
#
# The headphone table in the same document differs in four places, all of them
# in the deep attenuation region where the difference is inaudible: code 0x41
# is given as -32.6 dB rather than -32.7, 0x4A as -37.2 rather than -37.1,
# 0x6F as -60.1 rather than -60.2, and 0x73 as -66.7 rather than -68.7. One
# table is used for both.
#
# Codes above the end of this table are reserved, except for the mute code of
# each register (0x75 for headphone, 0x7F for speaker), which the mute
# properties write instead of a level.
ANALOG_VOLUME_TABLE = (
    0,  # 0x00
    -0.5,  # 0x01
    -1,  # 0x02
    -1.5,  # 0x03
    -2,  # 0x04
    -2.5,  # 0x05
    -3,  # 0x06
    -3.5,  # 0x07
    -4,  # 0x08
    -4.5,  # 0x09
    -5,  # 0x0A
    -5.5,  # 0x0B
    -6,  # 0x0C
    -6.5,  # 0x0D
    -7,  # 0x0E
    -7.5,  # 0x0F
    -8,  # 0x10
    -8.5,  # 0x11
    -9,  # 0x12
    -9.5,  # 0x13
    -10,  # 0x14
    -10.5,  # 0x15
    -11,  # 0x16
    -11.5,  # 0x17
    -12,  # 0x18
    -12.5,  # 0x19
    -13,  # 0x1A
    -13.5,  # 0x1B
    -14.1,  # 0x1C
    -14.6,  # 0x1D
    -15.1,  # 0x1E
    -15.6,  # 0x1F
    -16,  # 0x20
    -16.5,  # 0x21
    -17.1,  # 0x22
    -17.5,  # 0x23
    -18.1,  # 0x24
    -18.6,  # 0x25
    -19.1,  # 0x26
    -19.6,  # 0x27
    -20.1,  # 0x28
    -20.6,  # 0x29
    -21.1,  # 0x2A
    -21.6,  # 0x2B
    -22.1,  # 0x2C
    -22.6,  # 0x2D
    -23.1,  # 0x2E
    -23.6,  # 0x2F
    -24.1,  # 0x30
    -24.6,  # 0x31
    -25.1,  # 0x32
    -25.6,  # 0x33
    -26.1,  # 0x34
    -26.6,  # 0x35
    -27.1,  # 0x36
    -27.6,  # 0x37
    -28.1,  # 0x38
    -28.6,  # 0x39
    -29.1,  # 0x3A
    -29.6,  # 0x3B
    -30.1,  # 0x3C
    -30.6,  # 0x3D
    -31.1,  # 0x3E
    -31.6,  # 0x3F
    -32.1,  # 0x40
    -32.7,  # 0x41
    -33.1,  # 0x42
    -33.6,  # 0x43
    -34.1,  # 0x44
    -34.6,  # 0x45
    -35.2,  # 0x46
    -35.7,  # 0x47
    -36.1,  # 0x48
    -36.7,  # 0x49
    -37.1,  # 0x4A
    -37.7,  # 0x4B
    -38.2,  # 0x4C
    -38.7,  # 0x4D
    -39.2,  # 0x4E
    -39.7,  # 0x4F
    -40.2,  # 0x50
    -40.7,  # 0x51
    -41.2,  # 0x52
    -41.8,  # 0x53
    -42.1,  # 0x54
    -42.7,  # 0x55
    -43.2,  # 0x56
    -43.8,  # 0x57
    -44.3,  # 0x58
    -44.8,  # 0x59
    -45.2,  # 0x5A
    -45.8,  # 0x5B
    -46.2,  # 0x5C
    -46.7,  # 0x5D
    -47.4,  # 0x5E
    -47.9,  # 0x5F
    -48.2,  # 0x60
    -48.7,  # 0x61
    -49.3,  # 0x62
    -50,  # 0x63
    -50.3,  # 0x64
    -51,  # 0x65
    -51.4,  # 0x66
    -51.8,  # 0x67
    -52.3,  # 0x68
    -52.7,  # 0x69
    -53.7,  # 0x6A
    -54.2,  # 0x6B
    -55.4,  # 0x6C
    -56.7,  # 0x6D
    -58.3,  # 0x6E
    -60.2,  # 0x6F
    -62.7,  # 0x70
    -64.3,  # 0x71
    -66.2,  # 0x72
    -68.7,  # 0x73
    -72.3,  # 0x74
)


def _db_to_volume_code(db: float) -> int:
    """Convert an analog attenuation in dB to its register code.

    :param db: Analog volume in dB; range is 0 dB (loud) to -72.3 dB (soft)
    :return: Register code, range 0 (loud) to 116 (soft)
    """
    # Clip the dB argument into the range the table covers
    db = max(ANALOG_VOLUME_TABLE[-1], min(0, db))
    # Walk the table for the first code whose dB value is not above the target
    result = 0
    for code, table_db in enumerate(ANALOG_VOLUME_TABLE):
        if db < table_db:
            result = code
        elif db == table_db:
            result = code
            break
        else:
            break
    return result


def _volume_code_to_db(code: int) -> float:
    """Convert an analog volume register code to dB.

    :param code: Register code, range 0 (loud) to 116 (soft)
    :return: Analog volume in dB, range 0 dB (loud) to -72.3 dB (soft)
    """
    return ANALOG_VOLUME_TABLE[max(0, min(len(ANALOG_VOLUME_TABLE) - 1, int(code)))]


# Resource class of each processing block, from datasheet Table 3-3. The
# divider search has to satisfy MDAC * DOSR / 32 >= RC.
_RESOURCE_CLASS = {PRB_P1: 6, PRB_P2: 4, PRB_P3: 4}


# Oversampling ratios to try, largest first. These are the ones TI's own
# examples use; anything that is a multiple of 8 and lands in the datasheet's
# window is legal, but there is no reason to pick an odd one.
_DOSR_CHOICES = (1024, 768, 512, 384, 256, 192, 128, 96, 64, 32, 16, 8)


def _pick_dosr(sample_rate: int) -> int:
    """Pick a DAC oversampling ratio for a sample rate.

    The datasheet's constraint is 2.8 MHz < DOSR x DAC_fS < 6.2 MHz, with DOSR
    a multiple of 8. Oversampling as hard as that allows pushes the
    delta-sigma modulator's quantization noise further above the audio band,
    so the lowest sample rates get the largest DOSR.

    :param sample_rate: The sample rate in Hz
    :raises ValueError: If no legal DOSR exists for this sample rate
    :return: The oversampling ratio
    """
    for dosr in _DOSR_CHOICES:
        if 2_800_000 < dosr * sample_rate < 6_200_000:
            return dosr
    # Nothing standard fits, so walk multiples of 8 from the top of the window
    dosr = 8 * (6_199_999 // (8 * sample_rate))
    if dosr < 8 or dosr * sample_rate <= 2_800_000:
        raise ValueError(f"No legal DAC oversampling ratio for {sample_rate} Hz")
    return dosr


def _split_dividers(total: int, dosr: int, resource_class: int) -> Optional[Tuple[int, int]]:
    """Split a total divider into NDAC and MDAC.

    The datasheet asks for NDAC to be as large as possible, subject to
    MDAC x DOSR / 32 >= RC, because the NDAC divider runs the slower half of
    the clock tree.

    :param total: The product NDAC x MDAC that is needed
    :param dosr: The DAC oversampling ratio
    :param resource_class: The processing block's resource class
    :return: An (ndac, mdac) tuple, or None if the total cannot be split
    """
    best = None
    for mdac in range(1, 129):
        if total % mdac or mdac * dosr < resource_class * 32:
            continue
        ndac = total // mdac
        if ndac > 128:
            continue
        if best is None or ndac > best[0]:
            best = (ndac, mdac)
    return best


def _pll_multipliers(
    pll_clkin: int, codec_clkin: int, exact: bool
) -> Optional[Tuple[int, int, int, int, int]]:
    """Search the PLL multipliers that turn one input clock into one output clock.

    :param pll_clkin: The PLL input clock frequency in Hz
    :param codec_clkin: The CODEC_CLKIN frequency the PLL has to produce
    :param exact: True to only accept an integer (D = 0) solution, False to
        allow a fractional one
    :return: An (error, p, r, j, d) tuple, or None if nothing fits
    """
    best = None
    for p in range(1, 9):
        # 512 kHz to 20 MHz is the input window for an integer PLL; a
        # fractional one narrows the bottom of it to 10 MHz
        divided = pll_clkin // p
        if not (512_000 if exact else 10_000_000) <= divided <= 20_000_000:
            continue
        for r in range(1, 17):
            if exact:
                if (codec_clkin * p) % (pll_clkin * r):
                    continue
                j = (codec_clkin * p) // (pll_clkin * r)
                if 4 <= j <= 63 and 4 <= r * j <= 259:
                    return (0, p, r, j, 0)
                continue
            scaled = (codec_clkin * p * 10000) // (pll_clkin * r)
            j, d = scaled // 10000, scaled % 10000
            if not 4 <= j <= 63:
                continue
            error = abs(pll_clkin * r * scaled // (p * 10000) - codec_clkin)
            if best is None or error < best[0]:
                best = (error, p, r, j, d)
    return best


def _solve_pll(
    pll_clkin: int, sample_rate: int, dosr: int, resource_class: int
) -> Optional[Tuple[int, int, int, int, int, int]]:
    """Solve the PLL and divider settings for a sample rate.

    CODEC_CLKIN = NDAC x MDAC x DOSR x DAC_fS has to come out of the PLL,
    whose output is PLL_CLKIN x R x J.D / P. The datasheet constraints are:

    * 80 MHz <= PLL_CLKIN x R x J.D / P <= 110 MHz
    * 512 kHz <= PLL_CLKIN / P <= 20 MHz when D is zero, and
      10 MHz <= PLL_CLKIN / P <= 20 MHz when it is not
    * 4 <= R x J <= 259 when D is zero
    * DAC_CLK (CODEC_CLKIN / NDAC) <= 49.152 MHz

    An integer solution (D = 0) is looked for first, since a fractional PLL
    has more jitter; the fractional search only runs if there is no exact
    integer answer, and then the closest approximation wins.

    :param pll_clkin: The PLL input clock frequency in Hz
    :param sample_rate: The sample rate in Hz
    :param dosr: The DAC oversampling ratio
    :param resource_class: The processing block's resource class
    :return: A (p, r, j, d, ndac, mdac) tuple, or None if nothing satisfies
        the constraints
    """
    step = dosr * sample_rate
    lowest = -(-80_000_000 // step)
    highest = 110_000_000 // step
    best = None

    for exact in (True, False):
        for total in range(lowest, highest + 1):
            codec_clkin = total * step
            split = _split_dividers(total, dosr, resource_class)
            if split is None or codec_clkin // split[0] > 49_152_000:
                continue
            found = _pll_multipliers(pll_clkin, codec_clkin, exact)
            if found is None:
                continue
            error, p, r, j, d = found
            if exact:
                return (p, r, j, d) + split
            if best is None or error < best[0]:
                best = (error, (p, r, j, d) + split)

    return best[1] if best else None


def _solve_clocks(
    clock_in: int,
    sample_rate: int,
    dosr: int,
    resource_class: int,
    ndac: Optional[int],
    mdac: Optional[int],
    use_pll: bool,
) -> Optional[Tuple[int, int, int, int, int, int]]:
    """Solve everything between the input clock and the sample rate.

    :param clock_in: The input clock frequency in Hz
    :param sample_rate: The sample rate in Hz
    :param dosr: The DAC oversampling ratio
    :param resource_class: The processing block's resource class
    :param ndac: A pinned NDAC divider, or None to solve for one
    :param mdac: A pinned MDAC divider, or None to solve for one
    :param use_pll: Whether the clock runs through the PLL
    :raises ValueError: If pinned dividers ask the PLL for a clock it cannot
        produce
    :return: A (p, r, j, d, ndac, mdac) tuple, or None if nothing satisfies
        the constraints. P, R, J and D are all zero when the PLL is not used.
    """
    if ndac is None or mdac is None:
        if use_pll:
            return _solve_pll(clock_in, sample_rate, dosr, resource_class)
        dividers = _solve_dividers(clock_in, sample_rate, dosr, resource_class)
        return None if dividers is None else (0, 0, 0, 0) + dividers

    # The caller pinned the dividers, so the clock they imply is the one the
    # PLL has to produce -- or, without the PLL, the one the input clock
    # already has to be.
    codec_clkin = ndac * mdac * dosr * sample_rate
    if not use_pll:
        return (0, 0, 0, 0, ndac, mdac) if codec_clkin == clock_in else None
    if not 80_000_000 <= codec_clkin <= 110_000_000:
        raise ValueError(
            f"NDAC {ndac} and MDAC {mdac} need a {codec_clkin} Hz CODEC_CLKIN, which is "
            "outside the PLL's 80 MHz to 110 MHz output range"
        )
    found = _pll_multipliers(clock_in, codec_clkin, True) or _pll_multipliers(
        clock_in, codec_clkin, False
    )
    return None if found is None else found[1:] + (ndac, mdac)


def _solve_dividers(
    codec_clkin: int, sample_rate: int, dosr: int, resource_class: int
) -> Optional[Tuple[int, int]]:
    """Solve the NDAC and MDAC dividers for a clock used without the PLL.

    :param codec_clkin: The CODEC_CLKIN frequency in Hz
    :param sample_rate: The sample rate in Hz
    :param dosr: The DAC oversampling ratio
    :param resource_class: The processing block's resource class
    :return: An (ndac, mdac) tuple, or None if this clock cannot make this
        sample rate with the dividers alone
    """
    step = dosr * sample_rate
    if codec_clkin > 110_000_000 or codec_clkin % step:
        return None
    split = _split_dividers(codec_clkin // step, dosr, resource_class)
    if split is None or codec_clkin // split[0] > 49_152_000:
        return None
    return split


class _PagedRegisterBase:
    """Base class for paged register access."""

    def __init__(self, i2c_device, page):
        """Initialize the paged register base.

        :param i2c_device: The I2C device
        :param page: The register page number
        """
        self._device = i2c_device
        self._page = page
        self._buffer = bytearray(2)

    def _write_register(self, register, value):
        """Write a value to a register.

        :param register: The register address
        :param value: The value to write
        """
        self._set_page()
        self._buffer[0] = register
        self._buffer[1] = value
        with self._device as i2c:
            i2c.write(self._buffer)

    def _read_register(self, register):
        """Value from a register.

        :param register: The register address
        :return: The register value
        """
        self._set_page()
        self._buffer[0] = register
        with self._device as i2c:
            i2c.write(self._buffer, end=1)
            i2c.readinto(self._buffer, start=0, end=1)
        return self._buffer[0]

    def _set_page(self):
        """The current register page."""
        self._buffer[0] = _PAGE_SELECT
        self._buffer[1] = self._page
        with self._device as i2c:
            i2c.write(self._buffer)

    def _get_bits(self, register, mask, shift):
        """Specific bits from a register.

        :param register: The register address
        :param mask: The bit mask (after shifting)
        :param shift: The bit position (0 = LSB)
        :return: The extracted bits
        """
        value = self._read_register(register)
        return (value >> shift) & mask

    def _set_bits(self, register, mask, shift, value):
        """Specific bits in a register.

        :param register: The register address
        :param mask: The bit mask (after shifting)
        :param shift: The bit position (0 = LSB)
        :param value: The value to set
        """
        reg_value = self._read_register(register)
        reg_value &= ~(mask << shift)
        reg_value |= (value & mask) << shift
        self._write_register(register, reg_value)


class _Page0Registers(_PagedRegisterBase):
    """Page 0 registers containing clocking, the audio interface, and the DAC."""

    def __init__(self, i2c_device):
        """Initialize Page 0 registers.

        :param i2c_device: The I2C device
        """
        super().__init__(i2c_device, 0)

    def _reset(self):
        """Perform a software reset of the chip.

        :return: True if successful, False otherwise
        """
        self._write_register(_RESET, 1)
        time.sleep(0.01)
        return self._read_register(_RESET) == 0

    def _set_codec_interface(self, format, data_len, bclk_out=False, wclk_out=False):
        """The codec interface parameters."""
        value = (format & 0x03) << 6
        value |= (data_len & 0x03) << 4
        value |= (1 if bclk_out else 0) << 3
        value |= (1 if wclk_out else 0) << 2
        self._write_register(_CODEC_IF_CTRL1, value)

    def _get_codec_interface(self):
        """The current codec interface settings.

        :return: Dictionary with format, data_len, bclk_out, and wclk_out values
        """
        reg_value = self._read_register(_CODEC_IF_CTRL1)
        return {
            "format": (reg_value >> 6) & 0x03,
            "data_len": (reg_value >> 4) & 0x03,
            "bclk_out": bool(reg_value & (1 << 3)),
            "wclk_out": bool(reg_value & (1 << 2)),
        }

    def _set_dac_data_path(self, dac_on, path=DAC_PATH_LEFT, volume_step=VOLUME_STEP_1SAMPLE):
        """Configure the DAC data path settings."""
        value = 0x04  # D3-D2 are reserved and read back as 01
        if dac_on:
            value |= 1 << 7
        value |= (path & 0x03) << 4
        value |= volume_step & 0x03
        self._write_register(_DAC_SETUP1, value)

    def _get_dac_data_path(self):
        """The current DAC data path configuration.

        :return: Dictionary with DAC data path settings
        """
        reg_value = self._read_register(_DAC_SETUP1)
        return {
            "dac_on": bool(reg_value & (1 << 7)),
            "path": (reg_value >> 4) & 0x03,
            "volume_step": reg_value & 0x03,
        }

    def _set_dac_setup2(self, mute, auto_mute=0):
        """Configure the DAC mute and auto mute settings."""
        value = 0x04  # D2 is reserved and has to be written as 1
        value |= (auto_mute & 0x07) << 4
        if mute:
            value |= 1 << 3
        self._write_register(_DAC_SETUP2, value)

    def _get_dac_setup2(self):
        """The current DAC mute and auto mute configuration.

        :return: Dictionary with mute and auto_mute values
        """
        reg_value = self._read_register(_DAC_SETUP2)
        return {"mute": bool(reg_value & (1 << 3)), "auto_mute": (reg_value >> 4) & 0x07}

    def _set_dac_volume(self, db):
        """DAC digital volume in dB.

        :raises ValueError: If the volume is outside the -63.5 to 24 dB range
        """
        if not -63.5 <= db <= 24.0:
            raise ValueError("DAC volume must be in range -63.5 to 24 dB")
        self._write_register(_DAC_VOL, int(round(db * 2)) & 0xFF)

    def _get_dac_volume(self):
        """DAC digital volume in dB.

        :return: Current digital volume in dB
        """
        reg_val = self._read_register(_DAC_VOL)
        steps = reg_val - 256 if reg_val & 0x80 else reg_val
        return steps * 0.5

    def _get_dac_flags(self):
        """The DAC and output driver status flags.

        :return: Dictionary with status flags for various components
        """
        flag_reg = self._read_register(_DAC_FLAG)
        flag2_reg = self._read_register(_DAC_FLAG2)
        return {
            "dac_powered": bool(flag_reg & (1 << 7)),
            "hp_powered": bool(flag_reg & (1 << 5)),
            "dac_pga_gain_ok": bool(flag2_reg & (1 << 4)),
        }

    def _set_int_source(self, register, over_current, multiple_pulse):
        """Configure one of the interrupt sources."""
        value = 0
        if over_current:
            value |= 1 << 3
        if multiple_pulse:
            value |= 1 << 0
        self._write_register(register, value)

    def _configure_clocks_for_sample_rate(
        self, mclk_freq, sample_rate, bit_depth, bclk_ratio, dosr, ndac, mdac, use_pll
    ):
        # For sphinx docs, see configure_clocks() which wraps this function.
        # A bit count only -- unlike set_codec_interface, this one is documented
        # as bits and a bare 0..3 here would be a mistake, not a DATA_LEN_* code.
        if bit_depth not in _DATA_LEN_FOR_BITS:
            raise ValueError("Need a valid bit depth: 16, 20, 24, or 32")
        data_len = _DATA_LEN_FOR_BITS[bit_depth]

        if dosr is None:
            dosr = _pick_dosr(sample_rate)
        elif dosr % 4 or not 2_800_000 < dosr * sample_rate < 6_200_000:
            raise ValueError(f"DAC oversampling ratio {dosr} is illegal at {sample_rate} Hz")

        resource_class = _RESOURCE_CLASS.get(self._get_bits(_DAC_PRB, 0x1F, 0), 6)

        if mclk_freq:
            # MCLK pin drives the PLL (or CODEC_CLKIN directly)
            clock_in = mclk_freq
            clock_mux_source = 0b00
        else:
            # No MCLK, so the bit clock is the only clock the chip has. It is
            # bit_depth x 2 channels x sample rate unless told otherwise;
            # CircuitPython's I2S output sends 16-bit stereo, so 32x.
            clock_in = sample_rate * (bclk_ratio or bit_depth * 2)
            clock_mux_source = 0b01

        solution = _solve_clocks(clock_in, sample_rate, dosr, resource_class, ndac, mdac, use_pll)
        if solution is None:
            source = "MCLK" if mclk_freq else "BCLK"
            raise ValueError(
                f"Cannot make {sample_rate} Hz from a {clock_in} Hz {source}"
                + (
                    ". A bit clock below 512 kHz is under the PLL's input minimum"
                    if not mclk_freq and clock_in < 512_000
                    else ""
                )
            )
        p, r, j, d, ndac, mdac = solution

        # CAUTION: The datasheet specifies sequencing constraints around
        # changing the PLL and CODEC config. Specific ordering matters here.

        # 1. Ensure the DAC and the PLL are powered down
        self._set_bits(_DAC_SETUP1, 0x01, 7, 0b0)
        self._set_bits(_PLL_PROG_PR, 0x01, 7, 0b0)
        time.sleep(0.001)

        if use_pll and (p, r, j) != (0, 0, 0):
            # 2. Set the PLL clock scaling registers. Register 8 has to be
            # written immediately after register 7 for D to take effect.
            self._write_register(_PLL_PROG_PR, ((p & 0x07) << 4) | (r & 0x0F))
            self._write_register(_PLL_PROG_J, j & 0x3F)
            self._write_register(_PLL_PROG_D_MSB, (d >> 8) & 0x3F)
            self._write_register(_PLL_PROG_D_LSB, d & 0xFF)

            # 3. Set the mux for the PLL input clock (PLL_CLKIN), then power
            # the PLL up and give it time to lock
            self._set_bits(_CLOCK_MUX1, 0x03, 2, clock_mux_source)
            self._set_bits(_PLL_PROG_PR, 0x01, 7, 0b1)
            time.sleep(0.015)

            # 4. Route the PLL output to CODEC_CLKIN
            self._set_bits(_CLOCK_MUX1, 0x03, 0, 0b11)
        else:
            # No PLL: the input clock is CODEC_CLKIN as it stands
            self._set_bits(_CLOCK_MUX1, 0x03, 0, clock_mux_source)

        # 5. Set the data format
        self._set_codec_interface(FORMAT_I2S, data_len)

        # 6. Configure the codec clock dividers for oversampling and the DSP.
        # Register 14 has to be written immediately after register 13.
        self._write_register(_NDAC, 0x80 | (ndac & 0x7F))
        self._write_register(_MDAC, 0x80 | (mdac & 0x7F))
        self._write_register(_DOSR_MSB, (dosr >> 8) & 0x03)
        self._write_register(_DOSR_LSB, dosr & 0xFF)

        # 7. Power the DAC back up
        self._set_bits(_DAC_SETUP1, 0x01, 7, 0b1)

        return {
            "sample_rate": sample_rate,
            "bit_depth": bit_depth,
            "pll_clkin": clock_in if use_pll else 0,
            "codec_clkin": ndac * mdac * dosr * sample_rate,
            "p": p,
            "r": r,
            "j": j,
            "d": d,
            "ndac": ndac,
            "mdac": mdac,
            "dosr": dosr,
        }


class _Page1Registers(_PagedRegisterBase):
    """Page 1 registers containing the analog output stages and their routing."""

    def __init__(self, i2c_device):
        """Initialize Page 1 registers.

        :param i2c_device: The I2C device
        """
        super().__init__(i2c_device, 1)

    def _set_analog_reference_power(self, enable):
        """Power the analog reference up or down."""
        return self._set_bits(_REF_POR_LDO, 0x01, 4, 1 if enable else 0)

    def _configure_ldo(self, voltage=LDO_1_8V, pll_and_hp_enabled=True):
        """Configure the AVDD LDO output and the PLL/HP level shifters.

        The level shifters come out of reset powered *down*, which leaves the
        PLL unusable, so this has to be called before the PLL is programmed.
        """
        value = 0x04  # D2 is reserved and reads back as 1
        value |= (voltage & 0x03) << 4
        if not pll_and_hp_enabled:
            value |= 1 << 3
        self._write_register(_LDO_CTRL, value)

    def _set_common_mode(self, common_mode=CM_0_9V, hp_half_drive=False):
        """The full chip common mode voltage and headphone drive strength."""
        value = (1 if common_mode else 0) << 6
        if hp_half_drive:
            value |= 1 << 2
        self._write_register(_COMMON_MODE, value)

    def _set_output_drivers(self, hp_powered, ainl_enabled=False, ainr_enabled=False):
        """Power the headphone driver and enable the analog inputs."""
        value = (1 if hp_powered else 0) << 5
        if ainl_enabled:
            value |= 1 << 1
        if ainr_enabled:
            value |= 1
        self._write_register(_OUT_DRIVERS, value)

    def _get_output_drivers(self):
        """The current output driver and analog input configuration.

        :return: Dictionary with hp_powered, ainl_enabled, and ainr_enabled
        """
        reg_value = self._read_register(_OUT_DRIVERS)
        return {
            "hp_powered": bool(reg_value & (1 << 5)),
            "ainl_enabled": bool(reg_value & (1 << 1)),
            "ainr_enabled": bool(reg_value & 1),
        }

    def _set_dac_routing(self, dac_route=DAC_ROUTE_NONE, ainl_to_hp=False, ainr_to_hp=False):
        """Route the DAC and the analog inputs to the output drivers."""
        value = 0
        if dac_route == DAC_ROUTE_HP:
            value |= 1 << 3
        elif dac_route == DAC_ROUTE_MIXER:
            value |= 1 << 2
        if ainl_to_hp:
            value |= 1 << 1
        if ainr_to_hp:
            value |= 1
        self._write_register(_HP_ROUTING, value)

    def _get_dac_routing(self):
        """The current DAC and analog input routing.

        :return: Dictionary with dac_route, ainl_to_hp, and ainr_to_hp
        """
        reg_value = self._read_register(_HP_ROUTING)
        if reg_value & (1 << 3):
            dac_route = DAC_ROUTE_HP
        elif reg_value & (1 << 2):
            dac_route = DAC_ROUTE_MIXER
        else:
            dac_route = DAC_ROUTE_NONE
        return {
            "dac_route": dac_route,
            "ainl_to_hp": bool(reg_value & (1 << 1)),
            "ainr_to_hp": bool(reg_value & 1),
        }

    def _set_hp_driver(self, gain_db=0, mute=True):
        """Headphone driver gain and mute.

        :raises ValueError: If the gain is outside the -6 to 29 dB range
        """
        if not -6 <= gain_db <= 29:
            raise ValueError("Headphone gain must be in range -6 to 29 dB")
        value = int(gain_db) & 0x3F
        if mute:
            value |= 1 << 6
        self._write_register(_HP_DRIVER_GAIN, value)

    def _get_hp_driver(self):
        """The current headphone driver gain and mute state.

        :return: Dictionary with gain_db and mute
        """
        reg_value = self._read_register(_HP_DRIVER_GAIN)
        gain = reg_value & 0x3F
        return {"gain_db": gain - 64 if gain & 0x20 else gain, "mute": bool(reg_value & (1 << 6))}

    def _configure_hp_startup(self, routing_step=HP_ROUTING_STEP_0MS, power_up=0, resistance=0):
        """Headphone driver de-pop settings."""
        value = (routing_step & 0x03) << 6
        value |= (power_up & 0x0F) << 2
        value |= resistance & 0x03
        self._write_register(_HP_STARTUP, value)

    def _configure_overcurrent(self, debounce=OCP_DEBOUNCE_0MS, power_down=False):
        """Headphone over current protection settings."""
        value = 1 << 4  # D4 is reserved and has to be written as 1
        value |= (debounce & 0x07) << 1
        if power_down:
            value |= 1
        self._write_register(_HP_OCP, value)

    def _set_speaker_powered(self, enable):
        """Power the Class-D speaker amplifier up or down."""
        return self._set_bits(_SPK_AMP_CTRL, 0x01, 1, 1 if enable else 0)

    def _get_speaker_powered(self):
        """Check whether the Class-D speaker amplifier is powered up."""
        return bool(self._get_bits(_SPK_AMP_CTRL, 0x01, 1))

    def _configure_speaker_delay(self, delay=SPK_DELAY_512, bypass=False):
        """Speaker amplifier power-on delay settings."""
        value = (delay & 0x03) << 5
        if bypass:
            value |= 1 << 7
        self._write_register(_SPK_DELAY, value)

    def _set_playback_config(self, high_performance=False, ptm=PTM_P3P4):
        """DAC performance mode and PowerTune setting."""
        value = (1 if high_performance else 0) << 5
        value |= (ptm & 0x07) << 2
        self._write_register(_PLAYBACK_CFG, value)

    def _get_analog_gain_flags(self):
        """The analog gain status flags.

        :return: Dictionary with a flag per analog gain stage
        """
        reg_value = self._read_register(_ANALOG_GAIN_FLAG)
        return {
            "hp_gain_ok": bool(reg_value & (1 << 7)),
            "ain_mix_hp_gain_ok": bool(reg_value & (1 << 3)),
            "ainl_mixer_gain_ok": bool(reg_value & (1 << 1)),
            "ainr_mixer_gain_ok": bool(reg_value & 1),
        }


class TAS2505:
    """Driver for the TI TAS2505 Mono DAC with Class-D Speaker Amplifier."""

    def __init__(self, i2c: I2C, address: int = I2C_ADDR_DEFAULT) -> None:
        """Initialize the TAS2505.

        This resets the chip and powers up its analog reference. Both output
        amplifiers are left powered down and the DAC is left muted at minimum
        volume; set ``speaker_output`` or ``headphone_output`` to bring one up.

        **The clocks are deliberately left unprogrammed.** Only the caller
        knows what the board's bit clock is doing, so `configure_clocks` has to
        be called before an amplifier is brought up -- the quickstart setters
        raise if it has not been.

        :param i2c: The I2C bus the device is connected to
        :param address: The I2C device address (default is 0x18)
        :raises RuntimeError: If the chip does not answer the software reset
        """
        self._device: I2CDevice = I2CDevice(i2c, address)

        # Initialize register page classes
        self._page0: _Page0Registers = _Page0Registers(self._device)
        self._page1: _Page1Registers = _Page1Registers(self._device)
        # Zero means "no clocks programmed yet", not a real rate: the chip
        # cannot be told what its bit clock is until a caller says so.
        self._sample_rate: int = 0
        self._bit_depth: int = 0
        self._bclk_ratio: int = 0
        self._mclk_freq: int = 0  # Default to BCLK
        self._speaker_gain: int = 6
        self._clocks: Dict[str, int] = {}

        if not self.reset():
            raise RuntimeError("Failed to reset TAS2505")
        time.sleep(0.01)

        # Start muted at minimum volume so that bringing an amplifier up
        # cannot make a noise nobody asked for.
        self._page0._set_dac_volume(-63.5)
        self._page0._set_dac_setup2(mute=True)
        self._page0._set_dac_data_path(True, DAC_PATH_LEFT)

        # Datasheet section 3.4.12 step 3: analog blocks before output stages.
        # The LDO register also holds the PLL level shifter enable, which has
        # to be on before configure_clocks() programs the PLL.
        self._page1._configure_ldo(LDO_1_8V)
        self._page1._set_analog_reference_power(True)
        self._page1._set_common_mode(CM_0_9V)

        # No configure_clocks() here on purpose. Guessing a rate would program
        # the PLL to lock onto a bit clock that is not the one the board runs,
        # which is a wrong state to leave the chip in even though the first
        # real configure_clocks() call overwrites it.

    # Basic properties and methods

    def reset(self) -> bool:
        """Reset the device.

        :return: True if reset successful, False otherwise
        """
        return self._page0._reset()

    def _require_clocks(self, what: str) -> None:
        """Refuse to bring up an amplifier before the clocks are programmed.

        Out of reset the DAC has no idea what the board's bit clock is, so it
        would run from an unlocked PLL and play nothing. Failing here is a lot
        easier to debug than silence.
        """
        if not self._sample_rate:
            raise RuntimeError(f"call configure_clocks() before setting {what}")

    def configure_clocks(
        self,
        sample_rate: int,
        bit_depth: int = 16,
        mclk_freq: Optional[int] = None,
        bclk_ratio: Optional[int] = None,
        dosr: Optional[int] = None,
        ndac: Optional[int] = None,
        mdac: Optional[int] = None,
        use_pll: bool = True,
    ) -> Dict[str, int]:
        """Configure the TAS2505 clock settings.

        This works out the PLL multipliers and the clock dividers needed to
        make the requested sample rate out of the clock the board supplies,
        then programs them in the order the datasheet requires.

        :param sample_rate: The desired sample rate in Hz. Anything the
            constraints in the datasheet can be solved for will work; 8000,
            11025, 16000, 22050, 24000, 32000, 44100, and 48000 are all
            reachable from a suitable clock.
        :param bit_depth: The audio interface word length: 16, 20, 24, or 32.
            CircuitPython's I2S output always sends 16-bit stereo.
        :param mclk_freq: The MCLK frequency in Hz, or None (the
            default) to run the PLL from the I2S bit clock instead. The chip
            needs no MCLK, but a clean MCLK gives the PLL a better input than
            a jittery bit clock does, and it is the only option when the bit
            clock would fall below the PLL's 512 kHz input minimum -- which is
            what happens below 16 kHz at the usual 32x ratio.
        :param bclk_ratio: How many bit clocks there are per sample, when the
            bit clock is the PLL input. Defaults to ``bit_depth * 2``, which
            is what CircuitPython's 16-bit stereo I2S output produces. Pass
            the real ratio if some other device is generating the frame.
        :param dosr: The DAC oversampling ratio, or None to pick the largest
            one the datasheet's 2.8 MHz to 6.2 MHz window allows.
        :param ndac: Pin the NDAC divider instead of solving for it. Must be
            given together with ``mdac``.
        :param mdac: Pin the MDAC divider instead of solving for it. Must be
            given together with ``ndac``.
        :param use_pll: Whether to run the clock through the PLL. Set this to
            False when the input clock is already an exact multiple of what
            the DAC needs; the dividers alone then use less power. Not every
            clock can do this, and the call raises ValueError if this one
            cannot.
        :raises ValueError: If the requested sample rate cannot be made from
            the available clock, or the arguments are out of range
        :return: Dictionary of the clock settings that were programmed
        """
        if (ndac is None) != (mdac is None):
            raise ValueError("ndac and mdac have to be given together")

        mclk_freq = mclk_freq or 0
        bclk_ratio = bclk_ratio or bit_depth * 2

        clocks = self._page0._configure_clocks_for_sample_rate(
            mclk_freq, sample_rate, bit_depth, bclk_ratio, dosr, ndac, mdac, use_pll
        )

        # Commit only once the chip has actually been programmed. A call that
        # raises must not leave the object claiming a rate the DAC never got --
        # that is what the quickstart setters check before making a noise.
        self._sample_rate = sample_rate
        self._bit_depth = bit_depth
        self._mclk_freq = mclk_freq
        self._bclk_ratio = bclk_ratio
        self._clocks = clocks
        return clocks

    @property
    def clock_config(self) -> Dict[str, int]:
        """The clock settings the last ``configure_clocks`` call programmed.

        The keys are ``sample_rate``, ``bit_depth``, ``pll_clkin``,
        ``codec_clkin``, the PLL's ``p``, ``r``, ``j`` and ``d``, and the
        ``ndac``, ``mdac`` and ``dosr`` dividers.

        :getter: Return the settings
        """
        return self._clocks

    @property
    def sample_rate(self) -> int:
        """Configured sample rate in Hz, or 0 before `configure_clocks` runs.

        :getter: Return the sample rate in Hz
        """
        return self._sample_rate

    @property
    def bit_depth(self) -> int:
        """Configured bit depth, or 0 before `configure_clocks` runs.

        :getter: Return the bit depth
        """
        return self._bit_depth

    @property
    def mclk_freq(self) -> int:
        """Configured MCLK frequency in Hz, or 0 when the PLL runs from BCLK.

        :getter: Return the MCLK frequency in Hz
        """
        return self._mclk_freq

    # Audio interface

    @property
    def codec_interface(self) -> Dict[str, int]:
        """The audio interface format, word length, and clock directions.

        The keys are ``format`` (one of the FORMAT_* constants), ``data_len``
        (one of the DATA_LEN_* constants), ``bclk_out`` and ``wclk_out``.

        :getter: Return the settings
        """
        return self._page0._get_codec_interface()

    def set_codec_interface(
        self,
        format: int = FORMAT_I2S,
        data_len: int = DATA_LEN_16,
        bclk_out: bool = False,
        wclk_out: bool = False,
    ) -> None:
        """Audio interface settings.

        ``configure_clocks`` already sets I2S and the word length that goes
        with the bit depth it was given, so this is only needed for a
        different format or to make the chip drive the frame clocks.

        :param format: One of the FORMAT_* constants
        :param data_len: The word length, either as a bit count -- 16, 20, 24
            or 32, the same way `configure_clocks` takes it -- or as one of the
            DATA_LEN_* constants.
        :param bclk_out: True to drive BCLK, False to take it as an input
        :param wclk_out: True to drive WCLK, False to take it as an input
        :raises ValueError: if ``data_len`` is neither a supported bit count
            nor a DATA_LEN_* code.
        """
        self._page0._set_codec_interface(format, _data_len_code(data_len), bclk_out, wclk_out)

    @property
    def data_offset(self) -> int:
        """Data offset from the frame edge, in bit clocks.

        :getter: Return the offset
        :setter: Set the offset (0-255)
        """
        return self._page0._read_register(_DATA_OFFSET)

    @data_offset.setter
    def data_offset(self, offset: int) -> None:
        self._page0._write_register(_DATA_OFFSET, offset & 0xFF)

    @property
    def bclk_inverted(self) -> bool:
        """Whether the bit clock polarity is inverted.

        :getter: Return the polarity
        :setter: Set the polarity
        """
        return bool(self._page0._get_bits(_CODEC_IF_CTRL2, 0x01, 3))

    @bclk_inverted.setter
    def bclk_inverted(self, inverted: bool) -> None:
        self._page0._set_bits(_CODEC_IF_CTRL2, 0x01, 3, 1 if inverted else 0)

    # DAC

    @property
    def dac_power(self) -> bool:
        """The DAC channel power state.

        :getter: Return True if the DAC is powered up
        :setter: Power the DAC up or down
        """
        return self._page0._get_dac_data_path()["dac_on"]

    @dac_power.setter
    def dac_power(self, enabled: bool) -> None:
        current = self._page0._get_dac_data_path()
        self._page0._set_dac_data_path(enabled, current["path"], current["volume_step"])

    @property
    def dac_path(self) -> int:
        """Which audio interface channel the mono DAC plays.

        One of the DAC_PATH_* constants.

        :getter: Return the data path
        :setter: Set the data path
        :raises ValueError: If set to something that is not a DAC_PATH_* constant
        """
        return self._page0._get_dac_data_path()["path"]

    @dac_path.setter
    def dac_path(self, path: int) -> None:
        if path not in {DAC_PATH_OFF, DAC_PATH_LEFT, DAC_PATH_RIGHT, DAC_PATH_MONO_MIX}:
            raise ValueError(f"Invalid DAC path: {path}. Must be a DAC_PATH_* constant.")
        current = self._page0._get_dac_data_path()
        self._page0._set_dac_data_path(current["dac_on"], path, current["volume_step"])

    @property
    def dac_volume_step(self) -> int:
        """The DAC volume control's soft stepping rate.

        One of the VOLUME_STEP_* constants.

        :getter: Return the soft stepping rate
        :setter: Set the soft stepping rate
        :raises ValueError: If set to something that is not a VOLUME_STEP_* constant
        """
        return self._page0._get_dac_data_path()["volume_step"]

    @dac_volume_step.setter
    def dac_volume_step(self, volume_step: int) -> None:
        if volume_step not in {
            VOLUME_STEP_1SAMPLE,
            VOLUME_STEP_2SAMPLE,
            VOLUME_STEP_DISABLED,
        }:
            raise ValueError(
                f"Invalid volume step: {volume_step}. Must be a VOLUME_STEP_* constant."
            )
        current = self._page0._get_dac_data_path()
        self._page0._set_dac_data_path(current["dac_on"], current["path"], volume_step)

    @property
    def dac_volume(self) -> float:
        """The DAC's digital volume in dB.

        Range is -63.5 dB to +24 dB in 0.5 dB steps. This is the main volume
        control: it sits ahead of both output signal chains, so it moves the
        speaker and the headphone output together.

        Keep this below 0 dB unless you know the material has headroom;
        positive digital gain clips.

        :getter: Return the volume in dB
        :setter: Set the volume in dB
        :raises ValueError: If set outside the -63.5 to 24 dB range
        """
        return self._page0._get_dac_volume()

    @dac_volume.setter
    def dac_volume(self, db: float) -> None:
        self._page0._set_dac_volume(db)

    @property
    def dac_mute(self) -> bool:
        """The DAC's digital mute.

        :getter: Return True if the DAC is muted
        :setter: Mute or unmute the DAC
        """
        return self._page0._get_dac_setup2()["mute"]

    @dac_mute.setter
    def dac_mute(self, mute: bool) -> None:
        self._page0._set_dac_setup2(mute, self._page0._get_dac_setup2()["auto_mute"])

    @property
    def auto_mute(self) -> int:
        """How long a DC input mutes the DAC for.

        0 disables auto mute; 1 through 7 mute after 100, 200, 400, 800, 1600,
        3200, or 6400 consecutive DC samples.

        :getter: Return the setting
        :setter: Set the setting (0-7)
        :raises ValueError: If set outside the 0 to 7 range
        """
        return self._page0._get_dac_setup2()["auto_mute"]

    @auto_mute.setter
    def auto_mute(self, setting: int) -> None:
        if not 0 <= setting <= 7:
            raise ValueError("Auto mute setting must be in range 0 to 7")
        self._page0._set_dac_setup2(self._page0._get_dac_setup2()["mute"], setting)

    @property
    def processing_block(self) -> int:
        """The DAC's signal processing block.

        One of the PRB_P* constants. PRB_P3 is the default and covers up to
        96 kHz; PRB_P1 and PRB_P2 use interpolation filter A, which the
        datasheet prefers for 48 kHz high performance operation.

        :getter: Return the processing block
        :setter: Set the processing block
        :raises ValueError: If set to something that is not a PRB_P* constant
        """
        return self._page0._get_bits(_DAC_PRB, 0x1F, 0)

    @processing_block.setter
    def processing_block(self, block: int) -> None:
        if block not in {PRB_P1, PRB_P2, PRB_P3}:
            raise ValueError(f"Invalid processing block: {block}. Must be a PRB_P* constant.")
        self._page0._set_bits(_DAC_PRB, 0x1F, 0, block)

    def set_playback_config(self, high_performance: bool = False, ptm: int = PTM_P3P4) -> None:
        """The DAC's performance mode and PowerTune setting.

        :param high_performance: True for high performance mode, False for low power
        :param ptm: One of the PTM_* constants
        :raises ValueError: If ptm is not a PTM_* constant
        """
        if ptm not in {PTM_P3P4, PTM_P2, PTM_P1}:
            raise ValueError(f"Invalid PowerTune mode: {ptm}. Must be a PTM_* constant.")
        self._page1._set_playback_config(high_performance, ptm)

    @property
    def dac_soft_step_disabled(self) -> bool:
        """Whether soft stepping of the analog PGAs is disabled.

        :getter: Return True if soft stepping is disabled
        :setter: Disable or enable soft stepping
        """
        return bool(self._page1._get_bits(_DAC_PGA_CTRL, 0x01, 7))

    @dac_soft_step_disabled.setter
    def dac_soft_step_disabled(self, disabled: bool) -> None:
        self._page1._set_bits(_DAC_PGA_CTRL, 0x01, 7, 1 if disabled else 0)

    # Routing

    @property
    def dac_route(self) -> int:
        """Where the DAC output goes.

        One of the DAC_ROUTE_* constants. The speaker amplifier is fed from
        Mixer P, so it needs DAC_ROUTE_MIXER; the headphone driver can take
        either, but only DAC_ROUTE_MIXER passes through the attenuator that
        ``headphone_volume`` controls.

        :getter: Return the routing
        :setter: Set the routing
        :raises ValueError: If set to something that is not a DAC_ROUTE_* constant
        """
        return self._page1._get_dac_routing()["dac_route"]

    @dac_route.setter
    def dac_route(self, route: int) -> None:
        if route not in {DAC_ROUTE_NONE, DAC_ROUTE_MIXER, DAC_ROUTE_HP}:
            raise ValueError(f"Invalid DAC route: {route}. Must be a DAC_ROUTE_* constant.")
        current = self._page1._get_dac_routing()
        self._page1._set_dac_routing(route, current["ainl_to_hp"], current["ainr_to_hp"])

    def set_analog_input_routing(self, ainl_to_hp: bool = False, ainr_to_hp: bool = False) -> None:
        """Route the analog inputs to the headphone driver.

        :param ainl_to_hp: True to route the AINL attenuator to the headphone driver
        :param ainr_to_hp: True to route the AINR attenuator to the headphone driver
        """
        self._page1._set_dac_routing(
            self._page1._get_dac_routing()["dac_route"], ainl_to_hp, ainr_to_hp
        )

    def set_analog_inputs(self, ainl_enabled: bool = False, ainr_enabled: bool = False) -> None:
        """Enable or disable the analog inputs.

        :param ainl_enabled: True to enable the AINL input
        :param ainr_enabled: True to enable the AINR input
        """
        self._page1._set_output_drivers(
            self._page1._get_output_drivers()["hp_powered"], ainl_enabled, ainr_enabled
        )

    @property
    def ain_left_volume(self) -> float:
        """The AINL input attenuator in dB.

        Range is 0 (loud) to -72.3 (very soft).

        :getter: Return the volume
        :setter: Set the volume
        """
        return _volume_code_to_db(self._page1._read_register(_AINL_VOL) & 0x7F)

    @ain_left_volume.setter
    def ain_left_volume(self, db: float) -> None:
        forced = self._page1._read_register(_AINL_VOL) & 0x80
        self._page1._write_register(_AINL_VOL, forced | _db_to_volume_code(db))

    @property
    def ain_right_volume(self) -> float:
        """The AINR input attenuator in dB.

        Range is 0 (loud) to -72.3 (very soft).

        :getter: Return the volume
        :setter: Set the volume
        """
        return _volume_code_to_db(self._page1._read_register(_AINR_VOL) & 0x7F)

    @ain_right_volume.setter
    def ain_right_volume(self, db: float) -> None:
        forced = self._page1._read_register(_AINR_VOL) & 0x80
        self._page1._write_register(_AINR_VOL, forced | _db_to_volume_code(db))

    @property
    def mixer_forced_enable(self) -> bool:
        """Whether Mixer P and Mixer M are forced on.

        The mixers normally follow the DAC. Set this to route an analog input
        through them to an output driver while the DAC is powered down.

        :getter: Return True if the mixers are forced on
        :setter: Force the mixers on or let them follow the DAC
        """
        return bool(self._page1._get_bits(_AINL_VOL, 0x01, 7))

    @mixer_forced_enable.setter
    def mixer_forced_enable(self, forced: bool) -> None:
        self._page1._set_bits(_AINL_VOL, 0x01, 7, 1 if forced else 0)

    # Speaker output

    @property
    def speaker_output(self) -> bool:
        """Speaker output helper with quickstart default settings.

        If you set this property to True, the setter will set defaults that
        are intended for a quiet-ish listening level on a small 8-Ohm speaker:

        * dac_volume = -20
        * speaker_volume = -10
        * speaker_gain = 6

        If you set this to False, the setter turns the Class-D amplifier off.

        :getter: Return True if the Class-D amplifier is powered up
        :setter: **This sets several properties to prepare for speaker use**.
            Changed properties include the DAC's power, path, volume and mute,
            the DAC routing, and the speaker's volume, gain and mute.
        :raises RuntimeError: when set True before `configure_clocks` has run.
        """
        return self._page1._get_speaker_powered()

    @speaker_output.setter
    def speaker_output(self, enabled: bool) -> None:
        if enabled:
            self._require_clocks("speaker_output")
            self.dac_power = True
            self.dac_path = DAC_PATH_LEFT
            self.dac_volume = -20
            self.dac_route = DAC_ROUTE_MIXER
            self.speaker_volume = -10
            self.speaker_gain = 6
            self._page1._set_speaker_powered(True)
            self.dac_mute = False
        else:
            self._page1._set_speaker_powered(False)

    @property
    def speaker_power(self) -> bool:
        """The Class-D speaker amplifier's power state.

        Note that the amplifier powers itself down on a short circuit, so this
        can read back False without anything having set it that way. Writing
        True again is how the datasheet says to restart it once the short is
        gone -- but do not do that more than about three times, because a
        still-shorted output will overheat.

        :getter: Return True if the amplifier is powered up
        :setter: Power the amplifier up or down
        """
        return self._page1._get_speaker_powered()

    @speaker_power.setter
    def speaker_power(self, enabled: bool) -> None:
        self._page1._set_speaker_powered(enabled)

    @property
    def speaker_volume(self) -> float:
        """The speaker's analog volume in dB.

        Range is 0 (loud) to -72.3 (very soft). This is the attenuator between
        Mixer P and the Class-D amplifier -- datasheet Page 1 / Register 46.

        Note that ``dac_volume``, ``speaker_gain`` and ``speaker_mute`` also
        affect how loud the speaker is.

        :getter: Return the volume
        :setter: Set the volume
        """
        return _volume_code_to_db(self._page1._read_register(_SPK_VOL) & 0x7F)

    @speaker_volume.setter
    def speaker_volume(self, db: float) -> None:
        self._page1._write_register(_SPK_VOL, _db_to_volume_code(db))

    @property
    def speaker_gain(self) -> int:
        """The Class-D amplifier's gain in dB.

        One of 6, 12, 18, 24, or 32 dB. Reads back as 0 while the amplifier is
        muted, since mute and gain share a register field.

        :getter: Return the gain in dB
        :setter: Set the gain in dB
        :raises ValueError: If set to anything other than 6, 12, 18, 24, or 32
        """
        gain = self._page1._get_bits(_SPK_DRIVER, 0x07, 4)
        return {
            SPK_GAIN_MUTE: 0,
            SPK_GAIN_6DB: 6,
            SPK_GAIN_12DB: 12,
            SPK_GAIN_18DB: 18,
            SPK_GAIN_24DB: 24,
            SPK_GAIN_32DB: 32,
        }.get(gain, 0)

    @speaker_gain.setter
    def speaker_gain(self, gain_db: int) -> None:
        codes = {
            6: SPK_GAIN_6DB,
            12: SPK_GAIN_12DB,
            18: SPK_GAIN_18DB,
            24: SPK_GAIN_24DB,
            32: SPK_GAIN_32DB,
        }
        if gain_db not in codes:
            raise ValueError(f"Invalid speaker gain: {gain_db}. Must be 6, 12, 18, 24, or 32.")
        self._speaker_gain = gain_db
        self._page1._set_bits(_SPK_DRIVER, 0x07, 4, codes[gain_db])

    @property
    def speaker_mute(self) -> bool:
        """The Class-D amplifier's mute.

        The amplifier mutes by having its gain set to zero, so unmuting
        restores whatever ``speaker_gain`` was last set to, or 6 dB if it has
        never been set.

        :getter: Return True if the amplifier is muted
        :setter: Mute or unmute the amplifier
        """
        return self._page1._get_bits(_SPK_DRIVER, 0x07, 4) == SPK_GAIN_MUTE

    @speaker_mute.setter
    def speaker_mute(self, mute: bool) -> None:
        if mute:
            self._page1._set_bits(_SPK_DRIVER, 0x07, 4, SPK_GAIN_MUTE)
        else:
            self.speaker_gain = self._speaker_gain

    def configure_speaker_delay(self, delay: int = SPK_DELAY_512, bypass: bool = False) -> None:
        """The Class-D amplifier's power-on delay.

        :param delay: One of the SPK_DELAY_* constants
        :param bypass: True to bypass the power-on delay block entirely
        :raises ValueError: If delay is not a SPK_DELAY_* constant
        """
        if delay not in {SPK_DELAY_512, SPK_DELAY_1024, SPK_DELAY_256, SPK_DELAY_16}:
            raise ValueError(f"Invalid speaker delay: {delay}. Must be a SPK_DELAY_* constant.")
        self._page1._configure_speaker_delay(delay, bypass)

    # Headphone output

    @property
    def headphone_output(self) -> bool:
        """Headphone output helper with quickstart default settings.

        If you set this property to True, the setter will set defaults that
        are intended for a quiet listening level on sensitive low impedance
        earbuds:

        * dac_volume = -20
        * headphone_volume = -30.1
        * headphone_gain = 0

        If you set this to False, the setter powers the headphone driver down.

        :getter: Return True if the headphone driver is powered up
        :setter: **This sets several properties to prepare for headphone
            use**. Changed properties include the DAC's power, path, volume
            and mute, the DAC routing, and the headphone driver's volume, gain
            and mute.
        :raises RuntimeError: when set True before `configure_clocks` has run.
        """
        return self._page1._get_output_drivers()["hp_powered"]

    @headphone_output.setter
    def headphone_output(self, enabled: bool) -> None:
        if enabled:
            self._require_clocks("headphone_output")
            self.dac_power = True
            self.dac_path = DAC_PATH_LEFT
            self.dac_volume = -20
            # NOTE: DAC_ROUTE_HP would send the DAC straight into the
            # headphone amp, bypassing the attenuator. That saves a little
            # power, but for low impedance headphones it helps to have plenty
            # of attenuation ahead of the amp; otherwise the only volume
            # control left is dac_volume, down near the bottom of its range.
            self.dac_route = DAC_ROUTE_MIXER
            self.headphone_volume = -30.1
            self.headphone_gain = 0
            current = self._page1._get_output_drivers()
            self._page1._set_output_drivers(True, current["ainl_enabled"], current["ainr_enabled"])
            self.headphone_mute = False
            self.dac_mute = False
        else:
            current = self._page1._get_output_drivers()
            self._page1._set_output_drivers(False, current["ainl_enabled"], current["ainr_enabled"])

    @property
    def headphone_power(self) -> bool:
        """The headphone driver's power state.

        :getter: Return True if the headphone driver is powered up
        :setter: Power the headphone driver up or down
        """
        return self._page1._get_output_drivers()["hp_powered"]

    @headphone_power.setter
    def headphone_power(self, enabled: bool) -> None:
        current = self._page1._get_output_drivers()
        self._page1._set_output_drivers(enabled, current["ainl_enabled"], current["ainr_enabled"])

    @property
    def headphone_volume(self) -> float:
        """The headphone output's analog volume in dB.

        Range is 0 (loud) to -72.3 (very soft). This is the attenuator between
        Mixer P and the headphone driver -- datasheet Page 1 / Register 22 --
        so it only does anything while ``dac_route`` is DAC_ROUTE_MIXER.

        Note that ``dac_volume``, ``headphone_gain`` and ``headphone_mute``
        also affect how loud the headphone output is.

        :getter: Return the volume
        :setter: Set the volume
        """
        return _volume_code_to_db(self._page1._read_register(_HP_VOL) & 0x7F)

    @headphone_volume.setter
    def headphone_volume(self, db: float) -> None:
        self._page1._write_register(_HP_VOL, _db_to_volume_code(db))

    @property
    def headphone_gain(self) -> int:
        """The headphone driver's gain in dB.

        Range is -6 dB to +29 dB in 1 dB steps.

        **CAUTION**: this is the last stage before the jack. Anything much
        above 0 dB is loud enough to hurt on sensitive headphones.

        :getter: Return the gain in dB
        :setter: Set the gain in dB
        :raises ValueError: If set outside the -6 to 29 dB range
        """
        return self._page1._get_hp_driver()["gain_db"]

    @headphone_gain.setter
    def headphone_gain(self, gain_db: int) -> None:
        self._page1._set_hp_driver(gain_db, self._page1._get_hp_driver()["mute"])

    @property
    def headphone_mute(self) -> bool:
        """The headphone driver's mute.

        :getter: Return True if the headphone driver is muted
        :setter: Mute or unmute the headphone driver
        """
        return self._page1._get_hp_driver()["mute"]

    @headphone_mute.setter
    def headphone_mute(self, mute: bool) -> None:
        self._page1._set_hp_driver(self._page1._get_hp_driver()["gain_db"], mute)

    def configure_headphone_startup(
        self, routing_step: int = HP_ROUTING_STEP_0MS, power_up: int = 0, resistance: int = 0
    ) -> None:
        """Headphone driver de-pop settings.

        Ramping the driver up slowly is what keeps plugging in and powering up
        from making a pop. The time constants assume the datasheet's 47 uF
        output coupling capacitor.

        :param routing_step: One of the HP_ROUTING_STEP_* constants
        :param power_up: Slow power up setting: 0 disables it, 1 through 15
            ramp over 0.5 to 32 time constants
        :param resistance: Charging resistance: 0 for 25k, 1 for 6k, 2 for 2k
        :raises ValueError: If any argument is out of range
        """
        if not 0 <= power_up <= 15:
            raise ValueError("Headphone power up setting must be in range 0 to 15")
        if not 0 <= resistance <= 2:
            raise ValueError("Headphone charging resistance must be 0, 1, or 2")
        self._page1._configure_hp_startup(routing_step, power_up, resistance)

    def configure_overcurrent_protection(
        self, debounce: int = OCP_DEBOUNCE_0MS, power_down: bool = False
    ) -> None:
        """Headphone over current protection settings.

        :param debounce: One of the OCP_DEBOUNCE_* constants
        :param power_down: True to power the driver down on an over current
            condition, False to limit its output current instead
        """
        self._page1._configure_overcurrent(debounce, power_down)

    @property
    def headphone_overcurrent(self) -> bool:
        """Whether an over current condition is present on HPOUT right now.

        :getter: Return True if HPOUT is drawing too much current
        """
        return bool(self._page0._get_bits(_INT_FLAG2, 0x01, 7))

    # Analog reference and supplies

    @property
    def analog_reference_power(self) -> bool:
        """The analog reference's power state.

        Everything analog needs this. It is powered up during ``__init__``.

        :getter: Return True if the analog reference is powered up
        :setter: Power the analog reference up or down
        """
        return bool(self._page1._get_bits(_REF_POR_LDO, 0x01, 4))

    @analog_reference_power.setter
    def analog_reference_power(self, enabled: bool) -> None:
        self._page1._set_analog_reference_power(enabled)

    def configure_ldo(self, voltage: int = LDO_1_8V, pll_and_hp_enabled: bool = True) -> None:
        """AVDD LDO settings.

        :param voltage: One of the LDO_* constants
        :param pll_and_hp_enabled: True to power up the PLL and headphone
            level shifters. They come out of reset powered down, so the PLL
            does not work until this has been called with it True -- which
            ``__init__`` does.
        :raises ValueError: If voltage is not an LDO_* constant
        """
        if voltage not in {LDO_1_8V, LDO_1_6V, LDO_1_7V, LDO_1_5V}:
            raise ValueError(f"Invalid LDO voltage: {voltage}. Must be an LDO_* constant.")
        self._page1._configure_ldo(voltage, pll_and_hp_enabled)

    @property
    def ldo_shorted(self) -> bool:
        """Whether the AVDD LDO has detected a short circuit.

        :getter: Return True if a short circuit was detected
        """
        return bool(self._page1._get_bits(_LDO_CTRL, 0x01, 1))

    def set_common_mode(self, common_mode: int = CM_0_9V, hp_half_drive: bool = False) -> None:
        """The full chip common mode voltage.

        :param common_mode: CM_0_9V or CM_0_75V. Which one is right depends on
            the analog supply and the output swing the application needs.
        :param hp_half_drive: True to halve the headphone driver's drive ability
        :raises ValueError: If common_mode is not a CM_* constant
        """
        if common_mode not in {CM_0_9V, CM_0_75V}:
            raise ValueError(f"Invalid common mode: {common_mode}. Must be a CM_* constant.")
        self._page1._set_common_mode(common_mode, hp_half_drive)

    def set_reference_powerup_delay(self, setting: int = 0) -> None:
        """How long the analog reference takes to power up.

        :param setting: 0 to 3 for a slow, 40 ms, 80 ms or 120 ms power up
            when the analog blocks come up; 4 to 7 for the same times but
            forcing the reference up immediately
        :raises ValueError: If setting is outside the 0 to 7 range
        """
        if not 0 <= setting <= 7:
            raise ValueError("Reference power up setting must be in range 0 to 7")
        self._page1._set_bits(_REF_PWRUP_DELAY, 0x07, 0, setting)

    # Status flags and interrupts

    @property
    def flags(self) -> Dict[str, bool]:
        """The DAC and output driver status flags.

        The keys are ``dac_powered``, ``hp_powered`` and ``dac_pga_gain_ok``.

        :getter: Return the flags
        """
        return self._page0._get_dac_flags()

    @property
    def analog_gain_flags(self) -> Dict[str, bool]:
        """Whether each analog gain stage has finished soft stepping.

        The keys are ``hp_gain_ok``, ``ain_mix_hp_gain_ok``,
        ``ainl_mixer_gain_ok`` and ``ainr_mixer_gain_ok``. Each one is True
        once the gain actually applied has caught up with the gain programmed.

        :getter: Return the flags
        """
        return self._page1._get_analog_gain_flags()

    @property
    def dac_overflow(self) -> bool:
        """Whether the DAC is overflowing right now.

        An overflow means the digital signal chain is clipping; turn
        ``dac_volume`` down.

        :getter: Return True if an overflow is present
        """
        return bool(self._page0._get_bits(_INT_FLAG1, 0x01, 7))

    @property
    def sticky_flags(self) -> Dict[str, bool]:
        """The sticky flags, which latch until they are read.

        The keys are ``dac_overflow`` and ``headphone_overcurrent``. Reading
        this property clears both.

        :getter: Return the flags
        """
        return {
            "dac_overflow": bool(self._page0._get_bits(_STICKY_FLAG1, 0x01, 7)),
            "headphone_overcurrent": bool(self._page0._get_bits(_STICKY_FLAG2, 0x01, 7)),
        }

    def int1_source(self, over_current: bool = False, multiple_pulse: bool = False) -> None:
        """The INT1 interrupt source.

        :param over_current: True to interrupt on a headphone over current condition
        :param multiple_pulse: True for a pulse train until a flag register is
            read, False for a single 2 ms pulse
        """
        self._page0._set_int_source(_INT1_CTRL, over_current, multiple_pulse)

    def int2_source(self, over_current: bool = False, multiple_pulse: bool = False) -> None:
        """The INT2 interrupt source.

        :param over_current: True to interrupt on a headphone over current condition
        :param multiple_pulse: True for a pulse train until a flag register is
            read, False for a single 2 ms pulse
        """
        self._page0._set_int_source(_INT2_CTRL, over_current, multiple_pulse)
