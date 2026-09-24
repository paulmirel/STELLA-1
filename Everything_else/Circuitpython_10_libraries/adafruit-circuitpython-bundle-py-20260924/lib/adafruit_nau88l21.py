# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_nau88l21`
================================================================================

CircuitPython driver for the Nuvoton NAU88L21 audio codec


* Author(s): Tim Cocks

Implementation Notes
--------------------

**Hardware:**

* The NAU88L21 is a stereo codec: a DAC driving a headphone amplifier, and an
  ADC fed by a differential microphone front-end PGA.

* Registers are **16-bit addresses with 16-bit big-endian data**. Every
  descriptor in this module therefore has to be built with ``register_width=2``
  and ``lsb_first=False``;

* **CAUTION**: the 3.5mm amplifier can drive sensitive earbuds to levels
  that could damage your hearing. Teenage Engineering documentation states:
  TING is designed to connect to RIDDIM or any sound system, not directly to headphones.
  the maximum output is 2 VRMS. This can be very loud when connected directly to headphones.

**Clocking, and why it needs I2S running first**

CircuitPythons rp2 I2S generates BCLK and WS, the codec runs from that external
clock (what the datasheet calls slave mode). Its SYSCLK comes from the internal
FLL locked to the incoming bit clock, which means **BCLK must already be running
before** `NAU88L21.configure_clocks` is called, otherwise the FLL has nothing to
lock to. The correct order is::

    i2s = audiobusio.I2SOut(bit_clock, word_select, data)
    i2s.play(some_looping_sample, loop=True)   # BCLK starts here
    codec.configure_clocks()                   # now the FLL can lock

The driver does not own the ``I2SOut``/``I2SIn`` object; you construct it and
keep it.

**Full duplex**

The internal clock mode object has to exist before the external clock mode one
has anything to sync to, and the codec's FLL has to have BCLK before it can lock::

    i2s = audiobusio.I2SOut(bit_clock, word_select, data_out)
    codec.configure_clocks()
    codec.headphone_output = True
    codec.configure_microphone_input()
    mic = audioi2sin.I2SIn(bit_clock, word_select, data_in, sample_rate=48000,
                           bit_depth=16, external_clock=True,
                           left_justified=False)

**Input left_justified**

``I2SIn(left_justified=...)`` must match the framing the codec was configured
for: leave it ``False`` for the default Philips framing, and set it ``True``
only when `NAU88L21.configure_clocks` was called with ``left_justified=True``.
The codec drives ADCDAT in the same framing it expects on DACDAT, so the whole
bus, ``I2SOut``, codec, and ``I2SIn`` takes one setting.

**Effect chains order**

