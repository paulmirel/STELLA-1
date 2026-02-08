# SPDX-FileCopyrightText: Copyright (c) 2024 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_ina3221`
================================================================================

CircuitPython driver for the INA3221 Triple 0-26 VDC, ±3.2 Amp Power Monitor

* Author(s): Liz Clark

Implementation Notes
--------------------

**Hardware:**

* `Adafruit INA3221 - Triple 0-26 VDC, ±3.2 Amp Power Monitor <https://www.adafruit.com/product/6062>`_"

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads
* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
"""

try:
    from typing import Any, List
except ImportError:
    pass
from adafruit_bus_device.i2c_device import I2CDevice

__version__ = "1.2.1"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_INA3221.git"

DEFAULT_ADDRESS = 0x40
MANUFACTURER_ID = 0x5449
DIE_ID = 0x3220

# Register Definitions
CONFIGURATION = 0x00
SHUNTVOLTAGE_REGS = [0x01, 0x03, 0x05]
BUSVOLTAGE_REGS = [0x02, 0x04, 0x06]
CRITICAL_ALERT_LIMIT_REGS = [0x07, 0x09, 0x0B]
WARNING_ALERT_LIMIT_REGS = [0x08, 0x0A, 0x0C]
SHUNTVOLTAGE_SUM = 0x0D
SHUNTVOLTAGE_SUM_LIMIT = 0x0E
MASK_ENABLE = 0x0F
POWERVALID_UPPERLIMIT = 0x10
POWERVALID_LOWERLIMIT = 0x11
MANUFACTURER_ID_REG = 0xFE
DIE_ID_REG = 0xFF

# Mask/Enable Register bit flags
CONV_READY = 1 << 0
TIMECONT_ALERT = 1 << 1
POWER_VALID = 1 << 2
WARN_CH3 = 1 << 3
WARN_CH2 = 1 << 4
WARN_CH1 = 1 << 5
SUMMATION = 1 << 6
CRITICAL_CH3 = 1 << 7
CRITICAL_CH2 = 1 << 8
CRITICAL_CH1 = 1 << 9

# Default value for Adafruit-breakout
DEFAULT_SHUNT_RESISTANCE = 0.05

# Precision (LSB) of bus-voltage and shunt-voltage
BUS_V_LSB = 0.008  # 8mV
SHUNT_V_LSB = 0.000040  # 40µV


def _mask(offset, len, read=True):
    """return mask for reading or writing"""
    if read:
        return ((1 << len) - 1) << offset
    else:
        return ~(((1 << len) - 1) << offset) & 0xFFFF


def _to_signed(val: int, shift: int, bits: int):
    """convert value to signed int and shift result"""
    if val & (1 << (bits - 1)):
        val -= 1 << (bits - 1)  # remove sign
        val = (1 << bits - 1) - 1 - val  # bitwise not
        return -(val >> shift)
    return val >> shift


def _to_2comp(val: int, shift: int, bits: int):
    """convert value to twos complement, shifting as necessary"""
    if val > 0:
        return val << shift
    val = (-val) << shift
    val = (1 << bits - 1) - val  # bitwise not plus 1
    return val + (1 << (bits - 1))


class AVG_MODE:
    """Enumeration for the averaging mode options in INA3221.

    Attributes:
        AVG_1_SAMPLE (int): Average 1 sample.
        AVG_4_SAMPLES (int): Average 4 samples.
        AVG_16_SAMPLES (int): Average 16 samples.
        AVG_64_SAMPLES (int): Average 64 samples.
        AVG_128_SAMPLES (int): Average 128 samples.
        AVG_256_SAMPLES (int): Average 256 samples.
        AVG_512_SAMPLES (int): Average 512 samples.
        AVG_1024_SAMPLES (int): Average 1024 samples.
    """

    AVG_1_SAMPLE: int = 0b000
    AVG_4_SAMPLES: int = 0b001
    AVG_16_SAMPLES: int = 0b010
    AVG_64_SAMPLES: int = 0b011
    AVG_128_SAMPLES: int = 0b100
    AVG_256_SAMPLES: int = 0b101
    AVG_512_SAMPLES: int = 0b110
    AVG_1024_SAMPLES: int = 0b111


class CONV_TIME:
    """Enumeration for conversion time options in INA3221.

    Attributes:
        CONV_TIME_140US (int): Conversion time 140µs.
        CONV_TIME_204US (int): Conversion time 204µs.
        CONV_TIME_332US (int): Conversion time 332µs.
        CONV_TIME_588US (int): Conversion time 588µs.
        CONV_TIME_1MS (int): Conversion time 1ms.
        CONV_TIME_2MS (int): Conversion time 2ms.
        CONV_TIME_4MS (int): Conversion time 4ms.
        CONV_TIME_8MS (int): Conversion time 8ms.
    """

    CONV_TIME_140US: int = 0b000
    CONV_TIME_204US: int = 0b001
    CONV_TIME_332US: int = 0b010
    CONV_TIME_588US: int = 0b011
    CONV_TIME_1MS: int = 0b100
    CONV_TIME_2MS: int = 0b101
    CONV_TIME_4MS: int = 0b110
    CONV_TIME_8MS: int = 0b111


class MODE:
    """Enumeration for operating modes in INA3221.

    Attributes:
        POWER_DOWN (int): Power down mode.
        SHUNT_TRIG (int): Trigger shunt voltage measurement.
        BUS_TRIG (int): Trigger bus voltage measurement.
        SHUNT_BUS_TRIG (int): Trigger both shunt and bus voltage measurements.
        POWER_DOWN2 (int): Alternate power down mode.
        SHUNT_CONT (int): Continuous shunt voltage measurement.
        BUS_CONT (int): Continuous bus voltage measurement.
        SHUNT_BUS_CONT (int): Continuous shunt and bus voltage measurements.
    """

    POWER_DOWN: int = 0b000
    SHUNT_TRIG: int = 0b001
    BUS_TRIG: int = 0b010
    SHUNT_BUS_TRIG: int = 0b011
    POWER_DOWN2: int = 0b100
    SHUNT_CONT: int = 0b101
    BUS_CONT: int = 0b110
    SHUNT_BUS_CONT: int = 0b111


class INA3221Channel:
    """Represents a single channel of the INA3221.

    Args:
        device (Any): The device INA3221 instance managing the I2C communication.
        channel (int): The channel number (1, 2, or 3) for this instance.
    """

    def __init__(self, device: Any, channel: int) -> None:
        self._device = device
        self._channel = channel
        self._shunt_resistance = DEFAULT_SHUNT_RESISTANCE
        self._enabled = False

    def enable(self, flag: bool = True) -> None:
        """Enable/disable this channel"""
        # enable bits in the configuration-register: 14-12
        self._device._set_register_bits(CONFIGURATION, 14 - self._channel, 1, int(flag))
        self._enabled = flag

    @property
    def enabled(self) -> bool:
        """return buffered enable-state"""
        return self._enabled

    @property
    def bus_voltage(self) -> float:
        """Bus voltage in volts."""
        reg_addr = BUSVOLTAGE_REGS[self._channel]
        raw_value = self._device._get_register_bits(reg_addr, 0, 16)
        raw_value = _to_signed(raw_value, 3, 16)
        return raw_value * BUS_V_LSB

    @property
    def shunt_voltage(self) -> float:
        """Shunt voltage in millivolts."""
        reg_addr = SHUNTVOLTAGE_REGS[self._channel]
        raw_value = self._device._get_register_bits(reg_addr, 0, 16)
        raw_value = _to_signed(raw_value, 3, 16)
        return raw_value * SHUNT_V_LSB * 1000

    @property
    def shunt_resistance(self) -> float:
        """Shunt resistance in ohms."""
        return self._shunt_resistance

    @shunt_resistance.setter
    def shunt_resistance(self, value: float) -> None:
        self._shunt_resistance = value

    @property
    def current(self) -> float:
        """Returns the current in mA

        The current is calculated using the formula: I = Vshunt / Rshunt.
        If the shunt voltage is NaN (e.g., no valid measurement), it returns NaN.
        """
        shunt_voltage = self.shunt_voltage  # this is in mV
        if shunt_voltage != shunt_voltage:  # Check for NaN
            return float("nan")
        return shunt_voltage / self._shunt_resistance

    @property
    def critical_alert_threshold(self) -> float:
        """Critical-Alert threshold in amperes

        Returns:
            float: The current critical alert threshold in amperes.
        """
        reg_addr = CRITICAL_ALERT_LIMIT_REGS[self._channel]
        threshold = self._device._get_register_bits(reg_addr, 3, 13)
        return threshold * SHUNT_V_LSB / self._shunt_resistance

    @critical_alert_threshold.setter
    def critical_alert_threshold(self, current: float) -> None:
        threshold = int(current * self._shunt_resistance / SHUNT_V_LSB)
        reg_addr = CRITICAL_ALERT_LIMIT_REGS[self._channel]
        self._device._set_register_bits(reg_addr, 3, 13, threshold)

    @property
    def warning_alert_threshold(self) -> float:
        """Warning-Alert threshold in amperes

        Returns:
            float: The current warning alert threshold in amperes.
        """
        reg_addr = WARNING_ALERT_LIMIT_REGS[self._channel]
        threshold = self._device._get_register_bits(reg_addr, 3, 13)
        return threshold * SHUNT_V_LSB / self._shunt_resistance

    @warning_alert_threshold.setter
    def warning_alert_threshold(self, current: float) -> None:
        threshold = int(current * self._shunt_resistance / SHUNT_V_LSB)
        reg_addr = WARNING_ALERT_LIMIT_REGS[self._channel]
        self._device._set_register_bits(reg_addr, 3, 13, threshold)

    @property
    def summation_channel(self) -> bool:
        """Status of summation channel"""
        return self._device._get_register_bits(MASK_ENABLE, 14 - self._channel, 1)

    @summation_channel.setter
    def summation_channel(self, value: bool) -> None:
        """set value of summation control"""
        self._device._set_register_bits(MASK_ENABLE, 14 - self._channel, 1, int(value))


class INA3221:
    """Driver for the INA3221 device with three channels."""

    def __init__(
        self, i2c, address: int = DEFAULT_ADDRESS, enable: List = [0, 1, 2], probe: bool = True
    ) -> None:
        """Initializes the INA3221 class over I2C
        Args:
            i2c (I2C): The I2C bus to which the INA3221 is connected.
            address (int, optional): The I2C address of the INA3221. Defaults to DEFAULT_ADDRESS.
            enable(List[int], optional): channels to initialize at start (default: all)
            probe (bool, optional): Probe for the device upon object creation, default is true
        """
        self.i2c_dev = I2CDevice(i2c, address, probe=probe)
        self.reset()

        self.channels: List[INA3221Channel] = [INA3221Channel(self, i) for i in range(3)]
        for i in range(3):
            self.channels[i].enable(i in enable)
        self.mode: int = MODE.SHUNT_BUS_CONT
        self.shunt_voltage_conv_time: int = CONV_TIME.CONV_TIME_8MS
        self.bus_voltage_conv_time: int = CONV_TIME.CONV_TIME_8MS
        self.averaging_mode: int = AVG_MODE.AVG_64_SAMPLES

    def __getitem__(self, channel: int) -> INA3221Channel:
        """Allows access to channels via index, e.g., ina[0].bus_voltage.

        Args:
            channel (int): The channel index (0, 1, or 2).

        Raises:
            IndexError: If the channel index is out of range (must be 0, 1, or 2).
        """
        if channel < 0 or channel >= 3:
            raise IndexError("Channel must be 0, 1, or 2.")
        return self.channels[channel]

    def reset(self) -> None:
        """Perform a soft reset on the INA3221.

        Returns:
            None
        """
        self._set_register_bits(CONFIGURATION, 15, 1, 1)

    @property
    def die_id(self) -> int:
        """Die ID of the INA3221.

        Returns:
            int: The Die ID in integer format.
        """
        return int.from_bytes(self._read_register(DIE_ID_REG, 2), "big")

    @property
    def manufacturer_id(self) -> int:
        """Manufacturer ID of the INA3221.

        Returns:
            int: The Manufacturer ID in integer format.
        """
        return int.from_bytes(self._read_register(MANUFACTURER_ID_REG, 2), "big")

    @property
    def mode(self) -> int:
        """Operating mode of the INA3221.

        Returns:
            int: The current mode value.
            0: Power down mode, 1: Trigger shunt voltage measurement,
            2: Trigger bus voltage measurement, 3: Trigger both shunt and bus voltage measurements,
            4: Alternate power down mode, 5: Continuous shunt voltage measurement,
            6: Continuous bus voltage measurement, 7: Continuous shunt and bus voltage measurements
        """
        return self._get_register_bits(CONFIGURATION, 0, 3)

    @mode.setter
    def mode(self, value: int) -> None:
        if not 0 <= value <= 7:
            raise ValueError("Mode must be a 3-bit value (0-7).")
        self._set_register_bits(CONFIGURATION, 0, 3, value)

    @property
    def shunt_voltage_conv_time(self) -> int:
        """Shunt voltage conversion time.

        Returns:
            int: The current shunt voltage conversion time (0-7).
            0: 140µs, 1: 204µs, 2: 332µs, 3: 588µs,
            4: 1ms, 5: 2ms, 6: 4ms, 7: 8ms
        """
        return self._get_register_bits(CONFIGURATION, 3, 3)

    @shunt_voltage_conv_time.setter
    def shunt_voltage_conv_time(self, conv_time: int) -> None:
        if conv_time < 0 or conv_time > 7:
            raise ValueError("Conversion time must be between 0 and 7")
        self._set_register_bits(CONFIGURATION, 3, 3, int(conv_time))

    @property
    def bus_voltage_conv_time(self) -> int:
        """Bus voltage conversion time.

        Returns:
            int: The current bus voltage conversion time (0-7).
            0: 140µs, 1: 204µs, 2: 332µs, 3: 588µs,
            4: 1ms, 5: 2ms, 6: 4ms, 7: 8ms
        """
        return self._get_register_bits(CONFIGURATION, 6, 3)

    @bus_voltage_conv_time.setter
    def bus_voltage_conv_time(self, conv_time: int) -> None:
        if conv_time < 0 or conv_time > 7:
            raise ValueError("Conversion time must be between 0 and 7")
        self._set_register_bits(CONFIGURATION, 6, 3, int(conv_time))

    @property
    def averaging_mode(self) -> int:
        """Averaging mode.

        Returns:
            int: The current averaging mode (0-7).
            0: 1 SAMPLE, 1: 4_SAMPLES, 2: 16_SAMPLES,
            3: 64_SAMPLES, 4: 128_SAMPLES, 5: 256_SAMPLES,
            6: 512_SAMPLES, 7: 1024_SAMPLES
        """
        return self._get_register_bits(CONFIGURATION, 9, 3)

    @averaging_mode.setter
    def averaging_mode(self, mode: int) -> None:
        if mode < 0 or mode > 7:
            raise ValueError("Averaging mode must be between 0 and 7")
        self._set_register_bits(CONFIGURATION, 9, 3, int(mode))

    @property
    def flags(self) -> int:
        """Flag indicators from the Mask/Enable register.

        Returns:
            int: The current flag indicators from the Mask/Enable register,
            masked for relevant flag bits.
        """
        return self._get_register_bits(MASK_ENABLE, 0, 10)

    @property
    def power_valid_limits(self) -> tuple:
        """Power-Valid upper and lower voltage limits in volts.

        Returns:
            tuple: A tuple containing the lower and upper voltage limits
            in volts as (lower_limit, upper_limit).
        """
        # LSB value is 8 mV -- Datasheet: 8.6.2.17/.18
        LSB = BUS_V_LSB
        lower_limit = self._register_value_getter(addr=POWERVALID_LOWERLIMIT, lsb=LSB, shift=3)
        upper_limit = self._register_value_getter(addr=POWERVALID_UPPERLIMIT, lsb=LSB, shift=3)
        return lower_limit, upper_limit

    @power_valid_limits.setter
    def power_valid_limits(self, limits: tuple) -> None:
        if len(limits) != 2:
            raise ValueError("Must provide both lower and upper voltage limits.")
        # LSB value is 8 mV -- Datasheet: 8.6.2.17/.18
        LSB = BUS_V_LSB
        self._register_value_setter(addr=POWERVALID_LOWERLIMIT, value=limits[0], lsb=LSB, shift=3)
        self._register_value_setter(addr=POWERVALID_UPPERLIMIT, value=limits[1], lsb=LSB, shift=3)

    @property
    def shunt_voltage_sum(self) -> float:
        LSB = SHUNT_V_LSB
        return self._register_value_getter(addr=SHUNTVOLTAGE_SUM, lsb=LSB, shift=1)

    @property
    def shunt_voltage_sum_limit(self) -> float:
        LSB = SHUNT_V_LSB
        return self._register_value_getter(addr=SHUNTVOLTAGE_SUM_LIMIT, lsb=LSB, shift=1)

    @shunt_voltage_sum_limit.setter
    def shunt_voltage_sum_limit(self, limit: float | int) -> None:
        LSB = SHUNT_V_LSB
        self._register_value_setter(addr=POWERVALID_UPPERLIMIT, value=limit, lsb=LSB, shift=1)

    def _register_value_getter(
        self, addr: int, bits: int = 16, lsb: float = 1.0, shift: int = 0
    ) -> float:
        offset = 0
        raw_value = self._get_register_bits(reg=addr, offset=offset, len=bits)
        value = _to_signed(raw_value, shift, bits) * lsb
        return value

    def _register_value_setter(
        self, addr: int, value: float | int, bits: int = 16, lsb: float = 1.0, shift: int = 0
    ) -> None:
        offset = 0
        # Convert the value into number of LSB-value steps and twos-complement
        bitval = _to_2comp(int(value / lsb), shift, bits)
        self._set_register_bits(reg=addr, offset=offset, len=bits, value=bitval)

    def _get_register_bits(self, reg, offset, len):
        """return given bits from register"""
        value = self._read_register(reg, 2)
        value = (value[0] << 8) | value[1]  # swap bytes
        mask = _mask(offset, len, read=True)
        return (value & mask) >> offset

    def _set_register_bits(self, reg, offset, len, value):
        """set given bits of register"""
        old = self._read_register(reg, 2)
        old = (old[0] << 8) | old[1]  # swap bytes
        mask = _mask(offset, len, read=False)
        new = (old & mask) | value << offset
        high_byte = (new >> 8) & 0xFF
        low_byte = new & 0xFF
        self._write_register(reg, bytes([high_byte, low_byte]))

    def _write_register(self, reg, data):
        with self.i2c_dev:
            self.i2c_dev.write(bytes([reg]) + data)

    def _read_register(self, reg, length):
        result = bytearray(length)
        try:
            with self.i2c_dev:
                self.i2c_dev.write(bytes([reg]))
                self.i2c_dev.readinto(result)
        except OSError as ex:
            print(f"I2C error: {ex}")
            return None
        return result
