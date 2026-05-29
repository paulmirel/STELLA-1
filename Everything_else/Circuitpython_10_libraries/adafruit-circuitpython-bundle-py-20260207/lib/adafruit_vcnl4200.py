# SPDX-FileCopyrightText: Copyright (c) 2024 Liz Clark, Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Written by Liz Clark & Tim Cocks (Adafruit Industries) with OpenAI ChatGPT 4o May 13, 2024 build
# https://help.openai.com/en/articles/6825453-chatgpt-release-notes

# https://chatgpt.com/share/6720fdc1-2bc0-8006-8f7c-f0ff11189ea9
"""
`adafruit_vcnl4200`
================================================================================

CircuitPython driver for the Adafruit VCNL4200 Long Distance IR Proximity and Light Sensor


* Author(s): Liz Clark, Tim Cocks

Implementation Notes
--------------------

**Hardware:**

* `Adafruit VCNL4200 Long Distance IR Proximity and Light Sensor <https://www.adafruit.com/product/6064>`_

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
from adafruit_register.i2c_struct import ROUnaryStruct, Struct, UnaryStruct
from micropython import const

try:
    import typing

    from busio import I2C
except ImportError:
    pass

__version__ = "1.0.2"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_VCNL4200.git"

_I2C_ADDRESS = const(0x51)  # Default I2C address for VCNL4200

# Register addresses
_ALS_CONF = const(0x00)  # ALS configuration register
_ALS_THDH = const(0x01)  # ALS high threshold register
_ALS_THDL = const(0x02)  # ALS low threshold register
_PS_CONF12 = const(0x03)  # Proximity sensor configuration register 1 & 2
_PS_CONF3MS = const(0x04)  # Proximity sensor configuration register 3 & MS
_PS_CANC_LVL = const(0x05)  # Proximity cancellation level register
_PS_THDL = const(0x06)  # Proximity sensor low threshold register
_PS_THDH = const(0x07)  # Proximity sensor high threshold register
_PS_DATA = const(0x08)  # Proximity sensor data register
_ALS_DATA = const(0x09)  # ALS data register
_WHITE_DATA = const(0x0A)  # White sensor register
_INT_FLAG = const(0x0D)  # Interrupt flag register
_ID = const(0x0E)  # Device ID register

# Interrupt flags
_INTFLAG_PROX_UPFLAG = const(0x80)  # Proximity code saturation flag
_INTFLAG_PROX_SPFLAG = const(0x40)  # Proximity sunlight protection flag
_INTFLAG_ALS_LOW = const(0x20)  # ALS interrupt flag
_INTFLAG_ALS_HIGH = const(0x10)  # Proximity interrupt flag
_INTFLAG_PROX_CLOSE = const(0x02)  # Proximity THDH trigger
_INTFLAG_PROX_AWAY = const(0x01)  # Proximity THDL trigger

# ALS Integration Time settings
ALS_IT = {
    "50MS": const(0x00),  # 50 ms integration time
    "100MS": const(0x01),  # 100 ms integration time
    "200MS": const(0x02),  # 200 ms integration time
    "400MS": const(0x03),  # 400 ms integration time
}

# ALS Persistence settings
ALS_PERS = {
    "1": const(0x00),  # ALS persistence 1 conversion
    "2": const(0x01),  # ALS persistence 2 conversions
    "4": const(0x02),  # ALS persistence 4 conversions
    "8": const(0x03),  # ALS persistence 8 conversions
}

# Proximity Sensor Integration Time settings
PS_IT = {
    "1T": const(0x00),  # Proximity integration time 1T
    "2T": const(0x01),  # Proximity integration time 2T
    "3T": const(0x02),  # Proximity integration time 3T
    "4T": const(0x03),  # Proximity integration time 4T
    "8T": const(0x04),  # Proximity integration time 8T
    "9T": const(0x05),  # Proximity integration time 9T
}

# Proximity Sensor Persistence settings
PS_PERS = {
    "1": const(0x00),  # Proximity persistence 1 conversion
    "2": const(0x01),  # Proximity persistence 2 conversions
    "3": const(0x02),  # Proximity persistence 3 conversions
    "4": const(0x03),  # Proximity persistence 4 conversions
}

# Proximity Sensor Duty settings
PS_DUTY = {
    "1_160": const(0x00),  # Proximity duty cycle 1/160
    "1_320": const(0x01),  # Proximity duty cycle 1/320
    "1_640": const(0x02),  # Proximity duty cycle 1/640
    "1_1280": const(0x03),  # Proximity duty cycle 1/1280
}

# Proximity Sensor Interrupt settings
PS_INT = {
    "DISABLE": const(0x00),  # Proximity interrupt disabled
    "CLOSE": const(0x01),  # Proximity interrupt when an object is close
    "AWAY": const(0x02),  # Proximity interrupt when an object is away
    "BOTH": const(0x03),  # Proximity interrupt for both close and away
}

# LED Current settings
LED_I = {
    "50MA": const(0x00),  # LED current 50mA
    "75MA": const(0x01),  # LED current 75mA
    "100MA": const(0x02),  # LED current 100mA
    "120MA": const(0x03),  # LED current 120mA
    "140MA": const(0x04),  # LED current 140mA
    "160MA": const(0x05),  # LED current 160mA
    "180MA": const(0x06),  # LED current 180mA
    "200MA": const(0x07),  # LED current 200mA
}

# Proximity Sensor Multi Pulse settings
PS_MPS = {
    "1": const(0x00),  # Proximity multi pulse 1
    "2": const(0x01),  # Proximity multi pulse 2
    "4": const(0x02),  # Proximity multi pulse 4
    "8": const(0x03),  # Proximity multi pulse 8
}


class Adafruit_VCNL4200:
    """
    Driver for VCNL4200 Proximity & Light Sensor

    :param i2c: I2C bus
    :param addr: I2C Address if not using default
    """

    # Device ID expected value for VCNL4200
    _DEVICE_ID = 0x1058

    # Register for ALS configuration
    als_shutdown = RWBits(1, _ALS_CONF, 0)  # ALS shutdown bit
    """Enables or disables the ALS (Ambient Light Sensor) shutdown mode.
    Controls the power state of the ALS, allowing it to be shut down to conserve power.
    Set to true to enable shutdown mode (power off ALS), false to disable (power on ALS)."""
    als_threshold_low = UnaryStruct(_ALS_THDL, "<H")
    """The 16-bit numerical low threshold for the ALS (Ambient Light Sensor) interrupt.
    If the ALS reading falls below this threshold and ALS interrupt is enabled, an interrupt
    will be triggered."""
    als_threshold_high = UnaryStruct(_ALS_THDH, "<H")
    """The 16-bit numerical upper limit for proximity detection.If the proximity reading
    exceeds this threshold and the interrupt is enabled, an interrupt will be triggered."""
    prox_hd = RWBit(_PS_CONF12, 11)
    """The proximity sensor (PS) resolution to high definition (HD). Set to True to enable
    high definition mode (16-bit resolution), False for standard resolution (12-bit)."""
    prox_shutdown = RWBit(_PS_CONF12, 0)  # Bit 0: PS_SD (Proximity Sensor Shutdown)
    """The proximity sensor (PS) shutdown mode. Set to True to enable shutdown mode
    (power off proximity sensor), false to disable (power on proximity sensor)."""
    proximity = ROUnaryStruct(_PS_DATA, "<H")
    """The current proximity data from the proximity sensor (PS)."""
    lux = ROUnaryStruct(_ALS_DATA, "<H")
    """The current lux data from ambient light sensor (ALS)"""
    _prox_multi_pulse = RWBits(2, _PS_CONF3MS, 5, register_width=2)
    _prox_interrupt = RWBits(2, _PS_CONF12, 8, register_width=2)
    _prox_duty = RWBits(2, _PS_CONF12, 6, register_width=2)
    _prox_integration_time = RWBits(3, _PS_CONF12, 1, register_width=2)
    _prox_persistence = RWBits(2, _PS_CONF12, 4, register_width=2)
    prox_sun_cancellation = RWBit(_PS_CONF3MS, 0, register_width=2)
    """The sunlight cancellation feature for the proximity sensor (PS).
    Controls the sunlight cancellation feature, which improves proximity
    detection accuracy in bright or sunny conditions by mitigating background
    light interference. Set to true to enable sunlight cancellation, false to disable
    it."""
    prox_sunlight_double_immunity = RWBit(_PS_CONF3MS, 1, register_width=2)
    """Double immunity mode to sunlight for the proximity
    sensor (PS). Configures an enhanced sunlight immunity mode, which increases the sensor’s
    ability to filter out interference from bright sunlight for improved proximity detection.
    Set to True to enable double sunlight immunity, False to disable it."""
    prox_active_force = RWBit(_PS_CONF3MS, 3, register_width=2)
    """The active force mode for the proximity sensor (PS). Configures the proximity
    sensor to operate in active force mode, where measurements are taken only when
    manually triggered by `trigger_prox()`. Set to True to enable active force mode,
    False to disable it."""
    prox_smart_persistence = RWBit(_PS_CONF3MS, 4, register_width=2)
    """The smart persistence mode for the proximity sensor (PS).
    Configures the smart persistence feature, which helps reduce false triggers
    by adjusting the persistence behavior based on ambient conditions.
    Set to True to enable smart persistence, False to disable it."""
    sun_protect_polarity = RWBit(_PS_CONF3MS, 3 + 8, register_width=2)
    """The polarity of the sunlight protection output for the proximity sensor (PS).
    Configures the polarity of the sunlight protection output signal, which
    affects how sunlight interference is managed in proximity detection.
    Set to True for active high polarity, False for active low polarity."""
    prox_boost_typical_sunlight_capability = RWBit(_PS_CONF3MS, 4 + 8, register_width=2)
    """The boosted sunlight protection capability for the proximity sensor (PS).
    Boosts the proximity sensor's resistance to typical sunlight interference for
    more reliable proximity measurements in bright ambient conditions.
    Set to true to enable boosted sunlight protection, false to disable it."""
    prox_interrupt_logic_mode = RWBit(_PS_CONF3MS, 7 + 8, register_width=2)
    """The interrupt logic mode for the proximity sensor (PS). Configures
    the interrupt output logic mode for the proximity sensor, determining if
    the interrupt signal is active high or active low. Set to True for active
    high logic, False for active low logic."""
    prox_cancellation_level = UnaryStruct(
        _PS_CANC_LVL, "<H"
    )  # 16-bit registor for cancellation level
    """The 16-bit numerical proximity sensor (PS) cancellation level. Configures
    the cancellation level for the proximity sensor, which helps to
    reduce interference from background light by subtracting a baseline level."""
    prox_int_threshold_low = UnaryStruct(
        _PS_THDL, "<H"
    )  # 16-bit register for proximity threshold low
    """The 16-bit numerical low threshold for the proximity sensor (PS) interrupt.
    Configures the lower limit for proximity detection. If the proximity reading
    falls below this threshold and the interrupt is enabled, an interrupt will be
    triggered."""
    prox_int_threshold_high = UnaryStruct(
        _PS_THDH, "<H"
    )  # 16-bit register for proximity threshold high
    """The 16-bit numerical high threshold for the proximity sensor (PS) interrupt.
    Configures the upper limit for proximity detection. If the proximity reading
    exceeds this threshold and the interrupt is enabled, an interrupt will be
    triggered."""
    _interrupt_flags = RWBits(8, _INT_FLAG, 0, register_width=2)
    _prox_led_current = RWBits(3, _PS_CONF3MS, 8, register_width=2)
    white_light = ROUnaryStruct(_WHITE_DATA, "<H")  # 16-bit register for white light data
    """The current white light data. The 16-bit numerical raw white light measurement, representing
    the sensor’s sensitivity to white light."""
    _als_int_time = RWBits(2, _ALS_CONF, 6, register_width=2)
    _als_persistence = RWBits(2, _ALS_CONF, 2, register_width=2)
    _als_int_en = RWBits(1, _ALS_CONF, 1)  # Bit 1: ALS interrupt enable
    _als_int_switch = RWBits(1, _ALS_CONF, 5)  # Bit 5: ALS interrupt channel selection (white/ALS)
    _proximity_int_en = RWBits(1, _PS_CONF12, 0)
    _prox_trigger = RWBit(_PS_CONF3MS, 2)
    _device_id = UnaryStruct(_ID, "<H")
    _raw_interrupt_flags = UnaryStruct(_INT_FLAG, "<H")  # 2-byte read, big endian

    def __init__(self, i2c: I2C, addr: int = _I2C_ADDRESS) -> None:
        self.i2c_device = I2CDevice(i2c, addr)
        if self._device_id != self._DEVICE_ID:
            raise RuntimeError("Device ID mismatch.")
        try:
            self.als_shutdown = False
            self.als_integration_time = ALS_IT["50MS"]
            self.als_persistence = ALS_PERS["1"]
            self.als_threshold_low = 0
            self.als_threshold_high = 0xFFFF
            self.als_interrupt(enabled=True, white_channel=False)
            self.prox_duty = PS_DUTY["1_160"]
            self.prox_shutdown = False
            self.prox_integration_time = PS_IT["1T"]
            self.prox_persistence = PS_PERS["1"]
        except Exception as error:
            raise RuntimeError(f"Failed to initialize: {error}") from error

    def als_interrupt(self, enabled: bool, white_channel: bool) -> bool:
        """Configure ALS interrupt settings, enabling or disabling
        the interrupt and selecting the interrupt channel.

        :return bool: True if setting the values succeeded, False otherwise."""
        try:
            self._als_int_en = enabled
            self._als_int_switch = white_channel
            return True
        except OSError:
            return False

    def trigger_prox(self) -> bool:
        """Triggers a single proximity measurement manually in active force mode.
        Initiates a one-time proximity measurement in active force mode. This can be
        used when proximity measurements are not continuous and need to be triggered
        individually.

        :return bool: True if triggering succeeded, False otherwise."""
        try:
            self._prox_trigger = True
            return True
        except OSError:
            return False

    @property
    def prox_interrupt(self) -> str:
        """Interrupt mode for the proximity sensor
        Configures the interrupt condition for the proximity sensor, which determines
        when an interrupt will be triggered based on the detected proximity.

        :return str: The interrupt mode for the proximity sensor.
        """
        PS_INT_REVERSE = {value: key for key, value in PS_INT.items()}
        # Return the mode name if available, otherwise return "Unknown"
        return PS_INT_REVERSE.get(self._prox_interrupt, "Unknown")

    @prox_interrupt.setter
    def prox_interrupt(self, mode: int) -> None:
        if mode not in PS_INT.values():
            raise ValueError("Invalid interrupt mode")
        self._prox_interrupt = mode

    @property
    def prox_duty(self) -> str:
        """Proximity sensor duty cycle setting.
        Configures the duty cycle of the infrared emitter for the proximity sensor,
        which affects power consumption and response time.

        :return str: The duty cycle of the infrared emitter for the proximity sensor."""
        # Reverse lookup dictionary for PS_DUTY
        PS_DUTY_REVERSE = {value: key for key, value in PS_DUTY.items()}
        return PS_DUTY_REVERSE.get(self._prox_duty, "Unknown")

    @prox_duty.setter
    def prox_duty(self, setting: int) -> None:
        if setting not in PS_DUTY.values():
            raise ValueError(f"Invalid proximity duty cycle setting: {setting}")
        self._prox_duty = setting

    @property
    def als_integration_time(self) -> str:
        """ALS integration time setting. Configures the integration time for
        the ambient light sensor to control sensitivity and range.

        :return str: The ALS integration time setting"""
        # Reverse lookup dictionary for ALS_IT
        ALS_IT_REVERSE = {value: key for key, value in ALS_IT.items()}
        # Map the result to the setting name, defaulting to "Unknown" if unmatched
        return ALS_IT_REVERSE.get(self._als_int_time, "Unknown")

    @als_integration_time.setter
    def als_integration_time(self, it: int) -> None:
        if it not in ALS_IT.values():
            raise ValueError(f"Invalid ALS integration time setting: {it}")
        self._als_int_time = it

    @property
    def als_persistence(self) -> str:
        """ALS persistence setting. Configures the persistence level
        of the ALS interrupt, which determines how many consecutive ALS threshold
        triggers are required to activate the interrupt.

        :return str: The current persistence setting
        """
        # Reverse lookup dictionary for ALS_PERS
        ALS_PERS_REVERSE = {value: key for key, value in ALS_PERS.items()}
        return ALS_PERS_REVERSE.get(self._als_persistence, "Unknown")

    @als_persistence.setter
    def als_persistence(self, pers: int) -> None:
        if pers not in ALS_PERS.values():
            raise ValueError(f"Invalid ALS persistence setting: {pers}")
        self._als_persistence = pers

    @property
    def prox_multi_pulse(self) -> str:
        """Configures the number of infrared pulses used by the proximity sensor in a
        single measurement. Increasing the pulse count can improve accuracy,
        especially in high ambient light conditions.

        :return str: The number of infrared pulses configured for the proximity sensor
        """
        PS_MP_REVERSE = {value: key for key, value in PS_MPS.items()}
        return PS_MP_REVERSE.get(self._prox_multi_pulse, "Unknown")

    @prox_multi_pulse.setter
    def prox_multi_pulse(self, setting: int) -> None:
        if setting not in PS_MPS.values():
            raise ValueError(f"Invalid PS_MPS setting: {setting}")
        self._prox_multi_pulse = setting

    @property
    def prox_integration_time(self) -> str:
        """Proximity sensor integration time. Configures the integration
        time for the proximity sensor, which affects the duration for which the
        sensor is sensitive to reflected light.

        :return str: The current integration time
        """
        # Reverse lookup dictionary for PS_IT
        PS_IT_REVERSE = {value: key for key, value in PS_IT.items()}
        return PS_IT_REVERSE.get(self._prox_integration_time, "Unknown")

    @prox_integration_time.setter
    def prox_integration_time(self, setting: int) -> None:
        if setting not in PS_IT.values():
            raise ValueError(f"Invalid proximity integration time setting: {setting}")
        self._prox_integration_time = setting

    @property
    def prox_persistence(self) -> str:
        """Proximity sensor persistence setting. Configures the persistence
        level of the proximity sensor interrupt, defining how many consecutive
        threshold triggers are required to activate the interrupt.

        :return str: The current persistence setting
        """
        # Reverse lookup dictionary for PS_PERS
        PS_PERS_REVERSE = {value: key for key, value in PS_PERS.items()}
        return PS_PERS_REVERSE.get(self._prox_persistence, "Unknown")

    @prox_persistence.setter
    def prox_persistence(self, setting: int) -> None:
        if setting not in PS_PERS.values():
            raise ValueError(f"Invalid proximity persistence setting: {setting}")
        self._prox_persistence = setting

    @property
    def prox_led_current(self) -> str:
        """IR LED current setting. Configures the driving current for the
        infrared LED used in proximity detection, which affects the range
        and power consumption of the sensor.

        :return str: The LED current setting"""
        # Reverse lookup dictionary for PS_PERS
        LED_I_REVERSE = {value: key for key, value in LED_I.items()}
        return LED_I_REVERSE.get(self._prox_led_current, "Unknown")

    @prox_led_current.setter
    def prox_led_current(self, setting: int) -> None:
        if setting not in LED_I.values():
            raise ValueError(f"Invalid proximity IR LED current setting: {setting}")
        self._prox_led_current = setting

    @property
    def interrupt_flags(self) -> typing.Dict[str, bool]:
        """The current interrupt flags from the sensor. Retrieves the current
        interrupt status flags, which indicate various sensor states, such as
        threshold crossings or sunlight protection events.

        :return dict: The current interrupt flag values
        """
        # Read the full 16-bit register value and isolate the high byte
        raw_value = (self._raw_interrupt_flags >> 8) & 0xFF
        # Interpret each flag based on the datasheet's bit definition
        return {
            "ALS_HIGH": bool(raw_value & _INTFLAG_ALS_HIGH),
            "PROX_CLOSE": bool(raw_value & _INTFLAG_PROX_CLOSE),
            "ALS_LOW": bool(raw_value & _INTFLAG_ALS_LOW),
            "PROX_AWAY": bool(raw_value & _INTFLAG_PROX_AWAY),
            "PROX_SPFLAG": bool(raw_value & _INTFLAG_PROX_SPFLAG),
            "PROX_UPFLAG": bool(raw_value & _INTFLAG_PROX_UPFLAG),
        }
