# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_cs42l42`
================================================================================

CircuitPython driver library for Cirrus CS42L42 audio codec


* Author(s): Tim Cocks

Implementation Notes
--------------------

**Hardware:**

* The CS42L42 is a headset codec: a stereo DAC driving a Class H headphone
  amplifier, a mono ADC fed by a headset microphone, jack detection for the
  tip and ring sense lines, and a sample-rate converter on each path.

* **Registers are paged.** The control port carries an 8-bit register address
  within a page, and the page itself is selected by writing register ``0x00``.
  Every register in this module is therefore named by its full 16-bit
  ``0xPPRR`` datasheet address -- ``0x2001`` is register ``0x01`` of page
  ``0x20``

* **CAUTION**: the headphone amplifier can drive sensitive earbuds to levels
  that could damage your hearing. `CS42L42.headphone_output` deliberately
  comes up quiet -- -20 dB of mixer attenuation with the -6 dB full-scale pad
  engaged. Raise `CS42L42.dac_volume` a few dB at a time.



Everything the codec converts is timed by MCLKINT, and MCLKINT comes from the
SCLK pin, either straight through, or multiplied up by the fractional-N PLL.
Out of reset the chip runs from an internal RC oscillator (the RCO) that is
good for I2C and nothing else; `CS42L42.configure_clocks` is what hands it
over to SCLK, and it fails if SCLK is not already running::

    i2s = audiobusio.I2SOut(bit_clock, word_select, data)
    i2s.play(some_looping_sample, loop=True)   # SCLK starts here
    codec = adafruit_cs42l42.CS42L42(board.I2C())
    codec.configure_clocks(sclk_hz=1_536_000)  # now the switch can complete
    codec.configure_asp(sample_rate=48000, bit_depth=16)
    codec.headphone_output = True

The driver does not own the ``I2SOut`` object; you construct it and keep it.

``sclk_hz`` is the bit clock frequency: CircuitPython's
I2S output sends 32 bit clocks per frame, so 48 kHz 16-bit stereo is
``48000 * 32 = 1_536_000``. Only the SCLK frequencies in the datasheet's PLL
table are supported; `SUPPORTED_SCLK_RATES` lists them.

The CS42L42 can also *generate* LRCK from an incoming SCLK, the datasheet calls
this Hybrid-Master mode. It's for boards where a fixed oscillator feeds SCLK and
the microcontroller is an I2S follower on both clocks; pass ``generate_lrck=True``
to `CS42L42.configure_asp` along with the number of bit clocks per frame. Every
other board wants the default, ``generate_lrck=False``.

**Reset**