**Wire effect chains from the output backwards.** ``I2SOut.play()`` restarts
the internal clock mode state machine, which knocks an ``external_clock=True``
``I2SIn`` off the frame it had locked to; that ``I2SIn`` is re-synced only by a
``play()`` call made *on the mic*, and effects do not propagate that down to
their own source.
So the call that hands over the mic must come last::

    i2s.play(effect)      # first
    effect.play(mic)      # last

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
* Adafruit's Register library: https://github.com/adafruit/Adafruit_CircuitPython_Register
"""

import math
import time

from adafruit_bus_device.i2c_device import I2CDevice
from adafruit_register.register_accessor import I2CRegisterAccessor
from adafruit_register.register_bit import RWBit
from adafruit_register.register_bits import RWBits
from adafruit_register.register_struct import ROUnaryStruct, Struct, UnaryStruct

try:
    from typing import Optional, Sequence, Tuple

    from busio import I2C
except ImportError:
    pass

__version__ = "1.0.1"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_NAU88L21.git"

_DEFAULT_ADDRESS = 0x1B
_CHIP_ID = 0x1B23

# Register addresses. Names follow the datasheet and the Nuvoton ALSA driver.
_REG_RESET = 0x00
_REG_ENA_CTRL = 0x01
_REG_CLK_DIVIDER = 0x03
_REG_FLL1 = 0x04
_REG_FLL3 = 0x06
_REG_FLL4 = 0x07
_REG_FLL5 = 0x08
_REG_FLL6 = 0x09
_REG_FLL7 = 0x0A
_REG_FLL8 = 0x0B
_REG_JACK_DET_CTRL = 0x0D
_REG_I2S_PCM_CTRL1 = 0x1C
_REG_I2S_PCM_CTRL2 = 0x1D
_REG_BIQ0_COF1 = 0x21
_REG_BIQ0_COF10 = 0x2A
_REG_ADC_RATE = 0x2B
_REG_DAC_CTRL1 = 0x2C
_REG_ADC_DGAIN_CTRL = 0x30
_REG_MUTE_CTRL = 0x31
_REG_HSVOL_CTRL = 0x32
_REG_DACR_CTRL = 0x34
_REG_ADC_DGAIN_CTRL1 = 0x35
_REG_ADC_DRC_KNEE_IP12 = 0x36
_REG_ADC_DRC_KNEE_IP34 = 0x37
_REG_ADC_DRC_SLOPES = 0x38
_REG_ADC_DRC_ATKDCY = 0x39
_REG_DAC_DRC_KNEE_IP12 = 0x3A
_REG_DAC_DRC_KNEE_IP34 = 0x3B
_REG_DAC_DRC_SLOPES = 0x3C
_REG_DAC_DRC_ATKDCY = 0x3D
_REG_BIQ1_COF1 = 0x41
_REG_BIQ1_COF10 = 0x4A
_REG_CLASSG_CTRL = 0x4B
_REG_I2C_DEVICE_ID = 0x58
_REG_BIAS_ADJ = 0x66
_REG_ANALOG_CONTROL_2 = 0x6A
_REG_ANALOG_ADC_1 = 0x71
_REG_ANALOG_ADC_2 = 0x72
_REG_RDAC = 0x73
_REG_MIC_BIAS = 0x74
_REG_BOOST = 0x76
_REG_FEPGA = 0x77
_REG_PGA_GAIN = 0x7E
_REG_POWER_UP_CONTROL = 0x7F
_REG_CHARGE_PUMP = 0x80

# R1C[3:2] is the data length, R1C[1:0] the data format.
_I2S_DL = {16: 0x0, 20: 0x1, 24: 0x2, 32: 0x3}
_I2S_DF_LEFT = 0x1
_I2S_DF_I2S = 0x2

# One FLL setting covers every sample rate. FREF is BCLK, and CircuitPython
# always clocks 32 BCLK per frame, so FREF = 32*fs at any rate; multiplying it
# by a fixed FLL_INTEGER with a fixed MCLK_SRC divider makes MCLK track 256*fs
# automatically. FLL_FRAC stays 0, so the sigma-delta modulator and the loop
# filter stay off.
#
# The per-rate "divider families" derived from nau8821_calc_fll_param() (which
# keep FDCO inside 90-100 MHz for a fixed external MCLK) are *wrong* here and
# measurably worse: rewriting MCLK_SRC per rate breaks the 256*fs relationship
# the fixed multiplier gives you for free. Measured on hardware at 8/16/32 kHz,
# those values raise the distortion floor, and at 8 kHz they put a spur within
# 1.3 dB of the fundamental.
_MCLK_SRC = 0x3  # R03[3:0], MCLK divide by 4
_FLL_INTEGER = 64  # R06[9:0]
_FLL_RATIO = 0x01  # R04[3:0]

# R03 with SYSCLK still taken from the MCLK pin, and CLK_ADC_SRC / CLK_DAC_SRC
# both dividing by 2. This is also the whole of the MCLK-pin mode's setup, and
# R03's reset default.
_CLK_DIVIDER_MCLK = 0x0050

# R34/R35 digital volume codes. 0.5 dB per step around 0xCF = 0 dB; 0xFF is the
# +24 dB top of the scale and 0x4B the -66 dB bottom. Codes below 0x4B are
# either reserved (0x0F-0x4A) or mute (0x00-0x0E), so the conversions clip at
# 0x4B rather than running the line off the end of the table.
_DGAIN_0DB = 0xCF
_DGAIN_MIN = 0x4B
_DGAIN_MAX = 0xFF
_DGAIN_MIN_DB = (_DGAIN_MIN - _DGAIN_0DB) * 0.5  # -66.0
_DGAIN_MAX_DB = (_DGAIN_MAX - _DGAIN_0DB) * 0.5  # +24.0

# R32 headphone analog volume: two bits per channel, 3 dB per step.
_HP_VOL_STEP_DB = 3.0
_HP_VOL_MAX_CODE = 3  # -9 dB

# R7F bits [5:0]: PUP_INTEG_L/R, PUP_DRV_INSTG_L/R and PUP_MAIN_DRV_L/R, i.e.
# the whole headphone output driver chain. Bits [15:14] are PUP_PGA_L/R, the
# microphone PGAs
_HP_DRIVERS_ON = 0x3F
_MIC_PGAS_ON = 0x3

# R7E front-end PGA gain codes, one per channel: 1 dB per step with 0x00 at
# -1 dB and 0x25 at the +36 dB top of the scale. Codes above 0x25 are reserved.
_PGA_MIN_DB = -1.0
_PGA_MAX_DB = 36.0
_PGA_MAX_CODE = 0x25

# The microphone bias and the ADC's analog front end need about this long to
# settle.
_MIC_SETTLE_SECONDS = 0.4

# Quickstart levels for ``headphone_output = True``. Deliberately quiet: the
# headphone amp can drive sensitive earbuds to painful levels. The analog stage
# only reaches -9 dB, so most of the attenuation has to come from the DAC.
_QUICKSTART_DAC_VOLUME_DB = -20.0
_QUICKSTART_HP_VOLUME_DB = -9.0

# Quickstart level for ``microphone_input = True``.
_QUICKSTART_MIC_GAIN_DB = 36.0

# Biquad coefficients are 19-bit two's complement in S2.16 format: a sign bit,
# two integer bits and sixteen fractional bits. Each one occupies a *pair* of
# registers, low 16 bits then high 3 bits, so a filter is ten registers.
_BIQ_FRAC_BITS = 16
_BIQ_COEF_MIN = -4.0
_BIQ_COEF_MAX = 4.0 - 2**-_BIQ_FRAC_BITS
_BIQ_HIGH_MASK = 0x7
_BIQ_SIGN_BIT = 1 << 18
_BIQ_MODULUS = 1 << 19

# Pass-through: y[n] = x[n]. Also the coefficients a freshly reset chip does
# *not* have. reset leaves every coefficient at zero, which is silence, so an
# enabled biquad that has never been programmed mutes its path.
BIQUAD_PASSTHROUGH = (1.0, 0.0, 0.0, 0.0, 0.0)

# DRC compressor/limiter slopes, keyed by the denominator of the 1:N ratio.
# 1 is unity (no compression) and 0 is a hard limit;
_DRC_COMPRESSION_SLOPES = {
    0: 0b000,
    2: 0b001,
    4: 0b010,
    8: 0b011,
    16: 0b100,
    32: 0b101,
    64: 0b110,
    1: 0b111,
}
# CMP1 and CMP2 implement only part of that table.
_DRC_COMPRESSOR_SLOPES = (0, 1, 2, 4, 8, 16)
# Expansion slopes (noise gate and expander), keyed by the numerator of N:1.
_DRC_EXPANSION_SLOPES = {1: 0b00, 2: 0b01, 4: 0b10, 8: 0b11}

# The dB value each knee point register reads at code 0, and the top code.
# Knee 1 and 2 start at 0 dB; knees 3 and 4 start well down the curve. Knee 1
# is a 5-bit field and the other three are 6-bit.
_DRC_KNEE1 = (0, 0x1F)
_DRC_KNEE2 = (0, 0x3F)
_DRC_KNEE3 = (-18, 0x3F)
_DRC_KNEE4 = (-35, 0x3F)

# Attack/decay codes are exposed raw rather than in milliseconds: every entry in
# the datasheet's table is a multiple of Ts = 1/sample_rate, and this driver
# deliberately does not know the sample rate (see configure_clocks).
_DRC_ATTACK_MAX = 0xC
_DRC_DECAY_MAX = 0xA
_DRC_PEAK_MAX = 0x7


def _db_to_dgain(db: float) -> int:
    """Convert dB to an R34/R35 digital volume code, clipping at both ends."""
    db = max(_DGAIN_MIN_DB, min(_DGAIN_MAX_DB, db))
    return int(round(_DGAIN_0DB + db * 2))


def _dgain_to_db(code: int) -> float:
    """Convert an R34/R35 digital volume code to dB.

    Mute and reserved codes have no place on the dB line, so they read back as
    the bottom of the scale.
    """
    if code < _DGAIN_MIN:
        return _DGAIN_MIN_DB
    return (code - _DGAIN_0DB) * 0.5


def _db_to_hp_vol(db: float) -> int:
    """Convert dB to an R32 headphone volume code (0 / -3 / -6 / -9 dB)."""
    code = int(round(-db / _HP_VOL_STEP_DB))
    return max(0, min(_HP_VOL_MAX_CODE, code))


def _hp_vol_to_db(code: int) -> float:
    """Convert an R32 headphone volume code to dB."""
    return -_HP_VOL_STEP_DB * code


def _db_to_pga(db: float) -> int:
    """Convert dB to an R7E front-end PGA gain code, clipping at both ends."""
    db = max(_PGA_MIN_DB, min(_PGA_MAX_DB, db))
    return int(round(db - _PGA_MIN_DB))


def _pga_to_db(code: int) -> float:
    """Convert an R7E front-end PGA gain code to dB."""
    return min(_PGA_MAX_CODE, code) + _PGA_MIN_DB


def _float_to_biq(value: float) -> int:
    """Convert a biquad coefficient to its 19-bit S2.16 code, clipping."""
    value = max(_BIQ_COEF_MIN, min(_BIQ_COEF_MAX, value))
    return int(round(value * (1 << _BIQ_FRAC_BITS))) % _BIQ_MODULUS


def _biq_to_float(code: int) -> float:
    """Convert a 19-bit S2.16 biquad coefficient code back to a float."""
    if code & _BIQ_SIGN_BIT:
        code -= _BIQ_MODULUS
    return code / (1 << _BIQ_FRAC_BITS)


def _biquad_words(coefficients: "Sequence[float]") -> "Tuple[int, ...]":
    """Pack ``(b0, b1, b2, a1, a2)`` into the ten register words of a filter.

    Register order is A1, A2, B0, B1, B2, each as a low-16 word followed by a
    high-3 word. The tenth word carries no enable bit here; the caller ORs in
    whatever the filter's current enable state is.
    """
    b0, b1, b2, a1, a2 = coefficients
    words = []
    for value in (a1, a2, b0, b1, b2):
        code = _float_to_biq(value)
        words.append(code & 0xFFFF)
        words.append((code >> _BIQ_FRAC_BITS) & _BIQ_HIGH_MASK)
    return tuple(words)


def _biquad_coefficients(words: "Sequence[int]") -> "Tuple[float, ...]":
    """Unpack ten register words into ``(b0, b1, b2, a1, a2)``."""
    values = [
        _biq_to_float(((words[i + 1] & _BIQ_HIGH_MASK) << _BIQ_FRAC_BITS) | words[i])
        for i in range(0, 10, 2)
    ]
    a1, a2, b0, b1, b2 = values
    return (b0, b1, b2, a1, a2)


def _db_to_knee(db: float, knee: "Tuple[int, int]", name: str) -> int:
    """Convert a DRC knee point in dB to its register code, 1 dB per step."""
    top_db, max_code = knee
    code = int(round(top_db - db))
    if not 0 <= code <= max_code:
        raise ValueError(f"{name} must be {top_db} to {top_db - max_code} dB")
    return code


def _knee_to_db(code: int, knee: "Tuple[int, int]") -> float:
    """Convert a DRC knee point register code back to dB."""
    return float(knee[0] - code)


def _drc_slope(ratio: int, table: dict, name: str, allowed=None) -> int:
    """Look a DRC slope ratio up in its code table."""
    if ratio not in table or (allowed is not None and ratio not in allowed):
        choices = sorted(table if allowed is None else allowed)
        raise ValueError(f"{name} must be one of {choices}")
    return table[ratio]


def _drc_code(value: int, maximum: int, name: str) -> int:
    """Range-check a raw DRC timing code."""
    if not 0 <= value <= maximum:
        raise ValueError(f"{name} must be 0-{maximum}")
    return value


def _drc_words(
    knee1_db: float,
    knee2_db: float,
    knee3_db: float,
    knee4_db: float,
    limiter_slope: int,
    compressor1_slope: int,
    compressor2_slope: int,
    expander_slope: int,
    noise_gate_slope: int,
    attack: int,
    decay: int,
    peak_attack: int,
    peak_decay: int,
    smooth_filter: bool,
) -> "Tuple[int, int, int, int]":
    """Pack a DRC curve into its four register words, enable bit set.

    The ADC block (R36-R39) and the DAC block (R3A-R3D) have identical layouts,
    so both paths pack through here.
    """
    knee_ip12 = (
        (1 << 15)
        | (_db_to_knee(knee2_db, _DRC_KNEE2, "knee2_db") << 8)
        | (int(bool(smooth_filter)) << 7)
        | _db_to_knee(knee1_db, _DRC_KNEE1, "knee1_db")
    )
    knee_ip34 = (_db_to_knee(knee4_db, _DRC_KNEE4, "knee4_db") << 8) | _db_to_knee(
        knee3_db, _DRC_KNEE3, "knee3_db"
    )
    # Bit 11 is unimplemented, which is why the expander field is not simply
    # two bits below the noise gate field.
    slopes = (
        (_drc_slope(noise_gate_slope, _DRC_EXPANSION_SLOPES, "noise_gate_slope") << 12)
        | (_drc_slope(expander_slope, _DRC_EXPANSION_SLOPES, "expander_slope") << 9)
        | (
            _drc_slope(
                compressor2_slope,
                _DRC_COMPRESSION_SLOPES,
                "compressor2_slope",
                _DRC_COMPRESSOR_SLOPES,
            )
            << 6
        )
        | (
            _drc_slope(
                compressor1_slope,
                _DRC_COMPRESSION_SLOPES,
                "compressor1_slope",
                _DRC_COMPRESSOR_SLOPES,
            )
            << 3
        )
        | _drc_slope(limiter_slope, _DRC_COMPRESSION_SLOPES, "limiter_slope")
    )
    atkdcy = (
        (_drc_code(peak_attack, _DRC_PEAK_MAX, "peak_attack") << 12)
        | (_drc_code(peak_decay, _DRC_PEAK_MAX, "peak_decay") << 8)
        | (_drc_code(attack, _DRC_ATTACK_MAX, "attack") << 4)
        | _drc_code(decay, _DRC_DECAY_MAX, "decay")
    )
    return (knee_ip12, knee_ip34, slopes, atkdcy)


class NAU88L21:
    """Driver for the Nuvoton NAU88L21 stereo audio codec.

    :param i2c: The I2C bus the codec is connected to.
    :param address: The I2C device address. Defaults to ``0x1B``.
    :param reset: Reset the codec during construction. Defaults to True.

    The codec must have a running bit clock before `configure_clocks` is
    called; see the module documentation for the ordering.

    """

    chip_id = ROUnaryStruct(_REG_I2C_DEVICE_ID, ">H")
    """The device ID register, which always reads ``0x1B23``."""

    # Every register is a 16-bit address carrying 16-bit big-endian data, so
    # each descriptor takes ``register_width=2, lsb_first=False``. Note that the
    # ``">H"`` on a whole-register ``UnaryStruct`` carries the byte order of the
    # register *data*, while ``lsb_first`` carries the byte order of the
    # register *address*; the two are independent and both have to be set.
    _reset_register = UnaryStruct(_REG_RESET, ">H")

    # -- Clocking ---------------------------------------------------------
    # Bit fields are declared where the power-up sequence needs a
    # read-modify-write; the rest of the sequence writes whole registers.
    _global_bias_enable = RWBit(_REG_BOOST, 12, register_width=2, lsb_first=False)
    _sysclk_from_fll = RWBit(_REG_CLK_DIVIDER, 15, register_width=2, lsb_first=False)
    _fll_sdm_enable = RWBit(_REG_FLL6, 14, register_width=2, lsb_first=False)
    _fll_cutoff500 = RWBit(_REG_FLL6, 13, register_width=2, lsb_first=False)
    _bclk_inverted = RWBit(_REG_I2S_PCM_CTRL1, 7, register_width=2, lsb_first=False)

    _clk_divider = UnaryStruct(_REG_CLK_DIVIDER, ">H")
    _fll1 = UnaryStruct(_REG_FLL1, ">H")
    _fll3 = UnaryStruct(_REG_FLL3, ">H")
    _fll4 = UnaryStruct(_REG_FLL4, ">H")
    _fll5 = UnaryStruct(_REG_FLL5, ">H")
    _fll7 = UnaryStruct(_REG_FLL7, ">H")
    _fll8 = UnaryStruct(_REG_FLL8, ">H")

    _i2s_ctrl1 = UnaryStruct(_REG_I2S_PCM_CTRL1, ">H")
    _i2s_ctrl2 = UnaryStruct(_REG_I2S_PCM_CTRL2, ">H")

    # -- Playback ---------------------------------------------------------
    _ena_ctrl = UnaryStruct(_REG_ENA_CTRL, ">H")
    _jack_det_ctrl = UnaryStruct(_REG_JACK_DET_CTRL, ">H")
    _dac_ctrl1 = UnaryStruct(_REG_DAC_CTRL1, ">H")
    _mute_ctrl = UnaryStruct(_REG_MUTE_CTRL, ">H")
    _hsvol_ctrl = UnaryStruct(_REG_HSVOL_CTRL, ">H")
    _dac_channel_volumes = UnaryStruct(_REG_DACR_CTRL, ">H")
    _classg_ctrl = UnaryStruct(_REG_CLASSG_CTRL, ">H")
    _bias_adj = UnaryStruct(_REG_BIAS_ADJ, ">H")
    _analog_control_2 = UnaryStruct(_REG_ANALOG_CONTROL_2, ">H")
    _rdac = UnaryStruct(_REG_RDAC, ">H")
    _boost = UnaryStruct(_REG_BOOST, ">H")
    _charge_pump = UnaryStruct(_REG_CHARGE_PUMP, ">H")

    # The headphone drivers share R7F with the microphone PGAs, so this one has
    # to be a bit field even though the power-up sequence sets it wholesale.
    _hp_drivers = RWBits(6, _REG_POWER_UP_CONTROL, 0, register_width=2, lsb_first=False)

    _en_dac_left = RWBit(_REG_ENA_CTRL, 10, register_width=2, lsb_first=False)
    _en_dac_right = RWBit(_REG_ENA_CTRL, 11, register_width=2, lsb_first=False)
    _dac_left_enable = RWBit(_REG_RDAC, 12, register_width=2, lsb_first=False)
    _dac_right_enable = RWBit(_REG_RDAC, 13, register_width=2, lsb_first=False)
    _dac_left_clock_enable = RWBit(_REG_RDAC, 8, register_width=2, lsb_first=False)
    _dac_right_clock_enable = RWBit(_REG_RDAC, 9, register_width=2, lsb_first=False)
    # R80[9:8] are PDB_DAC, "DAC Right/Left Power Down Bar": active-LOW
    # power-downs, so 1 means the DAC output stage is POWERED.
    _dac_left_output_enable = RWBit(_REG_CHARGE_PUMP, 8, register_width=2, lsb_first=False)
    _dac_right_output_enable = RWBit(_REG_CHARGE_PUMP, 9, register_width=2, lsb_first=False)
    _charge_pump_enable = RWBit(_REG_CHARGE_PUMP, 5, register_width=2, lsb_first=False)

    # -- Capture ------------------------------------------------------------
    _analog_adc1 = UnaryStruct(_REG_ANALOG_ADC_1, ">H")
    _analog_adc2 = UnaryStruct(_REG_ANALOG_ADC_2, ">H")
    _mic_bias = UnaryStruct(_REG_MIC_BIAS, ">H")
    _fepga = UnaryStruct(_REG_FEPGA, ">H")
    _pga_gain = UnaryStruct(_REG_PGA_GAIN, ">H")
    _adc_rate = UnaryStruct(_REG_ADC_RATE, ">H")
    _adc_dgain_ctrl = UnaryStruct(_REG_ADC_DGAIN_CTRL, ">H")
    _adc_channel_volumes = UnaryStruct(_REG_ADC_DGAIN_CTRL1, ">H")

    # R7F[15:14], the other half of the register the headphone drivers live in.
    _mic_pgas = RWBits(2, _REG_POWER_UP_CONTROL, 14, register_width=2, lsb_first=False)

    _en_adc_left = RWBit(_REG_ENA_CTRL, 8, register_width=2, lsb_first=False)
    _en_adc_right = RWBit(_REG_ENA_CTRL, 9, register_width=2, lsb_first=False)
    _micbias_powerup = RWBit(_REG_MIC_BIAS, 8, register_width=2, lsb_first=False)
    _micbias_internal_resistor = RWBit(_REG_MIC_BIAS, 12, register_width=2, lsb_first=False)
    _micbias_voltage = RWBits(3, _REG_MIC_BIAS, 0, register_width=2, lsb_first=False)
    # PDNOTL / PDNOTR, the two ADC analog power enables. Bit 5 in between them
    # is set out of reset and is left alone.
    _adc_left_power = RWBit(_REG_ANALOG_ADC_2, 6, register_width=2, lsb_first=False)
    _adc_right_power = RWBit(_REG_ANALOG_ADC_2, 4, register_width=2, lsb_first=False)

    # -- Volumes and mutes -------------------------------------------------
    _dac_left_volume = RWBits(8, _REG_DACR_CTRL, 0, register_width=2, lsb_first=False)
    _dac_right_volume = RWBits(8, _REG_DACR_CTRL, 8, register_width=2, lsb_first=False)
    _adc_left_volume = RWBits(8, _REG_ADC_DGAIN_CTRL1, 0, register_width=2, lsb_first=False)
    _adc_right_volume = RWBits(8, _REG_ADC_DGAIN_CTRL1, 8, register_width=2, lsb_first=False)
    _hp_left_volume = RWBits(2, _REG_HSVOL_CTRL, 4, register_width=2, lsb_first=False)
    _hp_right_volume = RWBits(2, _REG_HSVOL_CTRL, 0, register_width=2, lsb_first=False)
    _hp_left_mute = RWBit(_REG_HSVOL_CTRL, 13, register_width=2, lsb_first=False)
    _hp_right_mute = RWBit(_REG_HSVOL_CTRL, 12, register_width=2, lsb_first=False)
    _dac_soft_mute = RWBit(_REG_MUTE_CTRL, 9, register_width=2, lsb_first=False)
    _adc_soft_mute = RWBit(_REG_MUTE_CTRL, 1, register_width=2, lsb_first=False)

    # -- Biquad filters and DRC ----------------------------------------------
    # Ten consecutive registers in one transaction.
    _adc_biquad_block = Struct(_REG_BIQ0_COF1, ">10H")
    _dac_biquad_block = Struct(_REG_BIQ1_COF1, ">10H")
    _adc_biquad_enable = RWBit(_REG_BIQ0_COF10, 3, register_width=2, lsb_first=False)
    _dac_biquad_enable = RWBit(_REG_BIQ1_COF10, 3, register_width=2, lsb_first=False)

    _adc_drc_knee_ip12 = UnaryStruct(_REG_ADC_DRC_KNEE_IP12, ">H")
    _adc_drc_knee_ip34 = UnaryStruct(_REG_ADC_DRC_KNEE_IP34, ">H")
    _adc_drc_slopes = UnaryStruct(_REG_ADC_DRC_SLOPES, ">H")
    _adc_drc_atkdcy = UnaryStruct(_REG_ADC_DRC_ATKDCY, ">H")
    _dac_drc_knee_ip12 = UnaryStruct(_REG_DAC_DRC_KNEE_IP12, ">H")
    _dac_drc_knee_ip34 = UnaryStruct(_REG_DAC_DRC_KNEE_IP34, ">H")
    _dac_drc_slopes = UnaryStruct(_REG_DAC_DRC_SLOPES, ">H")
    _dac_drc_atkdcy = UnaryStruct(_REG_DAC_DRC_ATKDCY, ">H")
    _adc_drc_enable = RWBit(_REG_ADC_DRC_KNEE_IP12, 15, register_width=2, lsb_first=False)
    _dac_drc_enable = RWBit(_REG_DAC_DRC_KNEE_IP12, 15, register_width=2, lsb_first=False)
    # CLK_DRC_EN. Set out of reset and set again by both quickstart paths.
    _drc_clock_enable = RWBit(_REG_ENA_CTRL, 0, register_width=2, lsb_first=False)

    def __init__(self, i2c: I2C, address: int = _DEFAULT_ADDRESS, reset: bool = True) -> None:
        self.register_accessor = I2CRegisterAccessor(
            I2CDevice(i2c, address), address_width=2, lsb_first=False
        )
        self._bit_depth = 16
        self._mclk_freq = 0  # 0 means "FLL locked to BCLK"

        found_id = self.chip_id
        if found_id != _CHIP_ID:
            raise RuntimeError(
                f"NAU88L21 not found at 0x{address:02X}; ID register read 0x{found_id:04X}"
            )
        if reset:
            self.reset()

    def reset(self) -> None:
        """Reset the codec to its power-on defaults.

        It is written twice to clear the internal state machines;
        one write clears the registers alone.
        """
        self._reset_register = 0xFFFF
        self._reset_register = 0xFFFF
        time.sleep(0.02)

    @property
    def bit_depth(self) -> int:
        """The I2S word length in bits, as last set by `configure_clocks`.

        :getter: Return the configured bit depth.
        """
        return self._bit_depth

    @property
    def mclk_freq(self) -> Optional[int]:
        """The MCLK pin frequency, as last set by `configure_clocks`.

        ``None`` means SYSCLK comes from the FLL locked to BCLK and the MCLK
        pin is unused.

        :getter: Return the configured MCLK frequency in Hz, or None.
        """
        return self._mclk_freq or None

    def configure_clocks(
        self,
        bit_depth: int = 16,
        mclk_freq: Optional[int] = None,
        left_justified: bool = False,
    ) -> None:
        """Configure the codec's I2S interface and clocking.

        **The bit clock must already be running when this is called.** With the
        default ``mclk_freq=None`` the codec's SYSCLK comes from its FLL locked
        to BCLK, and an FLL with no reference will not lock. Construct the
        ``I2SOut`` object and ``play()`` a looping sample first, at any sample
        rate, then call this.

        :param bit_depth: I2S word length: 16, 20, 24 or 32. CircuitPython
            always sends 16-bit stereo, so leave this at 16.
        :param mclk_freq: ``None`` (the default) locks the FLL to BCLK and
            leaves the MCLK pin unused. ``12_000_000`` instead takes SYSCLK
            straight from a 12 MHz clock on the MCLK pin with the FLL bypassed,
            which requires ``microcontroller.cpu.frequency = 144_000_000`` and
            a ``pwmio.PWMOut`` driving that pin, and which pins the sample rate
            at 46875 Hz. The FLL is the better default.
        :param left_justified: Use left-justified framing rather than Philips
            I2S. This is the framing the codec both expects on DACDAT and
            drives on ADCDAT, so it must match how the ``I2SOut`` object was
            built, and how any ``I2SIn`` capturing ADCDAT was built.
        """
        if bit_depth not in _I2S_DL:
            raise ValueError(f"bit_depth must be one of {sorted(_I2S_DL)}")
        if mclk_freq is not None and mclk_freq != 12_000_000:
            raise ValueError("mclk_freq must be None or 12000000")

        self._bit_depth = bit_depth
        self._mclk_freq = mclk_freq or 0

        # The FLL will not lock until the global bias is up.
        self._global_bias_enable = True

        self._i2s_ctrl1 = (_I2S_DL[bit_depth] << 2) | (
            _I2S_DF_LEFT if left_justified else _I2S_DF_I2S
        )
        # I2S_TRI=0 (drivers on -- it defaults to 1, which tri-states every I2S
        # pin), ADCDAT0_OE=1, MS0=0 so the codec runs from the external clock
        # (datasheet slave mode). BCLK_DIV and LRC_DIV only apply when the codec
        # generates the clocks itself, and are ignored here.
        self._i2s_ctrl2 = 0x0010

        if mclk_freq is not None:
            # SYSCLK straight from the MCLK pin; the FLL stays out of it.
            self._clk_divider = _CLK_DIVIDER_MCLK
            return

        # Stay on the MCLK pin while the FLL registers are written, exactly as
        # the vendor driver does, then switch SYSCLK over at the end.
        self._clk_divider = _CLK_DIVIDER_MCLK | _MCLK_SRC
        self._fll1 = _FLL_RATIO | (0x6 << 10)  # FLL_RATIO | ICTRL_LATCH
        self._fll7 = 0x0000  # FLL_FRAC[23:16]
        self._fll8 = 0x0000  # FLL_FRAC[15:0]
        self._fll3 = (0x2 << 10) | _FLL_INTEGER  # REF_SRC=BCLK | FLL_INTEGER
        self._fll4 = 0x8010  # HIGHBW_EN | REF_DIV=1 | N2
        # FLL_FRAC is 0, so take the integer path: accumulator output, no loop
        # filter, no sigma-delta.
        self._fll5 = 0x1000
        self._fll_sdm_enable = False
        self._fll_cutoff500 = False

        time.sleep(0.002)
        self._sysclk_from_fll = True

    @property
    def bit_clock_inverted(self) -> bool:
        """Which BCLK edge the codec latches on.

        Only needed if captured words come back rotated by a bit -- the
        datasheet's external clock timing already matches CircuitPython's
        edge convention, so this should not be necessary.

        :getter: Return True if the bit clock is inverted.
        :setter: Invert or un-invert the bit clock.
        """
        return self._bclk_inverted

    @bit_clock_inverted.setter
    def bit_clock_inverted(self, inverted: bool) -> None:
        self._bclk_inverted = inverted

    # -- Playback path -------------------------------------------------------

    @property
    def headphone_output(self) -> bool:
        """Headphone output helper with quickstart default settings.

        Setting this to True powers up the whole DAC-to-headphone chain and
        picks levels intended for quiet listening on sensitive low-impedance
        earbuds:

        * ``dac_volume`` = -20 dB
        * ``headphone_volume`` = -9 dB (the quietest the analog stage goes)

        Setting it to False powers the headphone drivers and the charge pump
        back down, leaving the microphone path alone.

        Either value leaves the microphone path as it found it, so this and
        `microphone_input` can be set in either order to run full duplex.

        `configure_clocks` must have been called first -- with no SYSCLK the
        DAC has no clock to run from.

        :getter: True if any of the headphone output drivers are powered.
        :setter: **This sets several properties at once**, including both DAC
            enables, both DAC channel volumes, the headphone analog volume, and
            the DAC and headphone mutes.
        """
        return self._hp_drivers != 0

    @headphone_output.setter
    def headphone_output(self, enabled: bool) -> None:
        if not enabled:
            self._hp_drivers = 0
            self._charge_pump_enable = False
            return

        # R01 is shared with the capture path, which ORs EN_ADCL/R (bits 8-9)
        # in. Mask those through rather than writing the register flat, so that
        # powering up the headphones after the microphone does not silently
        # switch the microphone off. Full duplex should leave R01 at 0x0FFF
        # whichever order the two paths were brought up in.
        self._ena_ctrl = (self._ena_ctrl & 0x0300) | 0x0CFF
        self._dac_ctrl1 = 0x0082  # OSR128
        self._mute_ctrl = 0x0000  # DAC and ADC soft mute off
        self._hsvol_ctrl = 0x0000  # headphone unmuted, 0 dB
        self._dac_channel_volumes = (_DGAIN_0DB << 8) | _DGAIN_0DB
        self._jack_det_ctrl = 0xC000  # output pulldowns disabled
        self._classg_ctrl = 0x0007  # class-G enable + left/right DAC
        # WARNING: R66 bits [9:8] are BIAS_TESTDAC. Setting them switches both
        # DACs to a test input tied to GND, which is guaranteed silence. This
        # value keeps them clear: VMIDEN + VMID_SEL=125k only.
        self._bias_adj = 0x0060
        self._analog_control_2 = 0x1003
        self._rdac = 0x772C  # DACL/R_EN + DACL/R_CLK_EN
        self._boost = 0x3140  # headphone boost, GLOBAL_BIAS_EN still set
        self._hp_drivers = _HP_DRIVERS_ON
        # Charge pump enable + PDB_DAC=11.  JAMNODCLOW (bit 10) goes on
        # only after the pump has ramped.
        self._charge_pump = 0x0320
        time.sleep(0.02)
        self._charge_pump = 0x0720

        # Now back the levels down from the 0 dB the sequence above sets.
        self.dac_volume = _QUICKSTART_DAC_VOLUME_DB
        self.headphone_volume = _QUICKSTART_HP_VOLUME_DB

    @property
    def left_dac(self) -> bool:
        """The left DAC enabled status.

        :getter: True if the left DAC is enabled.
        :setter: Enable or disable the left DAC.
        """
        return self._en_dac_left

    @left_dac.setter
    def left_dac(self, enabled: bool) -> None:
        self._en_dac_left = enabled
        self._dac_left_enable = enabled
        self._dac_left_clock_enable = enabled
        self._dac_left_output_enable = enabled

    @property
    def right_dac(self) -> bool:
        """The right DAC enabled status.

        :getter: True if the right DAC is enabled.
        :setter: Enable or disable the right DAC.
        """
        return self._en_dac_right

    @right_dac.setter
    def right_dac(self, enabled: bool) -> None:
        self._en_dac_right = enabled
        self._dac_right_enable = enabled
        self._dac_right_clock_enable = enabled
        self._dac_right_output_enable = enabled

    # -- Capture path --------------------------------------------------------

    @property
    def microphone_input(self) -> bool:
        """Microphone input helper with quickstart default settings.

        Setting this to True powers up the whole microphone-to-ADC chain --
        bias, MICBIAS, both front-end PGAs at `mic_gain` = 36 dB, the ADC
        analog front end and both ADC channels -- and then waits for the bias
        to settle before returning. It is equivalent to
        ``configure_microphone_input()``; use that method directly to pick a
        different gain or to skip the settling delay.

        Setting it to False powers the microphone path back down, leaving the
        headphone path alone.

        `configure_clocks` must have been called first.

        :getter: True if either microphone PGA is powered.
        :setter: **This sets several properties at once**, including
            `mic_gain`, `adc_volume` and both ADC enables, and it blocks for
            about 0.4 s while the bias settles.
        """
        return self._mic_pgas != 0

    @microphone_input.setter
    def microphone_input(self, enabled: bool) -> None:
        if not enabled:
            self._mic_pgas = 0
            self._micbias_powerup = False
            self._adc_left_power = False
            self._adc_right_power = False
            self._en_adc_left = False
            self._en_adc_right = False
            return
        self.configure_microphone_input()

    def configure_microphone_input(
        self, gain_db: float = _QUICKSTART_MIC_GAIN_DB, settle: bool = True
    ) -> None:
        """Power up the microphone-to-ADC path.

        This is what ``microphone_input = True`` runs; call it directly to
        choose the front-end gain, or to return immediately instead of waiting
        out the bias settling time.

        :param gain_db: Front-end PGA gain in dB, -1 to 36. See `mic_gain`.
        :param settle: Wait ~0.4 s for the microphone bias and the ADC front
            end to settle before returning. With ``settle=False`` the first
            few hundred milliseconds of a capture are DC drift with almost no
            audio in them, so only turn it off if you are going to discard or
            high-pass that part anyway.
        """
        # Bias first, then the global bias enable. R66 is the same value the
        # playback path writes; R76's bias bit is set without touching the
        # headphone boost bits next to it.
        self._bias_adj = 0x0060  # VMIDEN + VMID_SEL=125k, BIAS_TESTDAC clear
        self._global_bias_enable = True

        self._analog_adc1 = 0x0011  # PDMICDET: mic-detect powered down
        self._mic_bias = 0x0106  # MICBIAS POWERUP + the default 1.53x level
        # FEPGA_MODEL/MODER both 0: MICP and MICN connected, differential, no
        # anti-aliasing filter adjustment. Bit 1 of either nibble disconnects
        # that channel's mic pins, which is a useful way to prove that a signal
        # really is coming in through the analog front end.
        self._fepga = 0x0000
        self.mic_gain = gain_db
        self._mic_pgas = _MIC_PGAS_ON
        self._analog_adc2 = 0x0070  # PDNOTL | PDNOTR: ADC analog power
        self._adc_rate = 0x0002  # ADC_SYNC_DOWN=128, matching the DAC's OSR128
        self._adc_dgain_ctrl = 0x0000  # no headphone-bypass mixing
        self.adc_volume = 0
        # OR the ADC enables in: the playback path owns the DAC bits of R01, so
        # this register cannot be written wholesale. `headphone_output` masks
        # these two bits through for the same reason, which is what makes the
        # two paths safe to bring up in either order.
        self._ena_ctrl |= 0x03FF  # + EN_ADCL | EN_ADCR

        if settle:
            time.sleep(_MIC_SETTLE_SECONDS)

    @property
    def mic_gain(self) -> float:
        """The analog front-end PGA gain in dB, -1 to 36 in 1 dB steps.

        This is the gain applied to the microphone before the ADC, and it is
        the one that changes the signal-to-noise ratio of a capture -- unlike
        `adc_volume`, which scales what the ADC already produced. Setting it
        writes both channels.

        :getter: Return the left channel's gain in dB.
        :setter: Set both channels to the same gain in dB, clipped to range.
        """
        return _pga_to_db(self._pga_gain & 0x3F)

    @mic_gain.setter
    def mic_gain(self, db: float) -> None:
        code = _db_to_pga(db)
        self._pga_gain = (code << 8) | code

    @property
    def adc_volume(self) -> float:
        """The ADC digital volume in dB, averaged across the two channels.

        Same scale as `dac_volume`: -66 dB to +24 dB in 0.5 dB steps, 0 dB
        unity. Setting it writes both channels of R35 at once.

        Note that on a board with a single microphone on the left channel only
        the left half of this register does anything audible; the right
        channel's code reads back but has no signal to scale.

        :getter: Return the volume in dB.
        :setter: Set both channels to the same volume in dB, clipped to range.
        """
        left = _dgain_to_db(self._adc_left_volume)
        right = _dgain_to_db(self._adc_right_volume)
        return (left + right) / 2

    @adc_volume.setter
    def adc_volume(self, db: float) -> None:
        code = _db_to_dgain(db)
        self._adc_channel_volumes = (code << 8) | code

    def config_mic_bias(
        self, power_down: bool = False, voltage: int = 6, internal_resistor: bool = False
    ) -> None:
        """Configure the MICBIAS supply.

        :param power_down: Power MICBIAS down. `configure_microphone_input`
            powers it up, so this is how it goes back off on its own.
        :param voltage: Output level select, 0-7: 0 is VDDA, then 1x, 1.1x,
            1.2x, 1.3x, 1.4x and 1.53x for 6 and 7. 6 is the reset default and
            what the microphone path uses.
        :param internal_resistor: Connect the internal 2 kOhm resistor between
            MICBIAS and MICGND. Only needed if the board does not fit an
            external one.
        """
        if not 0 <= voltage <= 7:
            raise ValueError("voltage must be 0-7")
        self._micbias_voltage = voltage
        self._micbias_internal_resistor = internal_resistor
        self._micbias_powerup = not power_down

    # -- Volumes and mutes ---------------------------------------------------

    @property
    def dac_volume(self) -> float:
        """The DAC digital volume in dB, averaged across the two channels.

        Range is -66 dB (soft) to +24 dB (loud) in 0.5 dB steps; 0 dB is unity.
        Setting it writes both channels of R34 at once.

        This is the level feeding the headphone amplifier, so it interacts with
        `headphone_volume`, `headphone_left_mute`, `headphone_right_mute` and
        `dac_soft_mute`.

        :getter: Return the volume in dB.
        :setter: Set both channels to the same volume in dB, clipped to range.
        """
        return (self.left_dac_channel_volume + self.right_dac_channel_volume) / 2

    @dac_volume.setter
    def dac_volume(self, db: float) -> None:
        code = _db_to_dgain(db)
        self._dac_channel_volumes = (code << 8) | code

    @property
    def left_dac_channel_volume(self) -> float:
        """The left DAC channel digital volume in dB, -66 to +24.

        :getter: Return the volume in dB.
        :setter: Set the volume in dB, clipped to range.
        """
        return _dgain_to_db(self._dac_left_volume)

    @left_dac_channel_volume.setter
    def left_dac_channel_volume(self, db: float) -> None:
        self._dac_left_volume = _db_to_dgain(db)

    @property
    def right_dac_channel_volume(self) -> float:
        """The right DAC channel digital volume in dB, -66 to +24.

        :getter: Return the volume in dB.
        :setter: Set the volume in dB, clipped to range.
        """
        return _dgain_to_db(self._dac_right_volume)

    @right_dac_channel_volume.setter
    def right_dac_channel_volume(self, db: float) -> None:
        self._dac_right_volume = _db_to_dgain(db)

    @property
    def headphone_volume(self) -> float:
        """The headphone analog volume in dB, averaged across the two channels.

        T his stage has only four steps:
        0, -3, -6 and -9 dB. Values in between are rounded to the nearest step
        and values outside the range are clipped, so the level actually applied
        is worth reading back. Most of the usable attenuation lives in
        `dac_volume`.

        :getter: Return the volume in dB.
        :setter: Set both channels to the nearest available step.
        """
        left = _hp_vol_to_db(self._hp_left_volume)
        right = _hp_vol_to_db(self._hp_right_volume)
        return (left + right) / 2

    @headphone_volume.setter
    def headphone_volume(self, db: float) -> None:
        code = _db_to_hp_vol(db)
        self._hp_left_volume = code
        self._hp_right_volume = code

    @property
    def headphone_left_mute(self) -> bool:
        """The left headphone amplifier mute.

        :getter: True if the left headphone channel is muted.
        :setter: Mute or unmute the left headphone channel.
        """
        return self._hp_left_mute

    @headphone_left_mute.setter
    def headphone_left_mute(self, mute: bool) -> None:
        self._hp_left_mute = mute

    @property
    def headphone_right_mute(self) -> bool:
        """The right headphone amplifier mute.

        :getter: True if the right headphone channel is muted.
        :setter: Mute or unmute the right headphone channel.
        """
        return self._hp_right_mute

    @headphone_right_mute.setter
    def headphone_right_mute(self, mute: bool) -> None:
        self._hp_right_mute = mute

    @property
    def dac_soft_mute(self) -> bool:
        """The DAC soft mute, which ramps both channels down together.

        This is the *only* mute the DAC path has -- the chip has no per-channel
        DAC mute bit, so there is no ``left_dac_mute`` / ``right_dac_mute``
        here. A single channel can still be silenced through its
        `left_dac_channel_volume` / `right_dac_channel_volume`.

        :getter: True if the DAC is muted.
        :setter: Mute or unmute the DAC.
        """
        return self._dac_soft_mute

    @dac_soft_mute.setter
    def dac_soft_mute(self, mute: bool) -> None:
        self._dac_soft_mute = mute

    @property
    def adc_soft_mute(self) -> bool:
        """The ADC soft mute, which ramps both capture channels down together.

        :getter: True if the ADC is muted.
        :setter: Mute or unmute the ADC.
        """
        return self._adc_soft_mute

    @adc_soft_mute.setter
    def adc_soft_mute(self, mute: bool) -> None:
        self._adc_soft_mute = mute

    # -- Biquad filters ------------------------------------------------------

    @property
    def adc_biquad(self) -> bool:
        """Whether the capture-path biquad filter (BIQ0) is running.

        Enabling a filter whose coefficients have never been programmed is
        silence, not a bypass. reset leaves every coefficient at zero. Set
        `adc_biquad_coefficients` first, or to ``BIQUAD_PASSTHROUGH``.

        :getter: True if the ADC biquad is enabled.
        :setter: Enable or disable the ADC biquad.
        """
        return self._adc_biquad_enable

    @adc_biquad.setter
    def adc_biquad(self, enabled: bool) -> None:
        self._adc_biquad_enable = enabled

    @property
    def dac_biquad(self) -> bool:
        """Whether the playback-path biquad filter (BIQ1) is running.

        Same caveat as `adc_biquad`: zeroed coefficients are silence.

        :getter: True if the DAC biquad is enabled.
        :setter: Enable or disable the DAC biquad.
        """
        return self._dac_biquad_enable

    @dac_biquad.setter
    def dac_biquad(self, enabled: bool) -> None:
        self._dac_biquad_enable = enabled

    @property
    def adc_biquad_coefficients(self) -> "Tuple[float, ...]":
        """The capture-path biquad coefficients, as ``(b0, b1, b2, a1, a2)``.

        The filter is the usual second-order section::

                    b0 + b1*z**-1 + b2*z**-2
            H(z) = --------------------------
                     1 + a1*z**-1 + a2*z**-2

        which is exactly the sign convention ``scipy.signal.butter`` and
        friends return, so ``b, a = butter(...)`` maps straight onto
        ``(b[0], b[1], b[2], a[1], a[2])``.

        Coefficients are stored in a 19-bit S2.16 fixed-point format, so the
        range is -4.0 to +3.99998 in steps of 1/65536 and values outside it are
        clipped. Round-tripping through this property therefore returns the
        quantized coefficients, not the ones that were written.

        :getter: Return the five coefficients as floats.
        :setter: Write all five in a single ten-register transaction, leaving
            the enable bit as it was.
        """
        return _biquad_coefficients(self._adc_biquad_block)

    @adc_biquad_coefficients.setter
    def adc_biquad_coefficients(self, coefficients: "Sequence[float]") -> None:
        words = _biquad_words(coefficients)
        # The last register shares itself with BIQ0_EN, so preserve it rather
        # than switching the filter off as a side effect of retuning it.
        enable = (1 << 3) if self._adc_biquad_enable else 0
        self._adc_biquad_block = words[:9] + (words[9] | enable,)

    def configure_adc_highpass(
        self,
        frequency: float = 120.0,
        sample_rate: int = 48000,
        q: float = 0.7071,
        enable: bool = True,
    ) -> None:
        """Program the capture biquad as a DC-blocking high-pass filter.

        The microphone word carries a large DC offset plus a slow sub-audio
        bias drift -- thousands of counts, and it grows with `mic_gain`. Left
        in, it eats output headroom and, on speech transients, shows up in a
        passthrough as a loud subsonic "wind" that can drive the output into
        clipping. This loads BIQ0 with a second-order RBJ high-pass whose exact
        double zero at DC removes the offset *at the source*, before the I2S
        interface, so nothing downstream has to deal with it.

        Doing it here rather than with a host-side biquad matters: a high-pass
        at a corner this far below Nyquist has coefficients very close to
        (1, -2, 1)/(1, -2, 1), and host filters built in fixed point round away
        the tiny differences that give the stop-band its depth, so they leak
        tens of dB of sub-bass. This chip runs the section at full internal
        precision, and forcing the numerator symmetric below keeps the DC null
        exact even after the coefficients are quantized to the register's S2.16
        format.

        :param frequency: -3 dB corner in Hz. 120 keeps speech fundamentals
            while cutting the drift; go higher to cut more low end.
        :param sample_rate: The ADC's sample rate, i.e. the I2S frame rate the
            codec is clocked at. Must match it or the corner lands elsewhere.
        :param q: Filter Q. 0.7071 is a maximally flat (Butterworth) response.
        :param enable: Leave the filter switched on afterwards.
        """
        # RBJ high-pass (Audio EQ Cookbook), normalised so a0 = 1.
        w0 = 2 * math.pi * frequency / sample_rate
        cos_w0 = math.cos(w0)
        alpha = math.sin(w0) / (2 * q)
        a0 = 1 + alpha
        # Pre-quantise b0 to the S2.16 grid, then derive b1 = -2*b0, b2 = b0
        # from it. Because 2 * (an exact grid value) is still on the grid, the
        # setter's rounding is a no-op on these three and the zeros stay exactly
        # at z = 1 -- a perfect DC null instead of the ~-20 dB a naive rounding
        # of each coefficient leaves behind.
        b0 = round(((1 + cos_w0) / 2 / a0) * 65536) / 65536
        a1 = (-2 * cos_w0) / a0
        a2 = (1 - alpha) / a0
        self.adc_biquad_coefficients = (b0, -2 * b0, b0, a1, a2)
        self.adc_biquad = enable

    @property
    def dac_biquad_coefficients(self) -> "Tuple[float, ...]":
        """The playback-path biquad coefficients, as ``(b0, b1, b2, a1, a2)``.

        See `adc_biquad_coefficients` for the format and its limits.

        :getter: Return the five coefficients as floats.
        :setter: Write all five in a single ten-register transaction, leaving
            the enable bit as it was.
        """
        return _biquad_coefficients(self._dac_biquad_block)

    @dac_biquad_coefficients.setter
    def dac_biquad_coefficients(self, coefficients: "Sequence[float]") -> None:
        words = _biquad_words(coefficients)
        enable = (1 << 3) if self._dac_biquad_enable else 0
        self._dac_biquad_block = words[:9] + (words[9] | enable,)

    # -- Dynamic range compression -------------------------------------------

    @property
    def adc_drc(self) -> bool:
        """Whether the capture-path dynamic range compressor is running.

        Setting this to True applies the chip's default curve by calling
        `configure_adc_drc` with no arguments; use that method to shape it.

        :getter: True if the ADC DRC is enabled.
        :setter: Enable (with default settings) or disable the ADC DRC.
        """
        return self._adc_drc_enable

    @adc_drc.setter
    def adc_drc(self, enabled: bool) -> None:
        if enabled:
            self.configure_adc_drc()
        else:
            self._adc_drc_enable = False

    @property
    def dac_drc(self) -> bool:
        """Whether the playback-path dynamic range compressor is running.

        Setting this to True applies the chip's default curve by calling
        `configure_dac_drc` with no arguments; use that method to shape it.

        :getter: True if the DAC DRC is enabled.
        :setter: Enable (with default settings) or disable the DAC DRC.
        """
        return self._dac_drc_enable

    @dac_drc.setter
    def dac_drc(self, enabled: bool) -> None:
        if enabled:
            self.configure_dac_drc()
        else:
            self._dac_drc_enable = False

    def configure_adc_drc(
        self,
        knee1_db: float = -6,
        knee2_db: float = -20,
        knee3_db: float = -36,
        knee4_db: float = -50,
        limiter_slope: int = 1,
        compressor1_slope: int = 1,
        compressor2_slope: int = 1,
        expander_slope: int = 4,
        noise_gate_slope: int = 4,
        attack: int = 5,
        decay: int = 7,
        peak_attack: int = 3,
        peak_decay: int = 4,
        smooth_filter: bool = True,
    ) -> None:
        """Configure and enable the capture-path dynamic range compressor.

        The DRC is a five-section static curve. Reading down from the loudest
        input: the limiter above ``knee1_db``, compressor 1 between knee 1 and
        knee 2, compressor 2 between knee 2 and knee 3, the expander between
        knee 3 and knee 4, and the noise gate below knee 4. Every argument
        defaults to the chip's own reset value, so calling this with no
        arguments enables the datasheet's default curve.

        :param knee1_db: Limiter knee, 0 to -31 dB.
        :param knee2_db: Compressor 1 knee, 0 to -63 dB.
        :param knee3_db: Compressor 2 knee, -18 to -81 dB.
        :param knee4_db: Expander knee, -35 to -98 dB.
        :param limiter_slope: Denominator of the limiter's 1:N ratio: 1 (no
            limiting), 2, 4, 8, 16, 32, 64, or 0 for a hard limit.
        :param compressor1_slope: Same, but only 1, 2, 4, 8, 16 or 0.
        :param compressor2_slope: Same as ``compressor1_slope``.
        :param expander_slope: Numerator of the expander's N:1 ratio: 1, 2 or
            4. (8 is reserved on the capture path.)
        :param noise_gate_slope: Numerator of the noise gate's N:1 ratio: 1, 2,
            4 or 8.
        :param attack: Attack time code, 0-12. The times are multiples of
            Ts = 1/sample_rate -- 0 is Ts, then 3, 7, 15, 31, 63, 127, 255,
            511, 1023, 2047, 4095 and 8191 Ts. They are codes rather than
            milliseconds because this driver deliberately does not know the
            sample rate; see `configure_clocks`.
        :param decay: Decay time code, 0-10: 63 Ts, then 127, 255, 511, 1023,
            2047, 4095, 8191, 16383, 32767 and 65535 Ts.
        :param peak_attack: Peak detector attack code, 0-7, same series as
            ``attack``.
        :param peak_decay: Peak detector release code, 0-7, same series as
            ``decay``.
        :param smooth_filter: Round the corners of the static curve at the
            knee points.
        """
        self._drc_clock_enable = True
        knee_ip12, knee_ip34, slopes, atkdcy = _drc_words(
            knee1_db,
            knee2_db,
            knee3_db,
            knee4_db,
            limiter_slope,
            compressor1_slope,
            compressor2_slope,
            expander_slope,
            noise_gate_slope,
            attack,
            decay,
            peak_attack,
            peak_decay,
            smooth_filter,
        )
        # Curve first, enable last: the enable bit rides in the knee register,
        # so writing that one last means the DRC never runs a half-written
        # curve.
        self._adc_drc_knee_ip34 = knee_ip34
        self._adc_drc_slopes = slopes
        self._adc_drc_atkdcy = atkdcy
        self._adc_drc_knee_ip12 = knee_ip12

    def configure_dac_drc(
        self,
        knee1_db: float = -6,
        knee2_db: float = -20,
        knee3_db: float = -36,
        knee4_db: float = -50,
        limiter_slope: int = 2,
        compressor1_slope: int = 1,
        compressor2_slope: int = 1,
        expander_slope: int = 4,
        noise_gate_slope: int = 4,
        attack: int = 5,
        decay: int = 7,
        peak_attack: int = 3,
        peak_decay: int = 4,
        smooth_filter: bool = True,
    ) -> None:
        """Configure and enable the playback-path dynamic range compressor.

        The DRC is a five-section static curve. Reading down from the loudest
        input: the limiter above ``knee1_db``, compressor 1 between knee 1 and
        knee 2, compressor 2 between knee 2 and knee 3, the expander between
        knee 3 and knee 4, and the noise gate below knee 4. Every argument
        defaults to the chip's own reset value, so calling this with no
        arguments enables the datasheet's default curve.

        :param knee1_db: Limiter knee, 0 to -31 dB.
        :param knee2_db: Compressor 1 knee, 0 to -63 dB.
        :param knee3_db: Compressor 2 knee, -18 to -81 dB.
        :param knee4_db: Expander knee, -35 to -98 dB.
        :param limiter_slope: Denominator of the limiter's 1:N ratio: 1 (no
            limiting), 2, 4, 8, 16, 32, 64, or 0 for a hard limit.
        :param compressor1_slope: Same, but only 1, 2, 4, 8, 16 or 0.
        :param compressor2_slope: Same as ``compressor1_slope``.
        :param expander_slope: Numerator of the expander's N:1 ratio: 1, 2 or
            4. (8 is reserved on the capture path.)
        :param noise_gate_slope: Numerator of the noise gate's N:1 ratio: 1, 2,
            4 or 8.
        :param attack: Attack time code, 0-12. The times are multiples of
            Ts = 1/sample_rate -- 0 is Ts, then 3, 7, 15, 31, 63, 127, 255,
            511, 1023, 2047, 4095 and 8191 Ts. They are codes rather than
            milliseconds because this driver deliberately does not know the
            sample rate; see `configure_clocks`.
        :param decay: Decay time code, 0-10: 63 Ts, then 127, 255, 511, 1023,
            2047, 4095, 8191, 16383, 32767 and 65535 Ts.
        :param peak_attack: Peak detector attack code, 0-7, same series as
            ``attack``.
        :param peak_decay: Peak detector release code, 0-7, same series as
            ``decay``.
        :param smooth_filter: Round the corners of the static curve at the
            knee points.

        The DAC block's reset limiter slope is 1:2.

        Note that the DRC sits after the crosstalk/sidetone mixer, at the end
        of the playback path, so a quiet mixed-in signal can be squashed by it.
        """
        self._drc_clock_enable = True
        knee_ip12, knee_ip34, slopes, atkdcy = _drc_words(
            knee1_db,
            knee2_db,
            knee3_db,
            knee4_db,
            limiter_slope,
            compressor1_slope,
            compressor2_slope,
            expander_slope,
            noise_gate_slope,
            attack,
            decay,
            peak_attack,
            peak_decay,
            smooth_filter,
        )
        self._dac_drc_knee_ip34 = knee_ip34
        self._dac_drc_slopes = slopes
        self._dac_drc_atkdcy = atkdcy
        self._dac_drc_knee_ip12 = knee_ip12
