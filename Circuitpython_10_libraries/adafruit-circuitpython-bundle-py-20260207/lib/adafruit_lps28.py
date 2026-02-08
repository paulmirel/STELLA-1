# SPDX-FileCopyrightText: Copyright (c) 2025 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_lps28`
================================================================================

CircuitPython driver for the LPS28 (LPS28DFW) Pressure Sensor


* Author(s): Liz Clark

Implementation Notes
--------------------

**Hardware:**

* `Adafruit LPS28 Pressure Sensor <https://www.adafruit.com/product/6067>`_"

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
* Adafruit's Register library: https://github.com/adafruit/Adafruit_CircuitPython_Register
"""

import time

from adafruit_bus_device.i2c_device import I2CDevice
from adafruit_register.i2c_bits import RWBits
from adafruit_register.i2c_struct import ROUnaryStruct, UnaryStruct
from adafruit_register.i2c_struct_array import StructArray
from micropython import const

try:
    import typing

    from busio import I2C
except ImportError:
    pass

__version__ = "1.0.1"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_LPS28.git"

_DEFAULT_ADDR = const(0x5C)
_WHOAMI = const(0x0F)
_WHOAMI_VAL = const(0xB4)
_THS_P = const(0x0C)
_CTRL_REG1 = const(0x10)
_CTRL_REG2 = const(0x11)
_CTRL_REG3 = const(0x12)
_CTRL_REG4 = const(0x13)
_IF_CTRL = const(0x0E)
_INTERRUPT_CFG = const(0x0B)
_FIFO_CTRL = const(0x14)
_FIFO_WTM = const(0x15)
_REF_P = const(0x16)
_RPDS = const(0x18)
_INT_SOURCE = const(0x24)
_FIFO_STATUS1 = const(0x25)
_FIFO_STATUS2 = const(0x26)
_STATUS = const(0x27)
_PRESS_OUT = const(0x28)
_TEMP_OUT = const(0x2B)
_FIFO_DATA_OUT_PRESS_XL = const(0x78)
_FIFO_STATUS_WTM_IA = const(0x80)
_FIFO_STATUS_OVR_IA = const(0x40)
_FIFO_STATUS_FULL_IA = const(0x20)
_STATUS_TEMP_OVERRUN = const(0x20)
_STATUS_PRESS_OVERRUN = const(0x10)
_STATUS_TEMP_READY = const(0x02)
_STATUS_PRESS_READY = const(0x01)

_ODR_MAP = {
    0: const(0b0000),
    1: const(0b0001),
    4: const(0b0010),
    10: const(0b0011),
    25: const(0b0100),
    50: const(0b0101),
    75: const(0b0110),
    100: const(0b0111),
    200: const(0b1000),
}

_AVG_MAP = {
    4: const(0b000),
    8: const(0b001),
    16: const(0b010),
    32: const(0b011),
    64: const(0b100),
    128: const(0b101),
    512: const(0b111),
}

_FIFO_MODE_MAP = {
    "BYPASS": const(0b000),
    "FIFO": const(0b001),
    "CONTINUOUS": const(0b010),
    "CONTINUOUS_TO_FIFO": const(0b011),
    "BYPASS_TO_CONTINUOUS": const(0b100),
    "CONTINUOUS_TO_BYPASS": const(0b111),
}


class LPS28:
    """Driver for the LPS28 pressure sensor."""

    _ctrl_reg1 = UnaryStruct(_CTRL_REG1, "B")
    _ctrl_reg1_ro = ROUnaryStruct(_CTRL_REG1, "B")
    _chip_id = ROUnaryStruct(_WHOAMI, "B")
    _raw_pressure_xlsb = ROUnaryStruct(_PRESS_OUT, "B")
    _raw_pressure_lsb = ROUnaryStruct(_PRESS_OUT + 1, "B")
    _raw_pressure_msb = ROUnaryStruct(_PRESS_OUT + 2, "B")
    _raw_temperature = ROUnaryStruct(_TEMP_OUT, "<h")
    _boot = RWBits(1, _CTRL_REG2, 7)
    _sw_reset = RWBits(1, _CTRL_REG2, 2)
    _raw_fifo_pressure = ROUnaryStruct(_FIFO_DATA_OUT_PRESS_XL, ">I")
    _data_rate = RWBits(4, _CTRL_REG1, 3)
    _averaging = RWBits(3, _CTRL_REG1, 0)
    _int_polarity = RWBits(1, _CTRL_REG3, 3)
    _int_open_drain = RWBits(1, _CTRL_REG3, 1)
    trigger_one_shot = RWBits(1, _CTRL_REG2, 0)
    """Start a one-shot pressure measurement"""
    threshold_pressure = UnaryStruct(_THS_P, ">H")
    """Pressure threshold for interrupt generation (16-bit value)"""
    full_scale_mode = RWBits(1, _CTRL_REG2, 6)
    """Enable full-scale mode (False = 1260 hPa, True = 4060 hPa)"""
    lpf_odr9 = RWBits(1, _CTRL_REG2, 5)
    """Enable low-pass filter with ODR/9 cutoff"""
    sda_pullup = RWBits(1, _IF_CTRL, 4)
    """Enable I2C SDA pull-up"""
    int_pulldown_disable = RWBits(1, _IF_CTRL, 2)
    """Disable interrupt pin internal pull-down"""
    auto_ref_pressure = RWBits(1, _INTERRUPT_CFG, 7)
    """Enable automatic reference pressure update"""
    reset_arp = RWBits(1, _INTERRUPT_CFG, 6)
    """Reset automatic reference pressure"""
    auto_zero = RWBits(1, _INTERRUPT_CFG, 5)
    """Enable auto-zeroing of pressure readings"""
    reset_auto_zero = RWBits(1, _INTERRUPT_CFG, 4)
    """Reset auto-zeroing function"""
    pressure_high = RWBits(1, _INTERRUPT_CFG, 1)
    """Enable high-pressure threshold interrupt"""
    pressure_low = RWBits(1, _INTERRUPT_CFG, 2)
    """Enable low-pressure threshold interrupt"""
    latch_interrupt = RWBits(1, _INTERRUPT_CFG, 3)
    """Enable latching of interrupt events"""
    int_source = ROUnaryStruct(_INT_SOURCE, "B")
    """Interrupt source flags"""
    fifo_unread_samples = ROUnaryStruct(_FIFO_STATUS1, "B")
    """Number of unread FIFO samples (0-127)"""
    status = ROUnaryStruct(_STATUS, "B")
    """Sensor status flags (pressure/temp ready, overruns)"""
    fifo_status = ROUnaryStruct(_FIFO_STATUS2, "B")
    """FIFO status flags (full, watermark, overrun)"""
    fifo_stop_on_watermark = RWBits(1, _FIFO_CTRL, 3)
    """Stop FIFO when watermark level is reached"""
    _fifo_mode = RWBits(3, _FIFO_CTRL, 0)
    fifo_watermark = UnaryStruct(_FIFO_WTM, "B")
    """FIFO watermark threshold (0-127 samples)"""
    reference_pressure = UnaryStruct(_REF_P, ">h")
    """Reference pressure value (16-bit)"""
    pressure_offset = UnaryStruct(_RPDS, ">h")
    """Pressure offset adjustment (16-bit)"""
    data_ready_pulse = RWBits(1, _CTRL_REG4, 6)
    """Data-ready interrupt as a pulse"""
    data_ready_int = RWBits(1, _CTRL_REG4, 5)
    """Enable data-ready interrupt"""
    pressure_threshold_int = RWBits(1, _CTRL_REG4, 4)
    """Enable pressure threshold interrupt"""
    fifo_full_int = RWBits(1, _CTRL_REG4, 2)
    """Enable FIFO full interrupt"""
    fifo_watermark_int = RWBits(1, _CTRL_REG4, 1)
    """Enable FIFO watermark interrupt"""
    fifo_overrun_int = RWBits(1, _CTRL_REG4, 0)
    """Enable FIFO overrun interrupt"""

    def __init__(self, i2c_bus: I2C, address: int = _DEFAULT_ADDR) -> None:
        """Initialize the LPS28 sensor.

        :param i2c_bus: The I2C bus instance.
        :param address: The I2C address of the sensor (default: 0x5C).
        """
        self.i2c_device = I2CDevice(i2c_bus, address)

        if self._chip_id != _WHOAMI_VAL:
            raise RuntimeError("Failed to find LPS28")
        self.reset()
        self.data_rate = 200
        self.averaging = 4
        self.full_scale_mode = True
        self.interrupt_pin(True, False)
        self.drdy_pulse = True

    @property
    def pressure(self) -> float:
        """Pressure in hPa."""
        raw = self._raw_pressure_msb << 16 | self._raw_pressure_lsb << 8 | self._raw_pressure_xlsb
        divisor = 2048.0 if self.full_scale_mode else 4096.0
        return raw / divisor

    @property
    def temperature(self) -> float:
        """Temperature in °C."""
        return self._raw_temperature / 100

    def reset(self) -> None:
        """Perform a software reset of the sensor."""
        self._sw_reset = True

    def reboot_memory(self) -> None:
        """Reboot the memory content of the sensor."""
        self._boot = True

    @property
    def data_rate(self) -> int:
        """Output data rate in Hz.

        :param value: Desired data rate in Hz.
        :raises ValueError: If the provided value is not a valid data rate.
        """
        raw_value = self._data_rate
        for rate, bits in _ODR_MAP.items():
            if bits == raw_value:
                return rate
        return raw_value

    @data_rate.setter
    def data_rate(self, value: int) -> None:
        if value not in _ODR_MAP:
            raise ValueError(f"Invalid data rate. Must be one of: {sorted(_ODR_MAP.keys())}")
        self._data_rate = _ODR_MAP[value]

    @property
    def averaging(self) -> int:
        """Number of pressure and temperature samples to average

        :param value: Desired averaging factor.
        :raises ValueError: If the provided value is not a valid averaging setting.
        """
        raw_value = self._averaging
        for rate, bits in _AVG_MAP.items():
            if bits == raw_value:
                return rate
        return raw_value

    @averaging.setter
    def averaging(self, value: int) -> None:
        if isinstance(value, int):
            if value not in _AVG_MAP:
                raise ValueError(
                    f"Invalid output data rate. Must be one of: {sorted(_AVG_MAP.keys())}"
                )
            self._averaging = _AVG_MAP[value]
        else:
            self._averaging = value

    def interrupt_pin(self, polarity: bool, open_drain: bool) -> None:
        """Configure the interrupt pin settings.

        :param polarity: True for active-high, False for active-low.
        :param open_drain: True for open-drain output, False for push-pull.
        """
        self._int_polarity = polarity
        self._int_open_drain = open_drain

    @property
    def data_ready(self) -> bool:
        """Check if  data is ready to be read.

        Returns:
            bool: True if data is ready
        """
        return bool(self.status & _STATUS_PRESS_READY)

    @property
    def fifo_mode(self) -> str:
        """FIFO mode

        Available modes:
            'BYPASS', 'FIFO', 'CONTINUOUS',
            'CONTINUOUS_TO_FIFO', 'BYPASS_TO_CONTINUOUS',
            'CONTINUOUS_TO_BYPASS'

        :return: The current FIFO mode as a string.
        :raises ValueError: If an invalid FIFO mode is given.
        """
        raw_value = self._fifo_mode
        for mode, bits in _FIFO_MODE_MAP.items():
            if bits == raw_value:
                return mode
        return raw_value

    @fifo_mode.setter
    def fifo_mode(self, value: str) -> None:
        if isinstance(value, str):
            if value not in _FIFO_MODE_MAP:
                raise ValueError(
                    f"Invalid FIFO mode. Must be one of: {sorted(_FIFO_MODE_MAP.keys())}"
                )
            value = _FIFO_MODE_MAP[value]
        self._fifo_mode = 0b000
        time.sleep(0.01)
        self._fifo_mode = value

    @property
    def fifo_ready(self) -> bool:
        """Check if FIFO watermark level is reached.

        :return: True if FIFO watermark level is reached, False otherwise.
        """
        return bool(self.fifo_status & _FIFO_STATUS_WTM_IA)

    @property
    def fifo_pressure(self) -> float:
        """Reads and removes the next FIFO pressure sample in hPa.

        :return: Pressure value in hPa.
        """
        buffer = bytearray(3)
        with self.i2c_device as i2c:
            i2c.write_then_readinto(bytes([_FIFO_DATA_OUT_PRESS_XL]), buffer)
        raw = (buffer[2] << 16) | (buffer[1] << 8) | buffer[0]
        if raw & 0x800000:
            raw -= 0x1000000
        divisor = 2048.0 if self.full_scale_mode else 4096.0
        return raw / divisor