There is no software reset over I2C -- the RESET pin is the only way back to
the power-on defaults, and the codec must be held in reset while its supplies
come up. Pass a `digitalio.DigitalInOut` on that pin as ``reset_pin`` and the
constructor pulses it for you.

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
* Adafruit's Register library: https://github.com/adafruit/Adafruit_CircuitPython_Register
"""

import time

from adafruit_bus_device.i2c_device import I2CDevice
from adafruit_register.register_accessor import I2CRegisterAccessor
from adafruit_register.register_bit import ROBit, RWBit
from adafruit_register.register_bits import RWBits
from adafruit_register.register_struct import ROUnaryStruct, Struct, UnaryStruct

try:
    from typing import Optional, Tuple

    from busio import I2C
    from digitalio import DigitalInOut
except ImportError:
    pass

__version__ = "1.0.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_CS42L42.git"


class PagedI2CRegisterAccessor(I2CRegisterAccessor):
    """
    RegisterAccessor class for I2C devices whose register space is split into
    pages. Devices using this scheme reach a register in two steps: a page number is
    written to a fixed register, and every access after that is an offset
    within the page that was selected.

    Register addresses given to the descriptors are the two-byte form the
    datasheets print, ``page << 8 | register``: address ``0x2001`` is register
    ``0x01`` of page ``0x20``. That keeps a driver's register constants
    readable against its datasheet while ordinary ``RWBit``, ``RWBits``,
    ``UnaryStruct`` and ``Struct`` descriptors do the work.

    The selected page is remembered, so a run of accesses to one page costs a
    single transaction each; only a change of page adds a second one. Nothing
    else on the bus may write this device's page register behind the
    accessor's back. To recover from that state, call `forget_page`, after any reset
    that returns the device to its power-on page.

    :param I2CDevice i2c_device: I2C device to communicate over
    :param int page_select_register: The register the page number is written
      to. Nearly always ``0x00``, which is the default.
    :param int autoincrement_bit: A bit in the register address byte that asks
      the device to walk through consecutive registers during a multi-byte
      transfer. It is set for reads and writes longer than one byte, and the
      register address is masked to the bits below it. Leave it ``0`` for
      devices that autoincrement unconditionally or not at all.
    """

    def __init__(
        self,
        i2c_device: I2CDevice,
        page_select_register: int = 0x00,
        autoincrement_bit: int = 0x00,
    ):
        super().__init__(i2c_device, address_width=1, lsb_first=False)
        self.page_select_register = page_select_register
        self.autoincrement_bit = autoincrement_bit
        self._register_mask = 0xFF & ~autoincrement_bit
        self._page = None
        self._page_buffer = bytearray(2)

    def forget_page(self) -> None:
        """
        Forget which page is selected, so that the next access selects one
        again. Use after a device reset, or if something else has written
        the device's page register.

        :return: None
        """
        self._page = None

    def select_page(self, address: int, length: int = 1) -> int:
        """
        Select the page ``address`` lives on, if it is not already selected,
        and return the address byte to use within it.

        :param int address: The two-byte page and register address.
        :param int length: The number of data bytes about to be transferred,
          which decides whether the autoincrement bit is set.
        :return: The register address byte, autoincrement bit included.
        """
        page = address >> 8
        if page != self._page:
            self._page_buffer[0] = self.page_select_register
            self._page_buffer[1] = page
            with self.i2c_device as i2c:
                i2c.write(self._page_buffer)
            self._page = page
        register = address & self._register_mask
        if length > 1:
            register |= self.autoincrement_bit
        return register

    def read_register(self, address: int, buffer: bytearray):
        """
        Read register value over I2CDevice, selecting its page first.

        :param int address: The two-byte page and register address to read.
        :param bytearray buffer: Buffer that will be used to read register data into.
        :return: None
        """
        super().read_register(self.select_page(address, len(buffer)), buffer)

    def write_register(self, address: int, buffer: bytearray):
        """
        Write register value over I2CDevice, selecting its page first.

        :param int address: The two-byte page and register address to write.
        :param bytearray buffer: Buffer of data that will be written to the register.
        :return: None
        """
        super().write_register(self.select_page(address, len(buffer)), buffer)


# AD1/AD0 are latched at power-on, so a board's address is fixed by wiring.
_DEFAULT_ADDRESS = 0x48

# The top bit of the register address byte (the MAP byte, section 4.16.1) asks
# the codec to autoincrement through consecutive registers, which is what lets
# a multi-byte `Struct` cover a run of them in one transaction. Register 0x00
# of every page is the page pointer, which is the accessor's default.
_MAP_AUTOINCREMENT = 0x80

# Device ID A-E read 0x42, 0xA4, 0x2x on every CS42L42.
_CHIP_ID = 0x42A4

# -- Registers, named and addressed as the datasheet does -------------------

# Page 0x10, global
_REG_DEVID_AB = 0x1001
_REG_REVID = 0x1005
_REG_FREEZE = 0x1006
_REG_SRC_CTL = 0x1007
_REG_MCLK_CTL = 0x1009

# Page 0x11, power down and plug detect
_REG_PWR_CTL1 = 0x1101
_REG_PWR_CTL2 = 0x1102
_REG_OSC_SWITCH = 0x1107
_REG_OSC_SWITCH_STATUS = 0x1109
_REG_TS_RS_STATUS = 0x1115
_REG_HS_SWITCH_CTL = 0x1121
_REG_HS_CLAMP_DISABLE = 0x1129

# Page 0x12, clocking
_REG_MCLK_SRC_SEL = 0x1201
_REG_FSYNC_PULSE_WIDTH_LB = 0x1203
_REG_FSYNC_PERIOD_LB = 0x1205
_REG_ASP_CLK_CFG = 0x1207
_REG_ASP_FRAME_CFG = 0x1208
_REG_IASRC_CLK_SEL = 0x120A
_REG_OASRC_CLK_SEL = 0x120B
_REG_PLL_DIV_CFG1 = 0x120C

# Page 0x13, interrupt status
_REG_CODEC_INT_STATUS = 0x1308

# Page 0x15, fractional-N PLL
_REG_PLL_CTL1 = 0x1501
_REG_PLL_DIV_FRAC0 = 0x1502
_REG_PLL_DIV_INT = 0x1505
_REG_PLL_CTL3 = 0x1508
_REG_PLL_CAL_RATIO = 0x150A
_REG_PLL_CTL4 = 0x151B

# Page 0x1B, headset interface
_REG_TIP_SENSE_CTL2 = 0x1B73
_REG_MISC_DETECT_CTL = 0x1B74
_REG_MIC_DETECT_CTL1 = 0x1B75
_REG_DETECT_STATUS1 = 0x1B77
_REG_DETECT_STATUS2 = 0x1B78

# Page 0x1D, ADC
_REG_ADC_CTL = 0x1D01
_REG_ADC_VOLUME = 0x1D03

# Page 0x1F, DAC
_REG_DAC_CTL1 = 0x1F01
_REG_DAC_CTL2 = 0x1F06

# Pages 0x20-0x24, headphone amplifier, mixer, equalizer
_REG_HP_CTL = 0x2001
_REG_CLASSH_CTL = 0x2101
_REG_MIXER_CHA_VOL = 0x2301
_REG_MIXER_ADC_VOL = 0x2302
_REG_MIXER_CHB_VOL = 0x2303
_REG_EQ_MUTE = 0x240E

# Pages 0x26-0x2A, sample-rate converters and the audio serial port
_REG_SRC_SDIN_FS = 0x2601
_REG_SRC_SDOUT_FS = 0x2609
_REG_ASP_TX_SIZE_EN = 0x2901
_REG_ASP_TX_CH_EN = 0x2902
_REG_ASP_TX_CH_RES = 0x2903
_REG_ASP_RX_EN = 0x2A01
_REG_ASP_RX_CH1_RES = 0x2A02
_REG_ASP_RX_CH2_RES = 0x2A05

# Whole-register values

# Ex. 5-1 step 3: SRC and ASP powered up, FILT+ not clamped. Bits 7:5 are
# reserved and read 100, which is why this is 0x83 and not 0x03.
_PWR_CTL2_UP = 0x83
# Ex. 5-2 step 6: everything the sequence above turned on, turned off, plus
# DISCHARGE_FILT+ to bleed the FILT+ capacitor.
_PWR_CTL2_DOWN = 0x9C

# Ex. 5-2 step 4: every block down, then PDN_ALL. Everything else in this
# register is reached by clearing bits out of this, so that the two signal
# paths can be powered up in either order without either one switching the
# other off. Bit 1 is reserved and reads 1 throughout.
_PWR_CTL1_ALL_DOWN = 0xFF
# ASP_DAI_PDN | MIXER_PDN | HP_PDN | PDN_ALL: the playback path. Clearing these
# out of _PWR_CTL1_ALL_DOWN gives 0x96, which is Ex. 5-1 step 10 exactly.
_PWR_CTL1_PLAYBACK_MASK = 0x69
# ASP_DAO_PDN | ADC_PDN | PDN_ALL: the capture path.
_PWR_CTL1_CAPTURE_MASK = 0x85

# Ex. 5-1 step 9 leaves the analog mutes clear and FULL_SCALE_VOL set. Bit 0 is
# reserved and reads 1 in every sequence Cirrus publishes for this part.
_HP_CTL_RESERVED = 0x01

# 0x1109: RCO powered down (bit 2 clear) and OSC_SW_SEL_STAT = 10, SCLK or the
# PLL selected as MCLKINT. Note that Ex. 5-1 step 4.2 prints 0x01 for this,
# which is the "RCO selected" encoding and contradicts its own caption; 0x02 is
# what a working switch reads back.
_OSC_SWITCHED = 0x02
_OSC_STATUS_MASK = 0x07

# -- Timing, all bounded ----------------------------------------------------

_RESET_ASSERT_SECONDS = 0.001
# Section 4.17: wait 2.5 ms after RESET is released before writing registers.
_RESET_SETTLE_SECONDS = 0.003
# Section 4.7.1.1: the RCO-to-SCLK switch takes 150 us, during which no I2C
# transaction may start.
_CLOCK_SWITCH_SECONDS = 0.001
_CLOCK_SWITCH_TRIES = 10
# Ex. 5-1 step 11: the headphone amplifier is operational 10 ms after the codec
# is powered up.
_HP_POWER_UP_SECONDS = 0.010
_PDN_DONE_TRIES = 10
_PDN_DONE_SECONDS = 0.001

# -- Scales and lookup tables -----------------------------------------------

# Mixer input volume, 6 bits of attenuation in 1 dB steps. Code 0x3F is not
# -63 dB, it is mute, which is why the usable floor is -62.
_MIXER_MIN_DB = -62.0
_MIXER_MUTE_CODE = 0x3F

# ADC digital volume is a signed 8-bit dB value: +12 dB down to -96 dB in 1 dB
# steps. Codes 0x80-0x9F (-128 to -97) are mute rather than more attenuation.
_ADC_MAX_DB = 12.0
_ADC_MIN_DB = -96.0

# The headphone amplifier's full-scale pad, HP Control bit 1.
_FULL_SCALE_DB = (0.0, -6.0)

# ASP channel resolution codes. 8-bit samples are only valid in the isochronous
# and native modes, so this driver does not offer them.
_BIT_DEPTHS = {16: 0b01, 24: 0b10, 32: 0b11}

# SRC sample-rate codes, shared by SRC_SDIN_FS and SRC_SDOUT_FS. The 11.0295,
# 22.059, 44.118 and 88.236 kHz entries are the rates a 44.1 kHz source clocked
# from a 12 MHz crystal actually produces; they are here so that
# ``sample_rate=44118`` is expressible, and are unlikely to be what you want.
_SAMPLE_RATES = {
    8000: 0x01,
    11025: 0x02,
    11029: 0x03,
    12000: 0x04,
    16000: 0x05,
    22050: 0x06,
    22059: 0x07,
    24000: 0x08,
    32000: 0x09,
    44100: 0x0A,
    44118: 0x0B,
    48000: 0x0C,
    88200: 0x0D,
    88236: 0x0E,
    96000: 0x0F,
    176400: 0x10,
    176472: 0x11,
    192000: 0x12,
}

# FsINT, the rate the converters themselves run at, is MCLKINT divided by a
# fixed ratio: 250 for the 12 MHz family (INTERNAL_FS = 0) and 256 for the
# 12.288/11.2896 MHz family (INTERNAL_FS = 1).
_MCLK_INT_RATES = {
    12_000_000: (48000, 0),
    11_289_600: (44100, 1),
}

# PLL settings, from Table 4-6, as
# ``sclk_hz: (SCLK_PREDIV, PLL_DIV_INT, PLL_DIV_FRAC, PLL_MODE, PLL_DIVOUT,
# PLL_CAL_RATIO)``. ``None`` means the PLL is not needed: SCLK already *is*
# MCLKINT and MCLK_SRC_SEL stays on the SCLK pin.
_PLL_SETTINGS = {
    12_000_000: {
        1_024_000: (0b00, 0xBB, 0x800000, 0b11, 0x10, 125),
        1_536_000: (0b00, 0x7D, 0x000000, 0b11, 0x10, 125),
        2_048_000: (0b00, 0x5D, 0xC00000, 0b11, 0x10, 94),
        3_000_000: (0b00, 0x40, 0x000000, 0b11, 0x10, 128),
        3_072_000: (0b00, 0x3E, 0x800000, 0b11, 0x10, 125),
        4_000_000: (0b00, 0x30, 0x000000, 0b11, 0x10, 96),
        4_096_000: (0b00, 0x2E, 0xE00000, 0b11, 0x10, 94),
        6_000_000: (0b01, 0x40, 0x000000, 0b11, 0x10, 128),
        6_144_000: (0b01, 0x3E, 0x800000, 0b11, 0x10, 125),
        9_600_000: (0b10, 0x50, 0x000000, 0b11, 0x10, 80),
        12_000_000: None,
        12_288_000: (0b10, 0x3E, 0x800000, 0b11, 0x10, 125),
        13_000_000: (0b10, 0x3B, 0x13B13B, 0b11, 0x10, 118),
        19_200_000: (0b11, 0x50, 0x000000, 0b11, 0x10, 80),
        24_000_000: (0b11, 0x40, 0x000000, 0b11, 0x10, 128),
        24_576_000: (0b11, 0x3E, 0x800000, 0b11, 0x10, 125),
    },
    11_289_600: {
        1_024_000: (0b00, 0xAC, 0x440000, 0b01, 0x10, 118),
        1_536_000: (0b00, 0x72, 0xD80000, 0b01, 0x10, 118),
        2_048_000: (0b00, 0x56, 0x220000, 0b01, 0x10, 88),
        2_822_400: (0b00, 0x40, 0x000000, 0b11, 0x10, 128),
        3_000_000: (0b00, 0x3C, 0x361134, 0b11, 0x10, 120),
        3_072_000: (0b00, 0x39, 0x6C0000, 0b01, 0x10, 118),
        4_000_000: (0b00, 0x2D, 0x288CE7, 0b11, 0x10, 90),
        4_096_000: (0b00, 0x2B, 0x110000, 0b01, 0x10, 88),
        5_644_800: (0b01, 0x40, 0x000000, 0b11, 0x10, 128),
        6_000_000: (0b01, 0x3C, 0x361134, 0b11, 0x10, 120),
        6_144_000: (0b01, 0x39, 0x6C0000, 0b01, 0x10, 118),
        9_600_000: (0b10, 0x49, 0x800000, 0b01, 0x10, 150),
        11_289_600: None,
        12_000_000: (0b10, 0x3C, 0x361134, 0b11, 0x10, 120),
        12_288_000: (0b10, 0x39, 0x6C0000, 0b01, 0x10, 118),
        13_000_000: (0b10, 0x39, 0xAB52B5, 0b01, 0x11, 111),
        19_200_000: (0b11, 0x49, 0x800000, 0b01, 0x10, 150),
        22_579_200: (0b11, 0x40, 0x000000, 0b11, 0x10, 128),
        24_000_000: (0b11, 0x3C, 0x361134, 0b11, 0x10, 120),
        24_576_000: (0b11, 0x39, 0x6C0000, 0b01, 0x10, 118),
    },
}

SUPPORTED_SCLK_RATES = tuple(sorted(_PLL_SETTINGS[12_000_000]))
"""Bit clock frequencies the PLL has a published setting for, in Hz.

