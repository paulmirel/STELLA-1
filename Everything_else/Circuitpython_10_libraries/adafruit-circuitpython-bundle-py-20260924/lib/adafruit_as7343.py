# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_as7343`
================================================================================

CircuitPython driver for the ams OSRAM AS7343 14-channel spectral sensor.


* Author(s): Tim Cocks

Implementation Notes
--------------------

**Hardware:**

* `Adafruit AS7343 14-Channel Multi-Spectral Sensor Breakout <https://www.adafruit.com/product/6477>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
* Adafruit's Register library: https://github.com/adafruit/Adafruit_CircuitPython_Register
"""

__version__ = "1.0.3"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_AS7343.git"

# imports
import time

from adafruit_bus_device import i2c_device
from adafruit_register.i2c_bit import ROBit, RWBit
from adafruit_register.i2c_bits import RWBits
from adafruit_register.i2c_struct import Struct, UnaryStruct
from adafruit_register.i2c_struct_array import StructArray
from micropython import const

try:
    from typing import List, Optional, Tuple

    import busio
except ImportError:
    pass

# ── I2C address ──────────────────────────────────────────────────────────────
_AS7343_I2C_ADDRESS = const(0x39)

# ── Chip identification ───────────────────────────────────────────────────────
_AS7343_CHIP_ID = const(0x81)

# ── Register addresses — Bank 1 (REG_BANK=1, accessed at 0x58–0x6B) ──────────
_AS7343_AUXID = const(0x58)  # Auxiliary ID (bits 3:0)
_AS7343_REVID = const(0x59)  # Revision ID  (bits 2:0)
_AS7343_ID = const(0x5A)  # Part ID (should read 0x81)
_AS7343_CFG10 = const(0x65)  # FD_PERS configuration
_AS7343_CFG12 = const(0x66)  # SP_TH_CH — threshold channel select (bits 2:0)
_AS7343_GPIO = const(0x6B)  # GPIO control register

# ── Register addresses — Bank 0 (REG_BANK=0, default, accessed at 0x80+) ─────
_AS7343_ENABLE = const(0x80)  # Main enable register
_AS7343_ATIME = const(0x81)  # Integration time multiplier (0–255)
_AS7343_WTIME = const(0x83)  # Wait time between measurements (0–255)
_AS7343_SP_TH_L = const(0x84)  # Spectral low threshold, 16-bit little-endian
_AS7343_SP_TH_H = const(0x86)  # Spectral high threshold, 16-bit little-endian
_AS7343_STATUS2 = const(0x90)  # Status 2 (AVALID, saturation flags)
_AS7343_STATUS3 = const(0x91)  # Status 3 (interrupt source)
_AS7343_STATUS = const(0x93)  # Main status register (write-to-clear)
_AS7343_ASTATUS = const(0x94)  # ADC status — read to latch channel data
_AS7343_DATA_0_L = const(0x95)  # First channel data register (low byte)
_AS7343_STATUS5 = const(0xBB)  # Status 5 (SINT_FD, SINT_SMUX)
_AS7343_STATUS4 = const(0xBC)  # Status 4 (FIFO_OV, triggers)
_AS7343_CFG0 = const(0xBF)  # Config 0 (REG_BANK bit 4, LOW_POWER bit 5)
_AS7343_CFG1 = const(0xC6)  # Config 1 (AGAIN gain, bits 4:0)
_AS7343_CFG3 = const(0xC7)  # Config 3 (SAI — sleep after interrupt)
_AS7343_CFG8 = const(0xC9)  # Config 8 (FIFO_TH)
_AS7343_CFG9 = const(0xCA)  # Config 9 (SIEN_FD, SIEN_SMUX)
_AS7343_LED = const(0xCD)  # LED control (bit 7 = act, bits 6:0 = drive)
_AS7343_PERS = const(0xCF)  # Persistence filter (bits 3:0)
_AS7343_ASTEP_L = const(0xD4)  # Integration step size, 16-bit little-endian
_AS7343_CFG20 = const(0xD6)  # Config 20 (auto_smux bits 6:5, FD_FIFO_8b bit 4)
_AS7343_AGC_GAIN_MAX = const(0xD7)  # AGC maximum gain
_AS7343_AZ_CONFIG = const(0xDE)  # Auto-zero frequency (0–255)
_AS7343_FD_CFG0 = const(0xDF)  # Flicker detection config 0
_AS7343_FD_TIME_1 = const(0xE0)  # Flicker detection time LSB
_AS7343_FD_TIME_2 = const(0xE2)  # Flicker detection time MSB + gain
_AS7343_FD_STATUS = const(0xE3)  # Flicker detection status
_AS7343_INTENAB = const(0xF9)  # Interrupt enable register
_AS7343_CONTROL = const(0xFA)  # Control register (SW_RESET bit 3)
_AS7343_FIFO_MAP = const(0xFC)  # FIFO channel mapping
_AS7343_FIFO_LVL = const(0xFD)  # FIFO level
_AS7343_FDATA_L = const(0xFE)  # FIFO data low byte
_AS7343_FDATA_H = const(0xFF)  # FIFO data high byte

# CFG6 sits at 0xF5 — SMUX_CMD bits 4:3 trigger a SMUX re-configuration when written
_AS7343_CFG6 = const(0xF5)


# ── CV helper (enum base class) ───────────────────────────────────────────────
class CV:
    """Constant-value helper used as an enum base class.

    Subclasses define integer class attributes; :meth:`is_valid` and
    :meth:`get_name` provide validation and reverse-lookup.
    """

    @classmethod
    def is_valid(cls, value: int) -> bool:
        """Return ``True`` if *value* is a defined member of this class."""
        for k, v in cls.__dict__.items():
            if k.startswith("_"):
                continue
            if callable(v):
                continue
            if v == value:
                return True
        return False

    @classmethod
    def get_name(cls, value: int) -> str:
        """Return the attribute name whose value equals *value*."""
        for k, v in cls.__dict__.items():
            if k.startswith("_"):
                continue
            if callable(v):
                continue
            if v == value:
                return k
        raise KeyError(value)


# ── Gain ──────────────────────────────────────────────────────────────────────
class Gain(CV):
    """Spectral measurement analogue gain settings for CFG1 register bits 4:0.

    Higher gain increases sensitivity for low-light conditions but may saturate
    in bright environments.

    +---------------------------+----------+
    | Setting                   | Gain     |
    +===========================+==========+
    | :py:const:`Gain.X0_5`     | 0.5×     |
    +---------------------------+----------+
    | :py:const:`Gain.X1`       | 1×       |
    +---------------------------+----------+
    | :py:const:`Gain.X2`       | 2×       |
    +---------------------------+----------+
    | :py:const:`Gain.X4`       | 4×       |
    +---------------------------+----------+
    | :py:const:`Gain.X8`       | 8×       |
    +---------------------------+----------+
    | :py:const:`Gain.X16`      | 16×      |
    +---------------------------+----------+
    | :py:const:`Gain.X32`      | 32×      |
    +---------------------------+----------+
    | :py:const:`Gain.X64`      | 64×      |
    +---------------------------+----------+
    | :py:const:`Gain.X128`     | 128×     |
    +---------------------------+----------+
    | :py:const:`Gain.X256`     | 256× ★   |
    +---------------------------+----------+
    | :py:const:`Gain.X512`     | 512×     |
    +---------------------------+----------+
    | :py:const:`Gain.X1024`    | 1024×    |
    +---------------------------+----------+
    | :py:const:`Gain.X2048`    | 2048×    |
    +---------------------------+----------+

    ★ Default after :meth:`AS7343.__init__`.
    """

    X0_5 = 0
    X1 = 1
    X2 = 2
    X4 = 3
    X8 = 4
    X16 = 5
    X32 = 6
    X64 = 7
    X128 = 8
    X256 = 9  # default
    X512 = 10
    X1024 = 11
    X2048 = 12


# ── SMUX mode ─────────────────────────────────────────────────────────────────
class SmuxMode(CV):
    """Auto-SMUX channel-cycling mode settings for CFG20 register bits 6:5.

    The auto-SMUX hardware automatically cycles through multiple SMUX
    configurations in a single measurement trigger, accumulating data for
    more spectral channels per access of :attr:`AS7343.all_channels`.

    +-----------------------------+--------------------------------------------+
    | Setting                     | Channels measured                          |
    +=============================+============================================+
    | :py:const:`SmuxMode.CH6`    | 6 channels (1 SMUX cycle)                  |
    +-----------------------------+--------------------------------------------+
    | :py:const:`SmuxMode.CH12`   | 12 channels (2 SMUX cycles)                |
    +-----------------------------+--------------------------------------------+
    | :py:const:`SmuxMode.CH18`   | 18 channels (3 SMUX cycles) ★              |
    +-----------------------------+--------------------------------------------+

    ★ Default after :meth:`AS7343.__init__`.
    """

    CH6 = 0  # 6 channels — FZ, FY, FXL, NIR, VIS_TL, VIS_BR
    CH12 = 2  # 12 channels — 2 auto SMUX cycles
    CH18 = 3  # 18 channels — 3 auto SMUX cycles (all channels)  ★ default


# ── Channel identifiers ───────────────────────────────────────────────────────
class Channel(CV):
    """Spectral channel index within the 18-channel auto-SMUX data array.

    The index corresponds to the order in which data appears in the output
    buffer returned by :attr:`AS7343.all_channels` in
    :attr:`SmuxMode.CH18` mode.

    +----------------------------------+--------+--------------------------+
    | Setting                          | Index  | Centre wavelength        |
    +==================================+========+==========================+
    | :py:const:`Channel.FZ`           | 0      | 450 nm (blue)            |
    +----------------------------------+--------+--------------------------+
    | :py:const:`Channel.FY`           | 1      | 555 nm (yellow-green)    |
    +----------------------------------+--------+--------------------------+
    | :py:const:`Channel.FXL`          | 2      | 600 nm (orange)          |
    +----------------------------------+--------+--------------------------+
    | :py:const:`Channel.NIR`          | 3      | 855 nm (near-IR)         |
    +----------------------------------+--------+--------------------------+
    | :py:const:`Channel.VIS_TL_0`     | 4      | Clear, top-left, cycle 1 |
    +----------------------------------+--------+--------------------------+
    | :py:const:`Channel.VIS_BR_0`     | 5      | Clear, btm-right, cycle 1|
    +----------------------------------+--------+--------------------------+
    | :py:const:`Channel.F2`           | 6      | 425 nm (violet-blue)     |
    +----------------------------------+--------+--------------------------+
    | :py:const:`Channel.F3`           | 7      | 475 nm (blue-cyan)       |
    +----------------------------------+--------+--------------------------+
    | :py:const:`Channel.F4`           | 8      | 515 nm (green)           |
    +----------------------------------+--------+--------------------------+
    | :py:const:`Channel.F6`           | 9      | 640 nm (red)             |
    +----------------------------------+--------+--------------------------+
    | :py:const:`Channel.VIS_TL_1`     | 10     | Clear, top-left, cycle 2 |
    +----------------------------------+--------+--------------------------+
    | :py:const:`Channel.VIS_BR_1`     | 11     | Clear, btm-right, cycle 2|
    +----------------------------------+--------+--------------------------+
    | :py:const:`Channel.F1`           | 12     | 405 nm (violet)          |
    +----------------------------------+--------+--------------------------+
    | :py:const:`Channel.F7`           | 13     | 690 nm (deep red)        |
    +----------------------------------+--------+--------------------------+
    | :py:const:`Channel.F8`           | 14     | 745 nm (near-IR edge)    |
    +----------------------------------+--------+--------------------------+
    | :py:const:`Channel.F5`           | 15     | 550 nm (green-yellow)    |
    +----------------------------------+--------+--------------------------+
    | :py:const:`Channel.VIS_TL_2`     | 16     | Clear, top-left, cycle 3 |
    +----------------------------------+--------+--------------------------+
    | :py:const:`Channel.VIS_BR_2`     | 17     | Clear, btm-right, cycle 3|
    +----------------------------------+--------+--------------------------+
    """

    FZ = 0
    FY = 1
    FXL = 2
    NIR = 3
    VIS_TL_0 = 4
    VIS_BR_0 = 5
    F2 = 6
    F3 = 7
    F4 = 8
    F6 = 9
    VIS_TL_1 = 10
    VIS_BR_1 = 11
    F1 = 12
    F7 = 13
    F8 = 14
    F5 = 15
    VIS_TL_2 = 16
    VIS_BR_2 = 17


# ── Flicker detection result ───────────────────────────────────────────────────
class FlickerFreq(CV):
    """Flicker detection result values returned by :attr:`AS7343.flicker_frequency`.

    +-------------------------------+----------------------------+
    | Setting                       | Meaning                    |
    +===============================+============================+
    | :py:const:`FlickerFreq.NONE`  | No flicker detected        |
    +-------------------------------+----------------------------+
    | :py:const:`FlickerFreq.HZ100` | 100 Hz mains flicker       |
    +-------------------------------+----------------------------+
    | :py:const:`FlickerFreq.HZ120` | 120 Hz mains flicker       |
    +-------------------------------+----------------------------+
    """

    NONE = 0
    HZ100 = 100
    HZ120 = 120


# ── AS7343 driver class ───────────────────────────────────────────────────────
class AS7343:
    """CircuitPython driver for the ams OSRAM AS7343 14-channel spectral sensor.

    :param ~busio.I2C i2c_bus: The I2C bus the device is connected to.
    :param int address: I2C address. Defaults to :const:`0x39`.

    **Quickstart: Importing and using the device**

    .. code-block:: python

        import board
        from adafruit_as7343 import AS7343

        i2c = board.I2C()
        sensor = AS7343(i2c)
        readings = sensor.all_channels

    .. note::
        The AS7343 has two register banks selected by bit 4 of CFG0 (0xBF):

        * **Bank 0** (default, ``REG_BANK=0``): registers at 0x80 and above.
        * **Bank 1** (``REG_BANK=1``): registers at 0x58–0x7F (ID, REVID,
          AUXID, GPIO, CFG10, CFG12).

        CFG0 itself is always accessible in both bank modes and is used
        to switch between them via :meth:`_set_bank`.
    """

    # ── Register descriptors ─────────────────────────────────────────────────
    # CFG0 (0xBF) — always accessible in both bank modes
    # bit 4: REG_BANK   (1 = bank 1 / 0x58–0x7F,  0 = bank 0 / 0x80+)
    # bit 5: LOW_POWER  (1 = low-power idle between measurements)
    _reg_bank = RWBit(_AS7343_CFG0, 4)
    low_power_enabled = RWBit(
        _AS7343_CFG0, 5
    )  # True when low-power idle mode is active between measurements

    # ENABLE (0x80) individual enable bits
    power_enabled = RWBit(_AS7343_ENABLE, 0)  # Power ON — True when sensor is powered on (PON bit)
    spectral_measurement_enabled = RWBit(
        _AS7343_ENABLE, 1
    )  # True when the spectral measurement engine is running (SP_EN bit)
    wait_enabled = RWBit(
        _AS7343_ENABLE, 3
    )  # True when the wait timer between measurements is active
    _fden = RWBit(_AS7343_ENABLE, 6)  # Flicker detection enable

    # ATIME (0x81) — integration time multiplier 0–255
    atime = UnaryStruct(_AS7343_ATIME, "B")

    # WTIME (0x83) — wait time between measurements 0–255
    # Wait time (ms) = (WTIME + 1) × 2.78 ms
    wtime = UnaryStruct(_AS7343_WTIME, "B")

    # SP_TH_L/H (0x84, 0x86) — 16-bit spectral interrupt thresholds
    spectral_threshold_low = UnaryStruct(_AS7343_SP_TH_L, "<H")
    spectral_threshold_high = UnaryStruct(_AS7343_SP_TH_H, "<H")

    # STATUS2 (0x90) — measurement validity and saturation flags
    _avalid = RWBit(_AS7343_STATUS2, 6)  # AVALID: data valid after integration
    digital_saturated = RWBit(
        _AS7343_STATUS2, 4
    )  # True if any ADC counter reached its maximum value during the last integration
    analog_saturated = RWBit(
        _AS7343_STATUS2, 3
    )  # True if the analogue front-end was saturated during the
    # last integration (may assert even when channel readings appear normal)

    # STATUS (0x93) — main status; writing back the read value clears flags
    _status = UnaryStruct(_AS7343_STATUS, "B")

    # ASTATUS (0x94) — reading this register latches the channel data registers
    _astatus = UnaryStruct(_AS7343_ASTATUS, "B")

    # Channel data registers starting at DATA_0_L (0x95).
    # Each channel is a 16-bit little-endian value (2 bytes).
    # Struct descriptors for burst-reading 6, 12, or 18 channels at once:
    _data_6ch = Struct(_AS7343_DATA_0_L, "<6H")
    _data_12ch = Struct(_AS7343_DATA_0_L, "<12H")
    _data_18ch = Struct(_AS7343_DATA_0_L, "<18H")
    # StructArray descriptor for reading a single channel by index:
    _channel_data = StructArray(_AS7343_DATA_0_L, "<H", 18)

    # CFG1 (0xC6) bits 4:0 — analogue gain (AGAIN)
    _again = RWBits(5, _AS7343_CFG1, 0)

    # CFG20 (0xD6) bits 6:5 — auto-SMUX mode
    _auto_smux = RWBits(2, _AS7343_CFG20, 5)

    # LED (0xCD)
    # bit 7: LED_ACT — enables the LED driver
    # bits 6:0: LED_DRIVE — drive current; current_mA = 4 + (val × 2)
    led_enabled = RWBit(_AS7343_LED, 7)  # True when the on-board LED driver is active
    _led_drive = RWBits(7, _AS7343_LED, 0)

    # PERS (0xCF) bits 3:0 — interrupt persistence filter (0–15)
    _persistence = RWBits(4, _AS7343_PERS, 0)

    # ASTEP (0xD4–0xD5) — 16-bit integration step size, little-endian
    # Integration time (ms) = (ATIME + 1) × (ASTEP + 1) × 2.78 µs
    _astep = UnaryStruct(_AS7343_ASTEP_L, "<H")

    # AZ_CONFIG (0xDE) — auto-zero frequency; 0=never, 255=once before first measurement
    _az_config = UnaryStruct(_AS7343_AZ_CONFIG, "B")

    # FD_STATUS (0xE3) — flicker detection result flags
    _fd_status = UnaryStruct(_AS7343_FD_STATUS, "B")

    # INTENAB (0xF9) — interrupt enable flags
    _sien = RWBit(_AS7343_INTENAB, 0)  # System interrupt enable
    fifo_interrupt_enabled = RWBit(
        _AS7343_INTENAB, 2
    )  # True when the FIFO threshold interrupt is enabled
    spectral_interrupt_enabled = RWBit(
        _AS7343_INTENAB, 3
    )  # True when the spectral threshold interrupt is enabled

    # CONTROL (0xFA) — bit 3 = SW_RESET (self-clearing)
    _control = UnaryStruct(_AS7343_CONTROL, "B")

    # ── Bank 1 register descriptors (0x58–0x6B) ──────────────────────────────
    # These must only be accessed after _set_bank(True); call _set_bank(False)
    # when done to restore bank 0 (the default).
    _part_id = UnaryStruct(_AS7343_ID, "B")  # Chip part ID — expected 0x81
    _revid = UnaryStruct(_AS7343_REVID, "B")  # Revision ID (bits 2:0)
    _auxid = UnaryStruct(_AS7343_AUXID, "B")  # Auxiliary ID (bits 3:0)

    # GPIO (0x6B) individual bits
    _gpio_in = ROBit(_AS7343_GPIO, 0)  # GPIO input value (read-only pin state)
    _gpio_out = RWBit(_AS7343_GPIO, 1)  # GPIO output value
    _gpio_in_en = RWBit(_AS7343_GPIO, 2)  # 0=output mode, 1=input mode
    _gpio_inv = RWBit(_AS7343_GPIO, 3)  # Invert GPIO polarity

    # CFG12 (0x66) bits 2:0 — SP_TH_CH threshold comparison channel (0–5)
    # NOTE: In hardware testing this register has no observed effect on
    # threshold comparison — comparisons always target CH0 regardless.
    _sp_th_ch = RWBits(3, _AS7343_CFG12, 0)

    # ── Constructor ───────────────────────────────────────────────────────────
    def __init__(
        self,
        i2c_bus: "busio.I2C",
        address: int = _AS7343_I2C_ADDRESS,
    ) -> None:
        self.i2c_device = i2c_device.I2CDevice(i2c_bus, address)

        # Switch to bank 1 to read the part ID register (0x5A)
        self._set_bank(True)
        chip_id = self._part_id
        self._set_bank(False)

        if chip_id != _AS7343_CHIP_ID:
            raise RuntimeError(
                f"Failed to find AS7343 — check wiring! "
                + f"Expected chip ID 0x{_AS7343_CHIP_ID:02X}, "
                + f"got 0x{chip_id:02X}."
            )

        # Software reset to clear any stale state
        self._control = 0x08  # SW_RESET bit
        time.sleep(0.2)

        # Poll until the device responds again after reset
        for _ in range(20):
            try:
                with self.i2c_device:
                    pass
                break
            except OSError:
                time.sleep(0.05)

        # Power on
        self.power_enabled = True

        # Default: 256× gain
        self._again = Gain.X256

        # Default integration time: ATIME=29, ASTEP=599 → ~50 ms
        # t_int = (29+1) × (599+1) × 2.78 µs = 50.04 ms
        self.atime = 29
        self._astep = 599

        # Default: 18-channel auto-SMUX mode (all spectral channels)
        self._auto_smux = SmuxMode.CH18

        # Configure GPIO as output (default state after reset)
        self._set_bank(True)
        self._gpio_in_en = False  # False → output mode (GPIO_IN_EN=0)
        self._set_bank(False)

        # Ensure LED is off
        self.led_enabled = False

        # Timeout in milliseconds used by the all_channels property
        self.read_timeout: int = 1000

    # ── Bank switching ────────────────────────────────────────────────────────
    def _set_bank(self, bank1: bool) -> None:
        """Switch register bank access.

        :param bool bank1: ``True`` selects bank 1 (registers 0x58–0x7F),
            ``False`` restores bank 0 (registers 0x80+, the default).

        CFG0 (0xBF) is accessible in both bank modes and holds the
        ``REG_BANK`` bit (bit 4) used to perform the switch.
        """
        self._reg_bank = bank1

    # ── Gain ──────────────────────────────────────────────────────────────────
    @property
    def gain(self) -> int:
        """Analogue gain for spectral measurements.

        Must be a :class:`Gain` value, e.g. ``Gain.X256``.
        Default is :attr:`Gain.X256` (256×).
        """
        return self._again

    @gain.setter
    def gain(self, value: int) -> None:
        if not Gain.is_valid(value):
            raise ValueError("gain must be a Gain constant")
        self._again = value

    # ── Integration time ──────────────────────────────────────────────────────
    @property
    def astep(self) -> int:
        """Integration step size (ASTEP), 0–65534.

        Integration time (ms) = (``atime`` + 1) × (``astep`` + 1) × 2.78 µs.
        65535 is reserved by hardware.
        """
        return self._astep

    @astep.setter
    def astep(self, value: int) -> None:
        if not 0 <= value <= 65534:
            raise ValueError("astep must be 0–65534 (65535 is reserved)")
        self._astep = value

    @property
    def integration_time_ms(self) -> float:
        """Calculated integration time in milliseconds (read-only).

        ``(atime + 1) × (astep + 1) × 2.78 µs``
        """
        return (self.atime + 1) * (self._astep + 1) * 0.00278

    # ── SMUX mode ─────────────────────────────────────────────────────────────
    @property
    def smux_mode(self) -> int:
        """Auto-SMUX channel cycling mode.

        Must be a :class:`SmuxMode` value:

        * ``SmuxMode.CH6``  — 6 channels
        * ``SmuxMode.CH12`` — 12 channels
        * ``SmuxMode.CH18`` — 18 channels (default)
        """
        return self._auto_smux

    @smux_mode.setter
    def smux_mode(self, value: int) -> None:
        if not SmuxMode.is_valid(value):
            raise ValueError("smux_mode must be a SmuxMode constant")
        self._auto_smux = value

    @property
    def data_ready(self) -> bool:
        """``True`` when a complete set of channel data is available (AVALID)."""
        return self._avalid

    @property
    def all_channels(self) -> List[int]:
        """Trigger a measurement and return all channel readings.

        Starts a single measurement, waits for AVALID (fires after all
        auto-SMUX cycles complete), then returns a list of 16-bit readings.
        The list length matches the current :attr:`smux_mode`:
        6, 12, or 18 values.

        Uses :attr:`read_timeout` as the maximum number of milliseconds to
        wait for data ready.

        :returns: List of channel counts in the order defined by :class:`Channel`.
        :raises TimeoutError: If data is not ready within :attr:`read_timeout` ms.
        """
        mode = self._auto_smux
        if mode == SmuxMode.CH12:
            num_channels = 12
        elif mode == SmuxMode.CH18:
            num_channels = 18
        else:
            num_channels = 6

        # Stop any in-progress measurement and clear stale status
        self.spectral_measurement_enabled = False

        # Clear pending status by reading then writing back
        status_val = self._status
        self._status = status_val  # write-to-clear
        _ = self._astatus  # discard latched status

        # Trigger one measurement (auto-SMUX runs all cycles internally)
        self.spectral_measurement_enabled = True

        # Wait for AVALID — fires after all SMUX cycles complete
        deadline = time.monotonic() + self.read_timeout / 1000.0
        while not self.data_ready:
            if time.monotonic() > deadline:
                self.spectral_measurement_enabled = False
                raise TimeoutError("Timed out waiting for AS7343 data ready")
            time.sleep(0.001)

        # Latch channel data by reading ASTATUS
        _ = self._astatus

        # Burst-read all channel data via the appropriate Struct descriptor.
        if num_channels == 18:
            readings = list(self._data_18ch)
        elif num_channels == 12:
            readings = list(self._data_12ch)
        else:
            readings = list(self._data_6ch)

        # Stop measurement so AVALID clears for the next read
        self.spectral_measurement_enabled = False

        return readings

    def read_channel(self, channel: int) -> int:
        """Read a single spectral channel by index.

        Reads ASTATUS to latch data, then reads the specific channel register.
        Use :class:`Channel` constants to specify the channel.

        :param int channel: Channel index (a :class:`Channel` constant, 0–17).
        :returns: 16-bit channel count.
        """
        if not 0 <= channel <= 17:
            raise ValueError("channel must be 0–17 (use Channel constants)")

        # Latch data
        _ = self._astatus

        # Read the single channel via the StructArray descriptor.
        # _channel_data[index] returns a tuple (value,); extract the first element.
        return self._channel_data[channel][0]

    # ── LED driver ────────────────────────────────────────────────────────────
    @property
    def led_current_ma(self) -> int:
        """LED drive current in milliamps.

        Valid range: 4–258 mA (even values only; hardware steps of 2 mA).
        Formula: ``current_mA = 4 + (register_value × 2)``
        """
        return 4 + (self._led_drive * 2)

    @led_current_ma.setter
    def led_current_ma(self, current_ma: int) -> None:
        current_ma = max(4, min(258, current_ma))
        self._led_drive = (current_ma - 4) // 2

    # ── Flicker detection ─────────────────────────────────────────────────────
    @property
    def flicker_detection_enabled(self) -> bool:
        """``True`` when flicker detection is enabled."""
        return self._fden

    @flicker_detection_enabled.setter
    def flicker_detection_enabled(self, enable: bool) -> None:
        self._fden = enable

    @property
    def flicker_status(self) -> int:
        """Raw value of the FD_STATUS register (0xE3)."""
        return self._fd_status

    @property
    def flicker_frequency(self) -> int:
        """Detected mains flicker frequency.

        Returns a :class:`FlickerFreq` value:

        * ``FlickerFreq.NONE``  — no flicker detected
        * ``FlickerFreq.HZ100`` — 100 Hz
        * ``FlickerFreq.HZ120`` — 120 Hz

        Bit layout of FD_STATUS:
        - bit 0: 100 Hz detected flag
        - bit 1: 120 Hz detected flag
        - bit 2: 100 Hz valid flag
        - bit 3: 120 Hz valid flag
        """
        status = self._fd_status
        if (status & 0x08) and (status & 0x02):
            return FlickerFreq.HZ120
        if (status & 0x04) and (status & 0x01):
            return FlickerFreq.HZ100
        return FlickerFreq.NONE

    # ── Interrupts ────────────────────────────────────────────────────────────
    @property
    def system_interrupt_enabled(self) -> bool:
        """``True`` when the system interrupt is enabled."""
        return self._sien

    @system_interrupt_enabled.setter
    def system_interrupt_enabled(self, enable: bool) -> None:
        self._sien = enable

    @property
    def status(self) -> int:
        """Raw value of the main STATUS register (0x93).

        .. warning::
            Writing this register clears the status flags.  Use
            :meth:`clear_status` to explicitly clear all flags.
        """
        return self._status

    def clear_status(self) -> None:
        """Clear all status flags in the STATUS register (write-to-clear)."""
        val = self._status
        self._status = val

    # ── Persistence ───────────────────────────────────────────────────────────
    @property
    def persistence(self) -> int:
        """Interrupt persistence filter (0–15).

        Number of consecutive out-of-threshold measurements required before
        the interrupt flag is asserted. 0 = trigger every cycle.
        """
        return self._persistence

    @persistence.setter
    def persistence(self, value: int) -> None:
        if not 0 <= value <= 15:
            raise ValueError("persistence must be 0–15")
        self._persistence = value

    # ── Auto-zero ─────────────────────────────────────────────────────────────
    @property
    def auto_zero_frequency(self) -> int:
        """Cycles between automatic zero-offset calibration runs (0–255).

        * ``0``   — auto-zero disabled (not recommended)
        * ``1``   — every measurement cycle
        * ``255`` — only before the very first measurement (default)
        """
        return self._az_config

    @auto_zero_frequency.setter
    def auto_zero_frequency(self, value: int) -> None:
        if not 0 <= value <= 255:
            raise ValueError("auto_zero_frequency must be 0–255")
        self._az_config = value

    # ── Threshold channel ─────────────────────────────────────────────────────
    @property
    def threshold_channel(self) -> int:
        """ADC channel (0–5) used for spectral interrupt threshold comparison.

        .. note::
            Hardware testing shows this register has **no observed effect** —
            threshold comparison always targets CH0 regardless of this setting.
            Read/write works correctly but the value is not acted upon by
            the hardware.
        """
        self._set_bank(True)
        val = self._sp_th_ch
        self._set_bank(False)
        return val

    @threshold_channel.setter
    def threshold_channel(self, channel: int) -> None:
        if not 0 <= channel <= 5:
            raise ValueError("threshold_channel must be 0–5")
        self._set_bank(True)
        self._sp_th_ch = channel
        self._set_bank(False)

    # ── GPIO ──────────────────────────────────────────────────────────────────
    @property
    def gpio_output_mode(self) -> bool:
        """``True`` when the GPIO pin is configured as an output.

        Set to ``False`` to switch to input mode.
        """
        self._set_bank(True)
        # GPIO_IN_EN=0 means output mode; invert for user-facing polarity
        val = not self._gpio_in_en
        self._set_bank(False)
        return val

    @gpio_output_mode.setter
    def gpio_output_mode(self, output: bool) -> None:
        self._set_bank(True)
        self._gpio_in_en = not output  # GPIO_IN_EN: 0=output, 1=input
        self._set_bank(False)

    @property
    def gpio_value(self) -> bool:
        """GPIO pin state.

        When in output mode, read back the driven value.
        When in input mode, read the external signal level.
        """
        self._set_bank(True)
        val = self._gpio_in
        self._set_bank(False)
        return val

    @gpio_value.setter
    def gpio_value(self, high: bool) -> None:
        self._set_bank(True)
        self._gpio_out = high
        self._set_bank(False)

    @property
    def gpio_inverted(self) -> bool:
        """``True`` when GPIO polarity is inverted."""
        self._set_bank(True)
        val = self._gpio_inv
        self._set_bank(False)
        return val

    @gpio_inverted.setter
    def gpio_inverted(self, invert: bool) -> None:
        self._set_bank(True)
        self._gpio_inv = invert
        self._set_bank(False)

    # ── Chip information ──────────────────────────────────────────────────────
    @property
    def part_id(self) -> int:
        """Part ID register value (should be ``0x81`` for AS7343)."""
        self._set_bank(True)
        val = self._part_id
        self._set_bank(False)
        return val

    @property
    def revision_id(self) -> int:
        """Revision ID (bits 2:0 of REVID register)."""
        self._set_bank(True)
        val = self._revid & 0x07
        self._set_bank(False)
        return val

    @property
    def aux_id(self) -> int:
        """Auxiliary ID (bits 3:0 of AUXID register)."""
        self._set_bank(True)
        val = self._auxid & 0x0F
        self._set_bank(False)
        return val
