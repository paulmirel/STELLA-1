# SPDX-FileCopyrightText: Copyright (c) 2025 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_sths34pf80`
================================================================================

CircuitPython driver for the Adafruit STHS34PF80 IR Presence / Motion Sensor - STEMMA QT / Qwiic


* Author(s): Liz Clark

Implementation Notes
--------------------

**Hardware:**

* `Adafruit STHS34PF80 IR Presence / Motion Sensor <https://www.adafruit.com/product/6426>`_"

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
* Adafruit's Register library: https://github.com/adafruit/Adafruit_CircuitPython_Register
"""

import time

from adafruit_bus_device.i2c_device import I2CDevice
from adafruit_register.i2c_bit import ROBit, RWBit
from adafruit_register.i2c_bits import RWBits
from adafruit_register.i2c_struct import ROUnaryStruct, UnaryStruct
from micropython import const

try:
    import typing  # pylint: disable=unused-import

    from busio import I2C
except ImportError:
    pass

__version__ = "1.0.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_STHS34PF80.git"

# Register addresses
_LPF1 = const(0x0C)
_LPF2 = const(0x0D)
_WHO_AM_I = const(0x0F)
_AVG_TRIM = const(0x10)
_CTRL0 = const(0x17)
_SENS_DATA = const(0x1D)
_CTRL1 = const(0x20)
_CTRL2 = const(0x21)
_CTRL3 = const(0x22)
_STATUS = const(0x23)
_FUNC_STATUS = const(0x25)
_TOBJECT_L = const(0x26)
_TAMBIENT_L = const(0x28)
_TOBJ_COMP_L = const(0x38)
_TPRESENCE_L = const(0x3A)
_TMOTION_L = const(0x3C)
_TAMB_SHOCK_L = const(0x3E)

# Embedded function registers
_FUNC_CFG_ADDR = const(0x08)
_FUNC_CFG_DATA = const(0x09)
_PAGE_RW = const(0x11)

# Embedded function addresses
_EMBEDDED_RESET_ALGO = const(0x2A)

# Device ID
_DEVICE_ID = const(0xD3)

# Default I2C address
DEFAULT_ADDR = const(0x5A)

# Low-pass filter configuration options
LPF_ODR_DIV_9 = const(0x00)
LPF_ODR_DIV_20 = const(0x01)
LPF_ODR_DIV_50 = const(0x02)
LPF_ODR_DIV_100 = const(0x03)
LPF_ODR_DIV_200 = const(0x04)
LPF_ODR_DIV_400 = const(0x05)
LPF_ODR_DIV_800 = const(0x06)

# Ambient temperature averaging options
AVG_T_8 = const(0x00)
AVG_T_4 = const(0x01)
AVG_T_2 = const(0x02)
AVG_T_1 = const(0x03)

# Object temperature averaging options
AVG_TMOS_2 = const(0x00)
AVG_TMOS_8 = const(0x01)
AVG_TMOS_32 = const(0x02)
AVG_TMOS_128 = const(0x03)
AVG_TMOS_256 = const(0x04)
AVG_TMOS_512 = const(0x05)
AVG_TMOS_1024 = const(0x06)
AVG_TMOS_2048 = const(0x07)

# Output data rate options
ODR_POWER_DOWN = const(0x00)
ODR_0_25_HZ = const(0x01)
ODR_0_5_HZ = const(0x02)
ODR_1_HZ = const(0x03)
ODR_2_HZ = const(0x04)
ODR_4_HZ = const(0x05)
ODR_8_HZ = const(0x06)
ODR_15_HZ = const(0x07)
ODR_30_HZ = const(0x08)

# Interrupt signal options
INT_HIGH_Z = const(0x00)
INT_DRDY = const(0x01)
INT_OR = const(0x02)

# Validation dictionaries for properties
_ODR_VALUES = {
    ODR_POWER_DOWN: "POWER_DOWN",
    ODR_0_25_HZ: "0.25 Hz",
    ODR_0_5_HZ: "0.5 Hz",
    ODR_1_HZ: "1 Hz",
    ODR_2_HZ: "2 Hz",
    ODR_4_HZ: "4 Hz",
    ODR_8_HZ: "8 Hz",
    ODR_15_HZ: "15 Hz",
    ODR_30_HZ: "30 Hz",
}

_AVG_T_VALUES = {
    AVG_T_8: "8 samples",
    AVG_T_4: "4 samples",
    AVG_T_2: "2 samples",
    AVG_T_1: "1 sample",
}

_AVG_TMOS_VALUES = {
    AVG_TMOS_2: "2 samples",
    AVG_TMOS_8: "8 samples",
    AVG_TMOS_32: "32 samples",
    AVG_TMOS_128: "128 samples",
    AVG_TMOS_256: "256 samples",
    AVG_TMOS_512: "512 samples",
    AVG_TMOS_1024: "1024 samples",
    AVG_TMOS_2048: "2048 samples",
}

_LPF_VALUES = {
    LPF_ODR_DIV_9: "ODR/9",
    LPF_ODR_DIV_20: "ODR/20",
    LPF_ODR_DIV_50: "ODR/50",
    LPF_ODR_DIV_100: "ODR/100",
    LPF_ODR_DIV_200: "ODR/200",
    LPF_ODR_DIV_400: "ODR/400",
    LPF_ODR_DIV_800: "ODR/800",
}

_INT_SIGNAL_VALUES = {INT_HIGH_Z: "High-Z", INT_DRDY: "Data Ready", INT_OR: "INT OR"}


class STHS34PF80:
    """Driver for the STHS34PF80 IR presence and motion sensor.

    :param ~busio.I2C i2c: The I2C bus to use
    :param int address: The I2C device address. Default is 0x5A
    """

    # Register definitions using adafruit_register
    _device_id = ROUnaryStruct(_WHO_AM_I, "<B")

    # LPF1 register bits
    _lpf_motion = RWBits(3, _LPF1, 0)
    _lpf_motion_presence = RWBits(3, _LPF1, 3)

    # LPF2 register bits
    _lpf_temperature = RWBits(3, _LPF2, 0)
    _lpf_presence = RWBits(3, _LPF2, 3)

    # Averaging configuration
    _avg_tmos = RWBits(3, _AVG_TRIM, 0)
    _avg_t = RWBits(2, _AVG_TRIM, 4)

    # Gain mode
    _gain_mode = RWBits(3, _CTRL0, 4)

    # Sensitivity
    _sensitivity_raw = UnaryStruct(_SENS_DATA, "<b")  # Signed 8-bit

    # CTRL1 register
    _odr = RWBits(4, _CTRL1, 0)
    block_data_update = RWBit(_CTRL1, 4)
    """Block data update configuration (True or False)"""

    # CTRL2 register
    _one_shot = RWBit(_CTRL2, 0)
    _func_cfg_access = RWBit(_CTRL2, 4)
    _boot = RWBit(_CTRL2, 7)

    # CTRL3 register - interrupt configuration
    _int_signal = RWBits(2, _CTRL3, 0)
    interrupt_latched = RWBit(_CTRL3, 2)
    """Interrupt latched (True or False)"""
    _int_mask = RWBits(3, _CTRL3, 3)
    interrupt_open_drain = RWBit(_CTRL3, 6)
    """Set interrupt as open drain (True or False)"""
    interrupt_polarity = RWBit(_CTRL3, 7)
    """Interrupt polarity configuration (True or False)"""

    # Status registers
    data_ready = ROBit(_STATUS, 2)
    """Check if new data is ready"""

    # Function status
    temperature_shock = ROBit(_FUNC_STATUS, 0)
    """Check if ambient temperature shock is detected"""
    motion = ROBit(_FUNC_STATUS, 1)
    """Check if motion is detected"""
    presence = ROBit(_FUNC_STATUS, 2)
    """Check if presence is detected"""

    # Data registers
    object_temperature = ROUnaryStruct(_TOBJECT_L, "<h")  # Signed 16-bit
    """Read raw object temperature value"""
    _tambient_raw = ROUnaryStruct(_TAMBIENT_L, "<h")  # Signed 16-bit
    compensated_object_temperature = ROUnaryStruct(_TOBJ_COMP_L, "<h")  # Signed 16-bit
    """Read compensated object temperature raw value"""
    presence_value = ROUnaryStruct(_TPRESENCE_L, "<h")  # Signed 16-bit
    """Read presence detection raw value"""
    motion_value = ROUnaryStruct(_TMOTION_L, "<h")  # Signed 16-bit
    """Read motion detection raw value"""
    temperature_shock_value = ROUnaryStruct(_TAMB_SHOCK_L, "<h")  # Signed 16-bit
    """Read ambient temperature shock raw value"""

    def __init__(self, i2c: I2C, address: int = DEFAULT_ADDR) -> None:
        self.i2c_device = I2CDevice(i2c, address)

        # Check device ID
        if self._device_id != _DEVICE_ID:
            raise RuntimeError(f"Failed to find STHS34PF80! Chip ID {self._device_id:#x}")

        # Reset the sensor
        self.reset()

        # Apply recommended default settings
        self.object_averaging = AVG_TMOS_32
        self.ambient_averaging = AVG_T_8
        self.motion_lpf = LPF_ODR_DIV_20
        self.presence_lpf = LPF_ODR_DIV_50
        self.temperature_lpf = LPF_ODR_DIV_100
        self.data_rate = ODR_2_HZ
        self.block_data_update = True

    def reset(self) -> None:
        """Reset the sensor completely"""
        # Reboot OTP memory
        self._boot = True
        time.sleep(0.005)  # Wait 5ms for reboot

        # Reset the internal algorithm
        self._algorithm_reset()

    def _algorithm_reset(self) -> None:
        """Reset the internal algorithm"""
        self._write_embedded_function(_EMBEDDED_RESET_ALGO, bytes([0x01]))

    def _write_embedded_function(self, addr: int, data: bytes) -> None:
        """Write data to embedded function registers

        :param int addr: Embedded function register address
        :param bytes data: Data to write
        """
        # Save current ODR and enter power down mode
        current_odr = self._odr
        self._safe_set_odr(current_odr, ODR_POWER_DOWN)

        # Enable access to embedded functions register
        self._func_cfg_access = True

        # Enable write mode in PAGE_RW register
        with self.i2c_device as i2c:
            # Set write mode bit (bit 6 of PAGE_RW register)
            i2c.write_then_readinto(bytes([_PAGE_RW]), bytearray(1))
            page_rw_val = bytearray(1)
            i2c.readinto(page_rw_val)
            page_rw_val[0] |= 0x40  # Set bit 6
            i2c.write(bytes([_PAGE_RW, page_rw_val[0]]))

            # Set the address
            i2c.write(bytes([_FUNC_CFG_ADDR, addr]))

            # Write the data
            for byte in data:
                i2c.write(bytes([_FUNC_CFG_DATA, byte]))

            # Disable write mode
            page_rw_val[0] &= ~0x40  # Clear bit 6
            i2c.write(bytes([_PAGE_RW, page_rw_val[0]]))

        # Disable access to embedded functions register
        self._func_cfg_access = False

        # Restore ODR
        self._safe_set_odr(ODR_POWER_DOWN, current_odr)

    def _safe_set_odr(self, current_odr: int, new_odr: int) -> None:
        """Safely set the output data rate with proper algorithm reset

        :param int current_odr: Current ODR value
        :param int new_odr: New ODR value to set
        """
        if new_odr > ODR_POWER_DOWN:
            # Do a clean reset algo procedure when changing to operative state
            self._odr = ODR_POWER_DOWN
            self._algorithm_reset()
        elif current_odr > ODR_POWER_DOWN:
            # Clear DRDY by reading function status
            _ = self._read_register(_FUNC_STATUS)

            # Wait for DRDY to be set
            timeout = 1.0  # 1 second timeout
            start = time.monotonic()
            while not self.data_ready:
                if time.monotonic() - start > timeout:
                    break  # Continue even on timeout
                time.sleep(0.001)

            # Set ODR to power down
            self._odr = ODR_POWER_DOWN

            # Clear DRDY again
            _ = self._read_register(_FUNC_STATUS)

        # Set the new ODR
        self._odr = new_odr

    def _read_register(self, address: int, length: int = 1) -> bytearray:
        """Read register(s) from the sensor

        :param int address: Register address
        :param int length: Number of bytes to read
        :return: Register value(s)
        """
        result = bytearray(length)
        with self.i2c_device as i2c:
            i2c.write_then_readinto(bytes([address]), result)
        return result

    @property
    def trigger_oneshot(self) -> None:
        """Trigger a one-shot measurement"""
        self._one_shot = True

    @property
    def ambient_temperature(self) -> float:
        """Read ambient temperature in degrees Celsius

        :return: Ambient temperature in °C
        """
        return self._tambient_raw / 100.0

    @property
    def motion_lpf(self) -> int:
        """Motion detection low-pass filter configuration

        :return: LPF configuration value
        """
        return self._lpf_motion

    @motion_lpf.setter
    def motion_lpf(self, value: int) -> None:
        """Set motion detection low-pass filter configuration

        :param int value: LPF configuration value (LPF_ODR_DIV_*)
        """
        if value not in _LPF_VALUES:
            raise ValueError(f"Invalid LPF value. Must be one of: {list(_LPF_VALUES.keys())}")
        self._lpf_motion = value

    @property
    def motion_presence_lpf(self) -> int:
        """Motion and presence detection low-pass filter configuration

        :return: LPF configuration value
        """
        return self._lpf_motion_presence

    @motion_presence_lpf.setter
    def motion_presence_lpf(self, value: int) -> None:
        """Set motion and presence detection low-pass filter configuration

        :param int value: LPF configuration value (LPF_ODR_DIV_*)
        """
        if value not in _LPF_VALUES:
            raise ValueError(f"Invalid LPF value. Must be one of: {list(_LPF_VALUES.keys())}")
        self._lpf_motion_presence = value

    @property
    def presence_lpf(self) -> int:
        """Presence detection low-pass filter configuration

        :return: LPF configuration value
        """
        return self._lpf_presence

    @presence_lpf.setter
    def presence_lpf(self, value: int) -> None:
        """Set presence detection low-pass filter configuration

        :param int value: LPF configuration value (LPF_ODR_DIV_*)
        """
        if value not in _LPF_VALUES:
            raise ValueError(f"Invalid LPF value. Must be one of: {list(_LPF_VALUES.keys())}")
        self._lpf_presence = value

    @property
    def temperature_lpf(self) -> int:
        """Ambient temperature shock detection low-pass filter configuration

        :return: LPF configuration value
        """
        return self._lpf_temperature

    @temperature_lpf.setter
    def temperature_lpf(self, value: int) -> None:
        """Set ambient temperature shock detection low-pass filter configuration

        :param int value: LPF configuration value (LPF_ODR_DIV_*)
        """
        if value not in _LPF_VALUES:
            raise ValueError(f"Invalid LPF value. Must be one of: {list(_LPF_VALUES.keys())}")
        self._lpf_temperature = value

    @property
    def ambient_averaging(self) -> int:
        """Ambient temperature averaging configuration

        :return: Averaging configuration value
        """
        return self._avg_t

    @ambient_averaging.setter
    def ambient_averaging(self, value: int) -> None:
        """Set ambient temperature averaging configuration

        :param int value: Averaging value (AVG_T_*)
        """
        if value not in _AVG_T_VALUES:
            raise ValueError(
                f"Invalid averaging value. Must be one of: {list(_AVG_T_VALUES.keys())}"
            )
        self._avg_t = value

    @property
    def object_averaging(self) -> int:
        """Object temperature averaging configuration

        :return: Averaging configuration value
        """
        return self._avg_tmos

    @object_averaging.setter
    def object_averaging(self, value: int) -> None:
        """Set object temperature averaging configuration

        :param int value: Averaging value (AVG_TMOS_*)
        """
        if value not in _AVG_TMOS_VALUES:
            raise ValueError(
                f"Invalid averaging value. Must be one of: {list(_AVG_TMOS_VALUES.keys())}"
            )
        self._avg_tmos = value

    @property
    def gain_mode(self) -> bool:
        """Wide gain mode configuration

        :return: True if wide mode is enabled
        """
        return self._gain_mode == 0x00

    @gain_mode.setter
    def gain_mode(self, value: bool) -> None:
        """Set wide gain mode configuration

        :param bool value: True for wide mode, False for default gain mode
        """
        self._gain_mode = 0x00 if value else 0x07

    @property
    def sensitivity(self) -> int:
        """Sensitivity value for ambient temperature compensation

        :return: Signed 8-bit sensitivity value
        """
        return self._sensitivity_raw

    @sensitivity.setter
    def sensitivity(self, value: int) -> None:
        """Set sensitivity value for ambient temperature compensation

        :param int value: Signed 8-bit sensitivity value (-128 to 127)
        """
        if value < -128 or value > 127:
            raise ValueError("Sensitivity must be between -128 and 127")
        self._sensitivity_raw = value

    @property
    def data_rate(self) -> int:
        """Output data rate configuration

        :return: Current data rate value
        """
        return self._odr

    @data_rate.setter
    def data_rate(self, value: int) -> None:
        """Set output data rate configuration with validation

        :param int value: Data rate value (ODR_*)
        """
        if value not in _ODR_VALUES:
            raise ValueError(f"Invalid ODR value. Must be one of: {list(_ODR_VALUES.keys())}")

        # Get maximum ODR based on current averaging setting
        max_odr = ODR_30_HZ

        avg_tmos = self._avg_tmos
        if avg_tmos == AVG_TMOS_128:
            max_odr = ODR_8_HZ
        elif avg_tmos == AVG_TMOS_256:
            max_odr = ODR_4_HZ
        elif avg_tmos == AVG_TMOS_512:
            max_odr = ODR_2_HZ
        elif avg_tmos == AVG_TMOS_1024:
            max_odr = ODR_1_HZ
        elif avg_tmos == AVG_TMOS_2048:
            max_odr = ODR_0_5_HZ

        if value > max_odr:
            raise ValueError(f"ODR {_ODR_VALUES[value]} exceeds maximum {_ODR_VALUES[max_odr]}")

        current_odr = self._odr
        self._safe_set_odr(current_odr, value)

    @property
    def interrupt_mask(self) -> int:
        """Interrupt mask for function status flags

        :return: Current interrupt mask value
        """
        return self._int_mask

    @interrupt_mask.setter
    def interrupt_mask(self, value: int) -> None:
        """Set interrupt mask for function status flags

        :param int value: Mask value (bits 0-2 for TAMB_SHOCK, MOT, PRES flags)
        """
        if value > 0x07:
            raise ValueError("Interrupt mask must be 0-7")
        self._int_mask = value

    @property
    def interrupt_signal(self) -> int:
        """Interrupt signal type configuration

        :return: Current interrupt signal type
        """
        return self._int_signal

    @interrupt_signal.setter
    def interrupt_signal(self, value: int) -> None:
        """Set interrupt signal type

        :param int value: Signal type (INT_*)
        """
        if value not in _INT_SIGNAL_VALUES:
            raise ValueError(
                f"Invalid interrupt signal value. Must be one of: {list(_INT_SIGNAL_VALUES.keys())}"
            )
        self._int_signal = value