These are the values `CS42L42.configure_clocks` accepts with its default
``mclk_int``. The 44.1 kHz family (``mclk_int=11_289_600``) additionally
covers 2.8224 MHz, 5.6448 MHz and 22.5792 MHz, and drops nothing.
"""

# Quickstart levels for ``headphone_output = True``. Deliberately quiet: the
# amplifier can drive sensitive earbuds to painful levels, so the -6 dB pad is
# engaged as well.
_QUICKSTART_DAC_VOLUME_DB = -20.0
_QUICKSTART_FULL_SCALE_DB = -6.0

# Quickstart level for ``headset_mic_input = True``.
_QUICKSTART_ADC_VOLUME_DB = 0.0
# Section 4.12: HSBIAS needs time to ramp before the microphone is usable, and
# the ramp rate register decides how much. The default rate is "slow", whose
# ramp delay count is about 90 ms.
_HSBIAS_SETTLE_SECONDS = 0.1


def _db_to_mixer(db: float) -> int:
    """Convert dB to a mixer input volume code, clipping at both ends."""
    db = max(_MIXER_MIN_DB, min(0.0, db))
    return int(round(-db))


def _mixer_to_db(code: int) -> float:
    """Convert a mixer input volume code to dB.

    The mute code is not a point on the dB line, so it reads back as the
    bottom of the scale.
    """
    if code >= _MIXER_MUTE_CODE:
        return _MIXER_MIN_DB
    return -float(code) if code else 0.0


def _db_to_adc(db: float) -> int:
    """Convert dB to an ADC volume code, clipping at both ends."""
    db = max(_ADC_MIN_DB, min(_ADC_MAX_DB, db))
    return int(round(db)) & 0xFF


def _adc_to_db(code: int) -> float:
    """Convert an ADC volume code to dB, reading mute codes as the floor."""
    if code > 0x7F:
        code -= 0x100
    return float(max(_ADC_MIN_DB, code))


def _sample_rate_code(sample_rate: int) -> int:
    """Look a sample rate up in the SRC rate table."""
    if sample_rate not in _SAMPLE_RATES:
        raise ValueError(f"sample_rate must be one of {sorted(_SAMPLE_RATES)}")
    return _SAMPLE_RATES[sample_rate]


def _asrc_clock_select(sample_rate: int) -> int:
    """The ASRC MCLKINT encoding for a serial-port rate, from Table 4-21.

    The rate converters need an MCLK of at least 125 times the higher of their
    two rates, and want the closest one above that: 6 MHz up to 48 kHz, then
    12 MHz, then 24 MHz.
    """
    if sample_rate <= 48000:
        return 0b00
    if sample_rate <= 96000:
        return 0b01
    return 0b10


class CS42L42:
    """Driver for the Cirrus Logic CS42L42 headset codec.

    :param i2c: The I2C bus the codec is connected to.
    :param address: The I2C device address. AD1 and AD0 are latched at power
        on, so this is fixed by the board's wiring; defaults to ``0x48``.
    :param reset_pin: An output `digitalio.DigitalInOut` on the codec's active
        low RESET pin. If given, the codec is reset during construction. The
        driver does not deinitialize the pin.

    The codec must have a running bit clock before `configure_clocks` is
    called; see the module documentation for the ordering.
    """

    chip_id = ROUnaryStruct(_REG_DEVID_AB, ">H")
    """Device ID A through D, which always reads ``0x42A4``."""

    revision = ROUnaryStruct(_REG_REVID, "<B")
    """The analog and metal revision IDs, packed one per nibble."""

    # -- Power ------------------------------------------------------------
    # The power-down bits are active high: a set bit means powered *down*, so
    # every property that wraps one inverts it.
    _pwr_ctl1 = UnaryStruct(_REG_PWR_CTL1, "<B")
    _pwr_ctl2 = UnaryStruct(_REG_PWR_CTL2, "<B")
    _pdn_all = RWBit(_REG_PWR_CTL1, 0)
    _adc_pdn = RWBit(_REG_PWR_CTL1, 2)
    _hp_pdn = RWBit(_REG_PWR_CTL1, 3)
    _eq_pdn = RWBit(_REG_PWR_CTL1, 4)
    _mixer_pdn = RWBit(_REG_PWR_CTL1, 5)
    _asp_dai_pdn = RWBit(_REG_PWR_CTL1, 6)
    _asp_dao_pdn = RWBit(_REG_PWR_CTL1, 7)
    _pdn_done = ROBit(_REG_CODEC_INT_STATUS, 0)
    _freeze = RWBit(_REG_FREEZE, 0)

    # -- Clocking ---------------------------------------------------------
    _internal_fs = RWBit(_REG_MCLK_CTL, 1)
    _mclk_src_sel = RWBit(_REG_MCLK_SRC_SEL, 0)
    _mclk_div = RWBit(_REG_MCLK_SRC_SEL, 1)
    _sclk_present = RWBit(_REG_OSC_SWITCH, 0)
    _osc_switch_status = ROUnaryStruct(_REG_OSC_SWITCH_STATUS, "<B")
    _sclk_prediv = RWBits(2, _REG_PLL_DIV_CFG1, 0)
    _iasrc_clk_sel = RWBits(2, _REG_IASRC_CLK_SEL, 0)
    _oasrc_clk_sel = RWBits(2, _REG_OASRC_CLK_SEL, 0)

    _pll_start = RWBit(_REG_PLL_CTL1, 0)
    # PLL_DIV_FRAC is 24 bits spread over three consecutive registers, least
    # significant byte first, which one autoincrementing write covers.
    _pll_div_frac = Struct(_REG_PLL_DIV_FRAC0, "<BBB")
    _pll_div_int = UnaryStruct(_REG_PLL_DIV_INT, "<B")
    _pll_divout = UnaryStruct(_REG_PLL_CTL3, "<B")
    _pll_cal_ratio = UnaryStruct(_REG_PLL_CAL_RATIO, "<B")
    _pll_mode = RWBits(2, _REG_PLL_CTL4, 0)

    # -- Audio serial port -------------------------------------------------
    _asp_clk_cfg = UnaryStruct(_REG_ASP_CLK_CFG, "<B")
    _asp_frame_cfg = UnaryStruct(_REG_ASP_FRAME_CFG, "<B")
    _asp_sclk_enable = RWBit(_REG_ASP_CLK_CFG, 5)
    _asp_hybrid_mode = RWBit(_REG_ASP_CLK_CFG, 4)
    # FSYNC period and pulse width are 12- and 11-bit fields, each split over a
    # lower and an upper byte in consecutive registers.
    _fsync_period = Struct(_REG_FSYNC_PERIOD_LB, "<BB")
    _fsync_pulse_width = Struct(_REG_FSYNC_PULSE_WIDTH_LB, "<BB")
    _asp_rx_enable = UnaryStruct(_REG_ASP_RX_EN, "<B")
    _asp_rx_ch1_res = RWBits(2, _REG_ASP_RX_CH1_RES, 0)
    _asp_rx_ch2_res = RWBits(2, _REG_ASP_RX_CH2_RES, 0)
    _asp_rx_ch1_phase = RWBit(_REG_ASP_RX_CH1_RES, 6)
    _asp_rx_ch2_phase = RWBit(_REG_ASP_RX_CH2_RES, 6)
    _asp_tx_enable = RWBit(_REG_ASP_TX_SIZE_EN, 0)
    _asp_tx_ch_enable = RWBits(2, _REG_ASP_TX_CH_EN, 0)
    _asp_tx_ch1_res = RWBits(2, _REG_ASP_TX_CH_RES, 0)
    _asp_tx_ch2_res = RWBits(2, _REG_ASP_TX_CH_RES, 2)

    # -- Sample-rate converters --------------------------------------------
    _src_bypass_dac = RWBit(_REG_SRC_CTL, 1)
    _src_bypass_adc = RWBit(_REG_SRC_CTL, 0)
    _eq_bypass = RWBit(_REG_SRC_CTL, 4)
    _src_sdin_fs = RWBits(5, _REG_SRC_SDIN_FS, 0)
    _src_sdout_fs = RWBits(5, _REG_SRC_SDOUT_FS, 0)

    # -- Volumes and mutes -------------------------------------------------
    _hp_ctl = UnaryStruct(_REG_HP_CTL, "<B")
    _analog_mute_a = RWBit(_REG_HP_CTL, 2)
    _analog_mute_b = RWBit(_REG_HP_CTL, 3)
    _full_scale_vol = RWBit(_REG_HP_CTL, 1)
    _mixer_cha_vol = RWBits(6, _REG_MIXER_CHA_VOL, 0)
    _mixer_chb_vol = RWBits(6, _REG_MIXER_CHB_VOL, 0)
    _mixer_adc_vol = RWBits(6, _REG_MIXER_ADC_VOL, 0)
    _adc_vol = UnaryStruct(_REG_ADC_VOLUME, "<B")
    _adc_digital_boost = RWBit(_REG_ADC_CTL, 0)
    _eq_mute = RWBit(_REG_EQ_MUTE, 0)
    _dac_ctl1 = UnaryStruct(_REG_DAC_CTL1, "<B")
    _dac_ctl2 = UnaryStruct(_REG_DAC_CTL2, "<B")
    _adaptive_power = RWBits(3, _REG_CLASSH_CTL, 0)

    # -- Jack detection -----------------------------------------------------
    _tip_sense = ROBit(_REG_DETECT_STATUS1, 7)
    _detect_status1 = ROUnaryStruct(_REG_DETECT_STATUS1, "<B")
    _detect_status2 = ROUnaryStruct(_REG_DETECT_STATUS2, "<B")
    _ts_rs_status = ROUnaryStruct(_REG_TS_RS_STATUS, "<B")
    _tip_sense_ctl = RWBits(2, _REG_TIP_SENSE_CTL2, 6)
    _tip_sense_debounce = RWBits(2, _REG_TIP_SENSE_CTL2, 0)
    _latch_to_vp = RWBit(_REG_MIC_DETECT_CTL1, 7)
    _detect_mode = RWBits(2, _REG_MISC_DETECT_CTL, 3)
    _hsbias_ctrl = RWBits(2, _REG_MISC_DETECT_CTL, 1)
    _mic_level_detect_pdn = RWBit(_REG_MISC_DETECT_CTL, 0)
    _hs_clamp_disable = RWBit(_REG_HS_CLAMP_DISABLE, 0)
    _hs_switch_ctl = UnaryStruct(_REG_HS_SWITCH_CTL, "<B")

    def __init__(
        self,
        i2c: "I2C",
        address: int = _DEFAULT_ADDRESS,
        reset_pin: "Optional[DigitalInOut]" = None,
    ) -> None:
        self._reset_pin = reset_pin
        self._sclk_hz = 0
        self._mclk_int = 0
        self._sample_rate = 0
        self._bit_depth = 0

        # Before the bus, not after: a codec held in reset does not ACK, and
        # `I2CDevice` probes the address as it is constructed. Boards that
        # park RESET asserted between runs -- the SP-1 does -- would fail that
        # probe with `ValueError: No I2C device at address: 0x48`. Pulsing the
        # pin first only touches `digitalio`, so it is safe this early.
        if reset_pin is not None:
            self._pulse_reset()

        self.register_accessor = PagedI2CRegisterAccessor(
            I2CDevice(i2c, address), autoincrement_bit=_MAP_AUTOINCREMENT
        )

        found_id = self.chip_id
        if found_id != _CHIP_ID:
            raise RuntimeError(
                f"CS42L42 not found at 0x{address:02X}; ID register read 0x{found_id:04X}"
            )

    def reset(self) -> None:
        """Pulse the RESET pin, returning the codec to its power-on defaults.

        Requires a ``reset_pin``; there is no software reset over I2C. The
        codec comes back running from its internal RC oscillator, so
        `configure_clocks` has to be called again afterwards.

        :raises RuntimeError: if the driver was constructed without a reset pin.
        """
        self._pulse_reset()
        # The page pointer is back at whatever a reset leaves it at, and the
        # cached copy in the accessor is now a lie.
        self.register_accessor.forget_page()
        self._sclk_hz = 0
        self._mclk_int = 0
        self._sample_rate = 0
        self._bit_depth = 0

    def _pulse_reset(self) -> None:
        """Assert and release RESET, and wait out section 4.17's settling time.

        Touches nothing but the pin, so `__init__` can call it before the
        register accessor exists.
        """
        if self._reset_pin is None:
            raise RuntimeError("no reset_pin: the CS42L42 has no software reset")
        self._reset_pin.value = False
        time.sleep(_RESET_ASSERT_SECONDS)
        self._reset_pin.value = True
        time.sleep(_RESET_SETTLE_SECONDS)

    # -- Clocking ------------------------------------------------------------

    @property
    def sclk_freq(self) -> Optional[int]:
        """The bit clock frequency, as last set by `configure_clocks`.

        ``None`` before the clocks have been configured, when the codec is
        still running from its internal RC oscillator.

        :getter: Return the configured SCLK frequency in Hz, or None.
        """
        return self._sclk_hz or None

    @property
    def internal_sample_rate(self) -> Optional[int]:
        """FsINT, the rate the converters run at, as set by `configure_clocks`.

        This is not the rate on the wire -- the sample-rate converters sit
        between the two, and `sample_rate` is what the serial port carries.

        :getter: Return the internal sample rate in Hz, or None.
        """
        if not self._mclk_int:
            return None
        return _MCLK_INT_RATES[self._mclk_int][0]

    def configure_clocks(self, sclk_hz: int, mclk_int: int = 12_000_000) -> None:
        """Take MCLKINT from the bit clock, through the PLL if it needs one.

        The bit clock must already be running when this is called. Out of
        reset the codec runs from an internal RC oscillator that is good for
        I2C and nothing else; this is the handover to SCLK, and the codec
        reports whether the switch completed. Construct the ``I2SOut`` object
        and ``play()`` a looping sample first, then call this.

        :param sclk_hz: The bit clock frequency in Hz. This is the bit clock,
            not the sample rate: CircuitPython sends 32 bit clocks per frame,
            so 48 kHz stereo is ``1_536_000``. Must be one of
            `SUPPORTED_SCLK_RATES`.
        :param mclk_int: The internal clock to synthesize, either
            ``12_000_000`` (the default, giving FsINT = 48 kHz) or
            ``11_289_600`` (FsINT = 44.1 kHz). The sample-rate converters
            reconcile FsINT with whatever `configure_asp` is told the serial
            port carries, so the default suits both families.
        :raises ValueError: if there is no published PLL setting for this
            combination.
        :raises RuntimeError: if the codec never switches off its RC
            oscillator, which means SCLK is not running.
        """
        if mclk_int not in _MCLK_INT_RATES:
            raise ValueError(f"mclk_int must be one of {sorted(_MCLK_INT_RATES)}")
        settings = _PLL_SETTINGS[mclk_int]
        if sclk_hz not in settings:
            raise ValueError(
                f"no PLL setting for sclk_hz={sclk_hz} at mclk_int={mclk_int}; "
                + f"supported: {sorted(settings)}"
            )

        # Section 5.1: start from everything powered down with the PLL stopped.
        self._pwr_ctl1 = _PWR_CTL1_ALL_DOWN
        self._pll_start = False
        self._pwr_ctl2 = _PWR_CTL2_UP

        pll = settings[sclk_hz]
        if pll is not None:
            prediv, div_int, div_frac, mode, divout, cal_ratio = pll
            self._sclk_prediv = prediv
            self._pll_divout = divout
            self._pll_div_frac = (
                div_frac & 0xFF,
                (div_frac >> 8) & 0xFF,
                (div_frac >> 16) & 0xFF,
            )
            self._pll_div_int = div_int
            self._pll_cal_ratio = cal_ratio
            self._pll_mode = mode

        # MCLKDIV is only for the 22-24 MHz MCLKINT region, which this driver
        # does not target: both supported MCLKINT values want divide by 1.
        self._mclk_div = False
        self._mclk_src_sel = pll is not None
        self._internal_fs = bool(_MCLK_INT_RATES[mclk_int][1])
        if pll is not None:
            self._pll_start = True

        self._switch_to_sclk()

        self._sclk_hz = sclk_hz
        self._mclk_int = mclk_int

    def _switch_to_sclk(self) -> None:
        """Hand MCLKINT over from the RC oscillator, and confirm it landed."""
        status = 0
        self._sclk_present = True
        # Section 4.7.1.1: the switch takes 150 us, and no I2C transaction may
        # start while it runs. Sleeping first also means the status read below
        # is never the one that races it.
        for _ in range(_CLOCK_SWITCH_TRIES):
            time.sleep(_CLOCK_SWITCH_SECONDS)
            status = self._osc_switch_status
            if status & _OSC_STATUS_MASK == _OSC_SWITCHED:
                return
        raise RuntimeError(
            f"CS42L42 clock switch timed out (0x1109 = 0x{status:02X}); is SCLK running?"
        )

    # -- Audio serial port ---------------------------------------------------

    @property
    def sample_rate(self) -> Optional[int]:
        """The serial port sample rate, as last set by `configure_asp`.

        :getter: Return the configured sample rate in Hz, or None.
        """
        return self._sample_rate or None

    @property
    def bit_depth(self) -> Optional[int]:
        """The I2S word length in bits, as last set by `configure_asp`.

        :getter: Return the configured bit depth, or None.
        """
        return self._bit_depth or None

    def configure_asp(
        self,
        sample_rate: int = 48000,
        bit_depth: int = 16,
        generate_lrck: bool = False,
        sclk_per_frame: int = 64,
        sdin_rising_edge: bool = True,
        use_src: Optional[bool] = None,
    ) -> None:
        """Configure the audio serial port for two-channel I2S.

        Sets up standard Philips framing: a 50/50 duty cycle LRCK, one bit
        clock of frame-start delay, the left channel in the LRCK-low half of
        the frame and the right channel in the high half, and both receive
        channels enabled. `configure_clocks` must have been called first.

        :param sample_rate: The rate the serial port carries, in Hz. Must be
            one of the rates in the datasheet's SRC table -- the usual
            8000 through 192000 -- and need not equal `internal_sample_rate`,
            because the rate converters sit between them.
        :param bit_depth: The I2S word length: 16, 24 or 32. CircuitPython
            sends 16-bit stereo, so leave this at 16.
        :param generate_lrck: Have the codec generate LRCK from the incoming
            SCLK. Leave this False unless the microcontroller is an I2S
            follower on both clocks.
        :param sclk_per_frame: Bit clocks per LRCK frame, both channels
            together. Only used when ``generate_lrck`` is True, where it is
            what sets the LRCK frequency; CircuitPython's own I2S output
            uses 32.
        :param sdin_rising_edge: Latch SDIN on the rising edge of SCLK, which
            is what a transmitter launching data on the falling edge -- the I2S
            convention, and what CircuitPython does -- needs. The codec's reset
            default is the falling edge, so this is not the register default.
        :param use_src: Run the incoming stream through the sample-rate
            converter. The default, ``None``, bypasses it when the serial port
            rate already equals FsINT and engages it when it does not, which is
            the only case where it has anything to do.
        """
        if not self._mclk_int:
            raise RuntimeError("call configure_clocks() before configure_asp()")
        if bit_depth not in _BIT_DEPTHS:
            raise ValueError(f"bit_depth must be one of {sorted(_BIT_DEPTHS)}")
        rate_code = _sample_rate_code(sample_rate)
        if generate_lrck and not 1 <= sclk_per_frame <= 4096:
            raise ValueError("sclk_per_frame must be 1 to 4096")

        internal_rate = self.internal_sample_rate
        if use_src is None:
            use_src = sample_rate != internal_rate
        if not use_src and sample_rate != internal_rate:
            raise ValueError(f"use_src=False needs sample_rate to equal FsINT ({internal_rate} Hz)")

        self._sample_rate = sample_rate
        self._bit_depth = bit_depth

        # The rate converters are clocked from their own division of MCLKINT,
        # picked by the rate the serial port carries. The SP-1's published
        # sequence uses the 12 MHz encoding at 48 kHz, which also works; 6 MHz
        # is what Table 4-21 asks for.
        asrc_clock = _asrc_clock_select(sample_rate)
        self._iasrc_clk_sel = asrc_clock
        self._oasrc_clk_sel = asrc_clock
        self._src_sdin_fs = rate_code
        self._src_sdout_fs = rate_code
        self._eq_bypass = True
        self._src_bypass_dac = not use_src
        self._src_bypass_adc = not use_src

        # LRCK framing. In 50/50 Mode the period and pulse width registers are
        # ignored, but the codec still divides SCLK by the period to produce
        # LRCK, so it is written whenever the codec is the one generating the
        # frame.
        if generate_lrck:
            period = sclk_per_frame - 1
            self._fsync_period = (period & 0xFF, (period >> 8) & 0x0F)
            half = max(sclk_per_frame // 2, 1) - 1
            self._fsync_pulse_width = (half & 0xFF, (half >> 8) & 0x07)

        # ASP_STP: the frame begins on the rising edge of LRCK. ASP_5050: fixed
        # 50% duty cycle, so each channel owns half a frame. ASP_FSD = 010: one
        # bit clock of frame-start delay, which is what makes this I2S rather
        # than left-justified framing.
        self._asp_frame_cfg = 0x1A
        # ASP_SCLK_EN, plus the LRCK-generation bit and the SDIN sample edge.
        # The ADC path's polarity bit is left at its default: the codec launches
        # SDOUT on the rising edge, which a receiver latching on the falling
        # edge reads correctly.
        clk_cfg = 0x20
        if generate_lrck:
            clk_cfg |= 0x10
        if sdin_rising_edge:
            clk_cfg |= 0x04
        self._asp_clk_cfg = clk_cfg

        depth_code = _BIT_DEPTHS[bit_depth]
        self._asp_rx_ch1_res = depth_code
        self._asp_rx_ch2_res = depth_code
        self._asp_tx_ch1_res = depth_code
        self._asp_tx_ch2_res = depth_code
        # Active phase: channel 1 is valid while LRCK is low (the left channel
        # in a standard I2S frame) and channel 2 while it is high.
        self._asp_rx_ch1_phase = False
        self._asp_rx_ch2_phase = True
        # ASP_RX0_CH[2:1]_EN: the two DAI0 receive channels the DAC listens to.
        self._asp_rx_enable = 0x0C

    @property
    def bit_clock_enabled(self) -> bool:
        """Whether the serial port is clocked at all.

        Clearing this is the first half of stopping the bus safely: mute the
        outputs, disable the port, and only then stop the bit clock.

        :getter: True if the ASP is enabled.
        :setter: Enable or disable the ASP.
        """
        return self._asp_sclk_enable

    @bit_clock_enabled.setter
    def bit_clock_enabled(self, enabled: bool) -> None:
        self._asp_sclk_enable = enabled

    # -- Playback path -------------------------------------------------------

    @property
    def headphone_output(self) -> bool:
        """Headphone output helper with quickstart default settings.

        Setting this to True powers up the DAC-to-headphone chain the way the
        datasheet's own playback sequence does, and picks levels intended for
        quiet listening on sensitive low-impedance earbuds:

        * `dac_volume` = -20 dB
        * `full_scale_volume` = -6 dB
        * the microphone's contribution to the mixer muted

        Setting it to False powers the headphone amplifier and the DAC back
        down, leaving the microphone path alone.

        `configure_clocks` and `configure_asp` must have been called first --
        with no MCLKINT the DAC has no clock to run from.

        :getter: True if the headphone amplifier and DAC are powered.
        :setter: **This sets several properties at once**, including both mixer
            volumes, the analog mutes, the full-scale pad and the codec's
            power-down register, and it blocks for 10 ms while the headphone
            amplifier comes up.
        """
        return not self._pdn_all and not self._hp_pdn

    @headphone_output.setter
    def headphone_output(self, enabled: bool) -> None:
        if not enabled:
            self.muted = True
            self._hp_pdn = True
            return

        self._pwr_ctl2 = _PWR_CTL2_UP
        self._dac_ctl1 = 0x00  # neither DAC channel inverted
        # The equalizer stays powered down, so hold its input at digital zero
        # rather than leaving whatever the mixer feeds it running into a block
        # with pass-through coefficients it has never been given.
        self._eq_mute = True
        self.mic_mix_volume = _MIXER_MIN_DB
        self.dac_volume = _QUICKSTART_DAC_VOLUME_DB
        self.full_scale_volume = _QUICKSTART_FULL_SCALE_DB
        self.muted = False
        # Clear only this path's power-down bits, so that bringing the
        # headphones up after the microphone does not switch the microphone
        # off. Whichever order the two are enabled in, the register ends at
        # 0x12; playback alone ends at Ex. 5-1's 0x96.
        self._pwr_ctl1 = (self._pwr_ctl1 & ~_PWR_CTL1_PLAYBACK_MASK) | 0x02
        time.sleep(_HP_POWER_UP_SECONDS)

    @property
    def dac_volume(self) -> float:
        """The mixer input volume in dB, 0 dB down to -62 dB in 1 dB steps.

        This is the digital attenuation applied ahead of the DAC, and it is the
        volume control to reach for: the only analog level control the
        headphone amplifier has is the 6 dB step in `full_scale_volume`.
        Setting it writes both channels.

        :getter: Return channel A's volume in dB.
        :setter: Set both channels to the same volume in dB, clipped to range.
        """
        return _mixer_to_db(self._mixer_cha_vol)

    @dac_volume.setter
    def dac_volume(self, db: float) -> None:
        code = _db_to_mixer(db)
        self._mixer_cha_vol = code
        self._mixer_chb_vol = code

    @property
    def channel_a_volume(self) -> float:
        """Channel A's mixer input volume in dB, for an unbalanced pair.

        Channel A carries the first channel of the serial port frame, which is
        the left channel of a standard I2S stream. Same scale as `dac_volume`.

        :getter: Return channel A's volume in dB.
        :setter: Set channel A's volume in dB, clipped to range.
        """
        return _mixer_to_db(self._mixer_cha_vol)

    @channel_a_volume.setter
    def channel_a_volume(self, db: float) -> None:
        self._mixer_cha_vol = _db_to_mixer(db)

    @property
    def channel_b_volume(self) -> float:
        """Channel B's mixer input volume in dB. See `channel_a_volume`.

        :getter: Return channel B's volume in dB.
        :setter: Set channel B's volume in dB, clipped to range.
        """
        return _mixer_to_db(self._mixer_chb_vol)

    @channel_b_volume.setter
    def channel_b_volume(self, db: float) -> None:
        self._mixer_chb_vol = _db_to_mixer(db)

    @property
    def mic_mix_volume(self) -> float:
        """How much of the headset microphone is mixed into the headphones.

        This is the sidetone path -- the ADC's own signal folded back into the
        headphone mixer. Same scale as `dac_volume`, and the bottom of that
        scale is where both quickstarts leave it.

        :getter: Return the mixer's ADC input volume in dB.
        :setter: Set the mixer's ADC input volume in dB, clipped to range.
        """
        return _mixer_to_db(self._mixer_adc_vol)

    @mic_mix_volume.setter
    def mic_mix_volume(self, db: float) -> None:
        # The floor of this scale is -62 dB, but the code above it is a real
        # mute, and silence is what a sidetone nobody asked for should be.
        code = _db_to_mixer(db)
        if code >= _MIXER_MUTE_CODE - 1:
            code = _MIXER_MUTE_CODE
        self._mixer_adc_vol = code

    @property
    def muted(self) -> bool:
        """The headphone amplifier's analog mutes, both channels.

        :getter: True if both channels are muted.
        :setter: Mute or unmute both channels.
        """
        return self._analog_mute_a and self._analog_mute_b

    @muted.setter
    def muted(self, mute: bool) -> None:
        # One read-modify-write for both bits, so that muting cannot lose a
        # race with something else in this register -- the full-scale pad in
        # particular lives two bits along.
        value = self._hp_ctl & ~0x0C
        if mute:
            value |= 0x0C
        self._hp_ctl = value | _HP_CTL_RESERVED

    @property
    def full_scale_volume(self) -> float:
        """The headphone amplifier's full-scale output level: 0 or -6 dB.

        An analog pad on the output stage, so it stacks with the digital
        `dac_volume` rather than replacing it. -6 dB is the datasheet's
        recommendation for loads near 15 ohms, and the safe setting for a first
        listen on unknown headphones.

        The datasheet asks for the output to be muted across a change of this
        bit, which the setter does: if the amplifier is live it mutes, moves
        the bit and unmutes again.

        :getter: Return 0.0 or -6.0.
        :setter: Set 0 or -6 dB. Other values raise ValueError.
        """
        return _FULL_SCALE_DB[self._full_scale_vol]

    @full_scale_volume.setter
    def full_scale_volume(self, db: float) -> None:
        if db not in _FULL_SCALE_DB:
            raise ValueError(f"full_scale_volume must be one of {list(_FULL_SCALE_DB)}")
        padded = db == _FULL_SCALE_DB[1]
        if padded == self._full_scale_vol:
            return
        was_live = not self.muted
        if was_live:
            self.muted = True
        self._full_scale_vol = padded
        if was_live:
            self.muted = False

    @property
    def adaptive_power(self) -> int:
        """The Class H power scheme behind the headphone amplifier.

        ``0b111``, the default, adapts the amplifier's supply to the signal
        level, which is what makes this a Class H part. The fixed modes
        ``0b001`` through ``0b100`` trade that efficiency for a supply that
        never moves; see the datasheet's ADPTPWR table.

        :getter: Return the ADPTPWR field.
        :setter: Set the ADPTPWR field.
        """
        return self._adaptive_power

    @adaptive_power.setter
    def adaptive_power(self, mode: int) -> None:
        if not 1 <= mode <= 7 or mode in {5, 6}:
            raise ValueError("adaptive_power must be 1-4 or 7")
        self._adaptive_power = mode

    @property
    def settings_frozen(self) -> bool:
        """Whether volume and power-down changes are being held back.

        With this set, writes to the volume and power-down registers are
        staged rather than applied, and they all take effect together when it
        is cleared. Only use it once everything in use has finished powering
        up: a block that is still coming up when it is set can apply its
        change the moment it finishes, ungated.

        :getter: True if changes are being held.
        :setter: Hold changes, or apply everything staged so far.
        """
        return self._freeze

    @settings_frozen.setter
    def settings_frozen(self, frozen: bool) -> None:
        self._freeze = frozen

    @property
    def headphone_load_10nf(self) -> bool:
        """Whether the headphone amplifier is in its 10 nF load mode.

        Cables long enough to present more than about 1 nF of capacitance need
        this; the default 1 nF mode is right for ordinary headphones.

        :getter: True if the amplifier is in 10 nF Mode.
        :setter: Select the 1 nF or 10 nF load mode. The headphone path is
            powered down across the change, as the datasheet requires, and left
            in the state it was found in.
        """
        return bool(self._dac_ctl2 & 0x08)

    @headphone_load_10nf.setter
    def headphone_load_10nf(self, ten_nf: bool) -> None:
        was_powered = not self._hp_pdn
        self._hp_pdn = True
        value = self._dac_ctl2 & ~0x08
        self._dac_ctl2 = value | (0x08 if ten_nf else 0x00)
        if was_powered:
            self._hp_pdn = False
            time.sleep(_HP_POWER_UP_SECONDS)

    # -- Capture path --------------------------------------------------------

    @property
    def headset_mic_input(self) -> bool:
        """Headset microphone helper with quickstart default settings.

        Setting this to True powers up the microphone-to-ADC chain -- HSBIAS at
        2.0 V, the detect block in Normal Mode, the ADC, and the serial port's
        transmit channel -- waits for the bias to ramp, and leaves `adc_volume`
        at 0 dB. The microphone is *not* mixed into the headphones; raise
        `mic_mix_volume` for that.

        Setting it to False powers the microphone path back down, leaving the
        headphone path alone.

        `configure_clocks` and `configure_asp` must have been called first.

        :getter: True if the ADC is powered.
        :setter: **This sets several properties at once**, including `hsbias`,
            `adc_volume` and the ASP transmit enables, and it blocks for about
            0.1 s while the bias ramps.
        """
        return not self._pdn_all and not self._adc_pdn

    @headset_mic_input.setter
    def headset_mic_input(self, enabled: bool) -> None:
        if not enabled:
            self._asp_tx_enable = False
            self._asp_tx_ch_enable = 0b00
            self._adc_pdn = True
            self._asp_dao_pdn = True
            self.hsbias = 0.0
            return

        # LATCH_TO_VP has to be set before the detect-block fields below can be
        # written at all: they live in the VP supply domain, and this is the
        # bit that makes writes to them transparent.
        self._latch_to_vp = True
        self._detect_mode = 0b11  # Normal Mode, high-performance HSBIAS
        self.hsbias = 2.0
        self.adc_volume = _QUICKSTART_ADC_VOLUME_DB
        # ASP_TX_CH[2:1]_EN, then the port's output driver.
        self._asp_tx_ch_enable = 0b11
        self._asp_tx_enable = True
        # ASP_DAO_PDN, ADC_PDN and PDN_ALL, without disturbing the playback
        # path's bits. See the note in `headphone_output`.
        self._pwr_ctl1 = (self._pwr_ctl1 & ~_PWR_CTL1_CAPTURE_MASK) | 0x02
        time.sleep(_HSBIAS_SETTLE_SECONDS)

    @property
    def adc_volume(self) -> float:
        """The ADC digital volume in dB, +12 dB down to -96 dB in 1 dB steps.

        This scales what the ADC has already produced, so unlike `mic_boost` it
        cannot improve the signal-to-noise ratio of a capture.

        :getter: Return the ADC volume in dB.
        :setter: Set the ADC volume in dB, clipped to range.
        """
        return _adc_to_db(self._adc_vol)

    @adc_volume.setter
    def adc_volume(self, db: float) -> None:
        self._adc_vol = _db_to_adc(db)

    @property
    def mic_boost(self) -> bool:
        """The ADC's +20 dB digital boost.

        :getter: True if the boost is applied.
        :setter: Apply or remove the boost.
        """
        return self._adc_digital_boost

    @mic_boost.setter
    def mic_boost(self, enabled: bool) -> None:
        self._adc_digital_boost = enabled

    @property
    def hsbias(self) -> float:
        """The headset bias voltage: 0.0, 2.0 or 2.7 V.

        This is what powers the microphone in a four-pole headset, and it is
        also what the detect circuits measure. 0.0 V is a weak ground rather
        than an open circuit.

        :getter: Return the configured bias voltage.
        :setter: Set the bias voltage. Other values raise ValueError. Mute the
            headphone path first if it is live: the datasheet warns that
            changing this while the headset path is active is audible.
        """
        return (0.0, 0.0, 2.0, 2.7)[self._hsbias_ctrl]

    @hsbias.setter
    def hsbias(self, volts: float) -> None:
        codes = {0.0: 0b01, 2.0: 0b10, 2.7: 0b11}
        if volts not in codes:
            raise ValueError(f"hsbias must be one of {sorted(codes)}")
        self._latch_to_vp = True
        self._hsbias_ctrl = codes[volts]

    # -- Jack detection ------------------------------------------------------

    @property
    def headset_switches(self) -> int:
        """The headset switch matrix, Headset Switch Control (0x1121), raw.

        Which of the HS3 and HS4 pins is tied to ground, to the bias reference
        and to the bias filter is a property of how the jack is wired -- CTIA
        and OMTP headsets swap the microphone and ground contacts -- so there
        is no value here that suits every board. The reset default, 0xF3,
        connects both pins to their references.

        :getter: Return the register value.
        :setter: Write the register value.
        """
        return self._hs_switch_ctl

    @headset_switches.setter
    def headset_switches(self, value: int) -> None:
        self._latch_to_vp = True
        self._hs_switch_ctl = value

    @property
    def headset_clamps(self) -> bool:
        """The ground-noise clamps on the headset pins.

        The clamps suppress ground noise while the codec is powered down, at
        the cost of loading the pins; the datasheet's standby example lifts
        them. They are connected out of reset.

        :getter: True if the clamps are connected.
        :setter: Connect or disconnect the clamps.
        """
        return not self._hs_clamp_disable

    @headset_clamps.setter
    def headset_clamps(self, connected: bool) -> None:
        self._hs_clamp_disable = not connected

    def enable_tip_sense(self, debounce_ms: int = 500) -> None:
        """Turn on the tip-sense circuit that `headphone_detected` reads.

        Out of reset the circuit is powered down and the status bit reports
        nothing, so this has to be called before the detect status means
        anything.

        :param debounce_ms: How long the tip must stay unplugged before the
            status bit follows it: 0, 200, 500 or 1000 ms. This is a floor on
            how quickly `headphone_detected` can react, and it is deliberately
            long -- a jack being pushed in bounces for a while.
        """
        debounce = {0: 0b00, 200: 0b01, 500: 0b10, 1000: 0b11}
        if debounce_ms not in debounce:
            raise ValueError(f"debounce_ms must be one of {sorted(debounce)}")
        # Both of these registers are in the VP supply domain.
        self._latch_to_vp = True
        self._tip_sense_debounce = debounce[debounce_ms]
        # Short detect, with the weak pull-up the tip is measured against.
        self._tip_sense_ctl = 0b11

    @property
    def headphone_detected(self) -> bool:
        """Whether something is plugged into the headphone jack.

        Reads the debounced tip-sense status, so it lags the jack by the
        `enable_tip_sense` debounce time plus however long a hand takes. It
        reports nothing at all until `enable_tip_sense` has been called.

        :getter: True if the tip sense circuit sees a plug.
        """
        return self._tip_sense

    @property
    def mic_level_detect(self) -> bool:
        """The DC level detector behind `headset_detected`.

        It is powered down out of reset, and neither quickstart turns it on:
        the datasheet warns that leaving it enabled while the headset input is
        live degrades the microphone's noise performance. Turn it on, give it
        the 11 ms it needs to settle, read `headset_detected`, turn it off.

        :getter: True if the level detector is powered.
        :setter: Power the level detector up or down.
        """
        return not self._mic_level_detect_pdn

    @mic_level_detect.setter
    def mic_level_detect(self, enabled: bool) -> None:
        self._latch_to_vp = True
        self._mic_level_detect_pdn = not enabled

    @property
    def headset_detected(self) -> bool:
        """Whether the plug in the jack has a microphone on its second ring.

        HS_TRUE: the voltage on HSBIAS_IN has been pulled below the headset
        detect threshold, which a microphone element does and an open ring does
        not. Needs `hsbias` powered and `mic_level_detect` on to mean anything.

        :getter: True if a headset microphone is detected.
        """
        return bool(self._detect_status2 & 0x02)

    @property
    def button_pressed(self) -> bool:
        """Whether the headset's S0 (call/play) button is held down.

        The button shorts the microphone element out, which the codec sees as
        HSBIAS_IN dropping below its short-detect threshold. Requires
        ``headset_mic_input`` -- the detect block has to be in Normal Mode --
        and is not debounced, so poll it a few times before believing an edge.

        :getter: True while the button is pressed.
        """
        return bool(self._detect_status2 & 0x01)

    @property
    def detect_status(self) -> Tuple[int, int, int]:
        """The three raw detect registers, for arguing with the above.

        ``(0x1B77, 0x1B78, 0x1115)``: detect status 1 and 2, and the debounced
        tip and ring sense plug/unplug indicators.

        :getter: Return the three register values.
        """
        return (self._detect_status1, self._detect_status2, self._ts_rs_status)

    def register_read(self, address: int) -> int:
        """Read one register, by its 16-bit ``0xPPRR`` datasheet address.

        An escape hatch for the parts of this codec the driver does not wrap --
        the equalizer's coefficient interface, the interrupt masks, S/PDIF.

        :param address: The page and register address, e.g. ``0x2001``.
        """
        buffer = bytearray(1)
        self.register_accessor.read_register(address, buffer)
        return buffer[0]

    def register_write(self, address: int, value: int) -> None:
        """Write one register, by its 16-bit ``0xPPRR`` datasheet address.

        :param address: The page and register address, e.g. ``0x2001``.
        :param value: The byte to write.
        """
        self.register_accessor.write_register(address, bytes((value,)))

    # -- Shutdown ------------------------------------------------------------

    def power_down(self) -> None:
        """Run the datasheet's power-down sequence, quietly.

        Mutes the mixer and the amplifier, stops the serial port, powers every
        block down and then the codec itself, and finally clamps the FILT+
        capacitor to ground. Returns once the codec confirms it is down, or
        after about 10 ms of asking.

        The bit clock may be stopped after this returns, and only after: the
        codec needs SCLK running to switch back to its own oscillator, which is
        what `power_down` does before the last register writes. Call
        `configure_clocks` and `configure_asp` again to bring it back.
        """
        self._mixer_cha_vol = _MIXER_MUTE_CODE
        self._mixer_adc_vol = _MIXER_MUTE_CODE
        self._mixer_chb_vol = _MIXER_MUTE_CODE
        self.muted = True
        self._asp_rx_enable = 0x00
        self._asp_sclk_enable = False

        # Back to the RC oscillator while SCLK is still running, so that I2C
        # keeps working after the caller stops the clock (Section 4.7.1.2).
        self._sclk_present = False
        time.sleep(_CLOCK_SWITCH_SECONDS)
        self._pll_start = False

        self._pwr_ctl1 = _PWR_CTL1_ALL_DOWN
        for _ in range(_PDN_DONE_TRIES):
            if self._pdn_done:
                break
            time.sleep(_PDN_DONE_SECONDS)
        self._pwr_ctl2 = _PWR_CTL2_DOWN
        self._sclk_hz = 0
        self._mclk_int = 0
