# SPDX-FileCopyrightText: Copyright (c) 2020 Bryan Siepert for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_tmp117`
================================================================================

CircuitPython library for the TI TMP117 Temperature sensor

* Author(s): Bryan Siepert, Ian Grant

parts based on SparkFun_TMP117_Arduino_Library by Madison Chodikov @ SparkFun Electronics:
https://github.com/sparkfunX/Qwiic_TMP117
https://github.com/sparkfun/SparkFun_TMP117_Arduino_Library

Serial number register information:
https://e2e.ti.com/support/sensors/f/1023/t/815716?TMP117-Reading-Serial-Number-from-EEPROM

Implementation Notes
--------------------

**Hardware:**

* `Adafruit TMP117 ±0.1°C High Accuracy I2C Temperature Sensor
  <https://www.adafruit.com/product/4821>`_ (Product ID: 4821)

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's Bus Device library:
  https://github.com/adafruit/Adafruit_CircuitPython_BusDevice

* Adafruit's Register library:
  https://github.com/adafruit/Adafruit_CircuitPython_Register

"""

import time
from collections import namedtuple

from adafruit_bus_device import i2c_device
from adafruit_register.i2c_bit import ROBit, RWBit
from adafruit_register.i2c_bits import ROBits, RWBits
from adafruit_register.i2c_struct import ROUnaryStruct, UnaryStruct
from micropython import const

try:
    from typing import Optional, Sequence, Tuple, Union

    from busio import I2C
except ImportError:
    pass

__version__ = "2.0.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_TMP117.git"


_I2C_ADDR = 0x48  # default I2C Address
_TEMP_RESULT = const(0x00)
_CONFIGURATION = const(0x01)
_T_HIGH_LIMIT = const(0x02)
_T_LOW_LIMIT = const(0x03)
_EEPROM_UL = const(0x04)
_EEPROM1 = const(0x05)
_EEPROM2 = const(0x06)
_TEMP_OFFSET = const(0x07)
_EEPROM3 = const(0x08)
_DEVICE_ID = const(0x0F)
# DID[11:0] is shared by both parts (0x117); bits[15:12] are a silicon-revision field.
_DEVICE_ID_DID = 0x117
_DEVICE_ID_MASK = 0x0FFF
_TMP117_RESOLUTION = 0.0078125  # Resolution of the device, found on (page 1 of datasheet)

_CONTINUOUS_CONVERSION_MODE = 0b00  # Continuous Conversion Mode
_ONE_SHOT_MODE = 0b11  # One Shot Conversion Mode
_SHUTDOWN_MODE = 0b01  # Shutdown Conversion Mode

# Conversion time 15.5 ms typical 17.5 ms max (DS Sec 6.5)
_MAX_SINGLE_CONVERSION_S = 0.0175
_CONVERSION_WAIT_MARGIN_S = 0.002  # small guard for scheduling jitter

AlertStatus = namedtuple("AlertStatus", ["high_alert", "low_alert"])


def _convert_to_integer(bytes_to_convert: bytearray) -> int:
    """Combine a big-endian byte sequence into a single integer.

    :param bytearray bytes_to_convert: bytes in most-significant-first order.
    :return: the combined unsigned integer value.
    :rtype: int

    """
    integer = 0
    for chunk in bytes_to_convert:
        integer <<= 8
        integer |= chunk
    return integer


class CV:
    """struct helper"""

    @classmethod
    def add_values(cls, value_tuples: Sequence[Tuple[str, int, Union[int, str], Optional[int]]]):
        """Add CV values to the class"""
        cls.string = {}
        cls.lsb = {}

        for value_tuple in value_tuples:
            name, value, string, lsb = value_tuple
            setattr(cls, name, value)
            cls.string[value] = string
            cls.lsb[value] = lsb

    @classmethod
    def is_valid(cls, value: int) -> bool:
        """Validate that a given value is a member"""
        return value in cls.string


class AverageCount(CV):
    """Options for `averaged_measurements`"""


AverageCount.add_values(
    (
        ("AVERAGE_1X", 0b00, 1, None),
        ("AVERAGE_8X", 0b01, 8, None),
        ("AVERAGE_32X", 0b10, 32, None),
        ("AVERAGE_64X", 0b11, 64, None),
    )
)


class MeasurementDelay(CV):
    """Options for `measurement_delay`"""


MeasurementDelay.add_values(
    (
        ("DELAY_0_0155_S", 0b000, 0.0155, None),
        ("DELAY_0_125_S", 0b001, 0.125, None),
        ("DELAY_0_250_S", 0b010, 0.250, None),
        ("DELAY_0_500_S", 0b011, 0.500, None),
        ("DELAY_1_S", 0b100, 1, None),
        ("DELAY_4_S", 0b101, 4, None),
        ("DELAY_8_S", 0b110, 8, None),
        ("DELAY_16_S", 0b111, 16, None),
    )
)


class AlertMode(CV):
    """Options for `alert_mode`. See `alert_mode` for more information."""


AlertMode.add_values((("WINDOW", 0, "Window", None), ("HYSTERESIS", 1, "Hysteresis", None)))


class MeasurementMode(CV):
    """Options for `measurement_mode`. See `measurement_mode` for more information."""


MeasurementMode.add_values(
    (
        ("CONTINUOUS", 0, "Continuous", None),
        ("ONE_SHOT", 3, "One shot", None),
        ("SHUTDOWN", 1, "Shutdown", None),
    )
)


class TMP117:
    """Library for the TI TMP117 high-accuracy temperature sensor"""

    _part_id = ROUnaryStruct(_DEVICE_ID, ">H")
    _raw_temperature = ROUnaryStruct(_TEMP_RESULT, ">h")
    _raw_high_limit = UnaryStruct(_T_HIGH_LIMIT, ">h")
    _raw_low_limit = UnaryStruct(_T_LOW_LIMIT, ">h")
    _raw_temperature_offset = UnaryStruct(_TEMP_OFFSET, ">h")

    # these three bits will clear on read in some configurations, so we read them together
    _alert_status_data_ready = ROBits(3, _CONFIGURATION, 13, 2, False)
    _eeprom_busy = ROBit(_CONFIGURATION, 12, 2, False)
    _mode = RWBits(2, _CONFIGURATION, 10, 2, False)

    _raw_measurement_delay = RWBits(3, _CONFIGURATION, 7, 2, False)
    _raw_averaged_measurements = RWBits(2, _CONFIGURATION, 5, 2, False)

    _raw_alert_mode = RWBit(_CONFIGURATION, 4, 2, False)  # T/nA bits in the datasheet
    _int_active_high = RWBit(_CONFIGURATION, 3, 2, False)
    _data_ready_int_en = RWBit(_CONFIGURATION, 2, 2, False)
    _soft_reset = RWBit(_CONFIGURATION, 1, 2, False)

    def __init__(self, i2c_bus: I2C, address: int = _I2C_ADDR):
        """Create a driver for a TMP117 or TMP119 on the given I2C bus.

        :param ~busio.I2C i2c_bus: the I2C bus the sensor is connected to.
        :param int address: the 7-bit I2C address (0x48-0x4B, default 0x48).
        :raises AttributeError: if no TMP117/TMP119-family device answers at ``address``.

        .. note::
            The device-ID register reports a 16-bit value whose **upper nibble is a
            silicon-revision field**, not a part number: TMP117 = ``0x0117``,
            TMP119 = ``0x2117``, both sharing DID[11:0] = ``0x117``. The check below
            matches that shared field so future silicon revisions are still accepted.
        """
        self.i2c_device = i2c_device.I2CDevice(i2c_bus, address)

        # Match on DID[11:0] == 0x117 instead of the full 16-bit value. The high nibble
        # is a revision field, so hard-coding {0x0117, 0x2117} rejects any future
        # revision of the same part. Failure-surface change: __init__ now raises in
        # strictly fewer cases (accepts more valid silicon); it never newly rejects a
        # part the old check accepted.
        if (self._part_id & _DEVICE_ID_MASK) != _DEVICE_ID_DID:
            raise AttributeError("Cannot find a TMP117 or TMP119")
        # currently set when `alert_status` is read, but not exposed
        self.reset()
        self.initialize()

    def reset(self) -> None:
        """Reset the sensor to its unconfigured power-on state.

        :return: ``None``
        :rtype: None

        """
        self._soft_reset = True
        # Wait out the Soft_Reset duration (2 ms Table 7-6) so a config write issued
        # immediately afterward is not lost.
        time.sleep(0.002)

    def initialize(self) -> None:
        """Configure the sensor with sensible defaults. `initialize` is primarily provided to be
        called after `reset`, however it can also be used to easily set the sensor to a known
        configuration

        :return: ``None``
        :rtype: None
        """
        # Datasheet specifies that reset will finish in 2ms however by default the first
        # conversion will be averaged 8x and take 1s
        # TODO: sleep depending on current averaging config
        self._set_mode_and_wait_for_measurement(_CONTINUOUS_CONVERSION_MODE)  # continuous
        time.sleep(1)

    @property
    def temperature(self) -> float:
        """The current measured temperature in degrees Celsius.

        :return: the most recent temperature in degrees Celsius.
        :rtype: float

        .. note::
            In continuous-conversion mode this returns the most recent sample and does
            not block. After a `reset` and before the first conversion completes, the
            sensor reports -256 degrees C.
        """

        return self._read_temperature()

    @property
    def temperature_offset(self) -> float:
        """User defined temperature offset to be added to measurements from `temperature`.

        The offset is applied inside the sensor (added after linearization) and is in the
        same -256 to +255.9921 degrees C range as the temperature result.

        :return: the configured offset in degrees Celsius.
        :rtype: float

        .. code-block::python

            import time
            import board
            import adafruit_tmp117

            i2c = board.I2C()  # uses board.SCL and board.SDA

            tmp117 = adafruit_tmp117.TMP117(i2c)

            print("Temperature without offset: %.2f degrees C" % tmp117.temperature)
            tmp117.temperature_offset = 10.0
            while True:
                print("Temperature w/ offset: %.2f degrees C" % tmp117.temperature)
                time.sleep(1)

        """
        return self._raw_temperature_offset * _TMP117_RESOLUTION

    @temperature_offset.setter
    def temperature_offset(self, value: float):
        if value > 255.9921 or value < -256:
            raise AttributeError("temperature_offset must be from -256 to 255.9921")
        scaled_offset = round(value / _TMP117_RESOLUTION)
        self._raw_temperature_offset = scaled_offset

    @property
    def high_limit(self) -> float:
        """The high temperature limit in degrees Celsius. When the measured temperature exceeds this
        value, the `high_alert` attribute of the `alert_status` property will be True. See the
        documentation for `alert_status` for more information.

        :return: the high limit in degrees Celsius.
        :rtype: float
        """

        return self._raw_high_limit * _TMP117_RESOLUTION

    @high_limit.setter
    def high_limit(self, value: float):
        if value > 255.9921 or value < -256:
            raise AttributeError("high_limit must be from -256 to 255.9921")
        scaled_limit = round(value / _TMP117_RESOLUTION)
        self._raw_high_limit = scaled_limit

    @property
    def low_limit(self) -> float:
        """The low  temperature limit in degrees Celsius. When the measured temperature goes below
        this value, the `low_alert` attribute of the `alert_status` property will be True. See the
        documentation for `alert_status` for more information.

        :return: the low limit in degrees Celsius.
        :rtype: float
        """

        return self._raw_low_limit * _TMP117_RESOLUTION

    @low_limit.setter
    def low_limit(self, value: float):
        if value > 255.9921 or value < -256:
            raise AttributeError("low_limit must be from -256 to 255.9921")
        scaled_limit = round(value / _TMP117_RESOLUTION)
        self._raw_low_limit = scaled_limit

    @property
    def alert_status(self) -> "AlertStatus":
        """The current triggered status of the high and low temperature alerts as a AlertStatus
        named tuple with attributes for the triggered status of each alert.

        :return: an `AlertStatus` namedtuple ``(high_alert, low_alert)`` of booleans.
        :rtype: AlertStatus

        .. warning::
            Reading this property reads the configuration register, which **clears the
            latched HIGH/LOW alert flags in window mode** (:py:const:`AlertMode.WINDOW`). Read it
            once per loop and reuse the result; reading it twice can miss an alert that
            the first read cleared. In hysteresis mode (:py:const:`AlertMode.HYSTERESIS`) the flag
            is not cleared by a register read.

        .. note::
            In hysteresis mode ``low_alert`` is always ``False`` (the low flag is
            disabled); only ``high_alert`` is meaningful.

        .. code-block :: python

            import board
            import adafruit_tmp117
            i2c = board.I2C()  # uses board.SCL and board.SDA

            tmp117 = adafruit_tmp117.TMP117(i2c)

            tmp117.high_limit = 25
            tmp117.low_limit = 10

            print("High limit", tmp117.high_limit)
            print("Low limit", tmp117.low_limit)

            # Try changing `alert_mode`  to see how it modifies the behavior of the alerts.
            # tmp117.alert_mode = AlertMode.WINDOW #default
            # tmp117.alert_mode = AlertMode.HYSTERESIS

            print("Alert mode:", AlertMode.string[tmp117.alert_mode])
            print("")
            print("")
            while True:
                print("Temperature: %.2f degrees C" % tmp117.temperature)
                alert_status = tmp117.alert_status
                print("High alert:", alert_status.high_alert)
                print("Low alert:", alert_status.low_alert)
                print("")
                time.sleep(1)

        """
        high_alert, low_alert, *_ = self._read_status()
        return AlertStatus(high_alert=high_alert, low_alert=low_alert)

    @property
    def averaged_measurements(self):
        """The number of measurements that are taken and averaged before updating the temperature
        measurement register. A larger number will reduce measurement noise but may also affect
        the rate at which measurements are updated, depending on the value of `measurement_delay`

        Note that each averaged measurement takes 15.5ms which means that larger numbers of averaged
        measurements may make the delay between new reported measurements to exceed the delay set
        by `measurement_delay`

        :return: the current `AverageCount` register code (number of averaged samples).
        :rtype: int

        .. code-block::python3

            import time
            import board
            from adafruit_tmp117 import TMP117, AverageCount

            i2c = board.I2C()  # uses board.SCL and board.SDA

            tmp117 = TMP117(i2c)

            # uncomment different options below to see how it affects the reported temperature
            # tmp117.averaged_measurements = AverageCount.AVERAGE_1X
            # tmp117.averaged_measurements = AverageCount.AVERAGE_8X
            # tmp117.averaged_measurements = AverageCount.AVERAGE_32X
            # tmp117.averaged_measurements = AverageCount.AVERAGE_64X

            print(
                "Number of averaged samples per measurement:",
                AverageCount.string[tmp117.averaged_measurements],
            )
            print("")

            while True:
                print("Temperature:", tmp117.temperature)
                time.sleep(0.1)

        """
        return self._raw_averaged_measurements

    @averaged_measurements.setter
    def averaged_measurements(self, value: int):
        if not AverageCount.is_valid(value):
            raise AttributeError("averaged_measurements must be an `AverageCount`")
        self._raw_averaged_measurements = value

    @property
    def measurement_mode(self):
        """Sets the measurement mode, specifying the behavior of how often measurements are taken.
                `measurement_mode` must be one of:

        +----------------------------------------+------------------------------------------------------+
        | Mode                                   | Behavior                                             |
        +========================================+======================================================+
        | :py:const:`MeasurementMode.CONTINUOUS` | Measurements are made at the interval determined by  |
        |                                        |                                                      |
        |                                        | `averaged_measurements` and `measurement_delay`.     |
        |                                        |                                                      |
        |                                        | `temperature` returns the most recent measurement    |
        +----------------------------------------+------------------------------------------------------+
        | :py:const:`MeasurementMode.ONE_SHOT`   | Take a single measurement with the current number of |
        |                                        |                                                      |
        |                                        | `averaged_measurements` and switch to                |
        |                                        | :py:const:`SHUTDOWN` when                            |
        |                                        |                                                      |
        |                                        | finished.                                            |
        |                                        |                                                      |
        |                                        |                                                      |
        |                                        | `temperature` will return the new measurement until  |
        |                                        |                                                      |
        |                                        | `measurement_mode` is set to :py:const:`CONTINUOUS`  |
        |                                        | or :py:const:`ONE_SHOT` is                           |
        |                                        |                                                      |
        |                                        | set again.                                           |
        +----------------------------------------+------------------------------------------------------+
        | :py:const:`MeasurementMode.SHUTDOWN`   | The sensor is put into a low power state and no new  |
        |                                        |                                                      |
        |                                        | measurements are taken.                              |
        |                                        |                                                      |
        |                                        | `temperature` will return the last measurement until |
        |                                        |                                                      |
        |                                        | a new `measurement_mode` is selected.                |
        +----------------------------------------+------------------------------------------------------+

        :return: the current `MeasurementMode` register code.
        :rtype: int

        """
        # pylint: enable=line-too-long
        return self._mode

    @measurement_mode.setter
    def measurement_mode(self, value: int):
        if not MeasurementMode.is_valid(value):
            raise AttributeError("measurement_mode must be a `MeasurementMode` ")

        self._set_mode_and_wait_for_measurement(value)

    @property
    def measurement_delay(self):
        """The minimum amount of time between measurements in seconds. Must be a
        `MeasurementDelay`. The specified amount may be exceeded depending on the
        current setting off `averaged_measurements` which determines the minimum
        time needed between reported measurements.

        :return: the current `MeasurementDelay` register code.
        :rtype: int

        .. code-block::python

            import time
            import board
            from adafruit_tmp117 import TMP117, AverageCount, MeasurementDelay

            i2c = board.I2C()  # uses board.SCL and board.SDA

            tmp117 = TMP117(i2c)

            # uncomment different options below to see how it affects the reported temperature

            # tmp117.measurement_delay = MeasurementDelay.DELAY_0_0155_S
            # tmp117.measurement_delay = MeasurementDelay.DELAY_0_125_S
            # tmp117.measurement_delay = MeasurementDelay.DELAY_0_250_S
            # tmp117.measurement_delay = MeasurementDelay.DELAY_0_500_S
            # tmp117.measurement_delay = MeasurementDelay.DELAY_1_S
            # tmp117.measurement_delay = MeasurementDelay.DELAY_4_S
            # tmp117.measurement_delay = MeasurementDelay.DELAY_8_S
            # tmp117.measurement_delay = MeasurementDelay.DELAY_16_S

            print("Minimum time between measurements:",
            MeasurementDelay.string[tmp117.measurement_delay], "seconds")

            print("")

            while True:
                print("Temperature:", tmp117.temperature)
                time.sleep(0.01)

        """

        return self._raw_measurement_delay

    @measurement_delay.setter
    def measurement_delay(self, value: int):
        if not MeasurementDelay.is_valid(value):
            raise AttributeError("measurement_delay must be a `MeasurementDelay`")
        self._raw_measurement_delay = value

    def take_single_measurement(self) -> float:
        """Perform a single measurement cycle respecting the value of `averaged_measurements`,
        returning the measurement once complete. Once finished the sensor is placed into a low power
        state until :py:meth:`take_single_measurement` or `temperature` are read.

        :return: the freshly measured temperature in degrees Celsius.
        :rtype: float

        **Note:** if `averaged_measurements` is set to a high value there will be a notable
        delay before the temperature measurement is returned while the sensor takes the required
        number of measurements
        """

        return self._set_mode_and_wait_for_measurement(_ONE_SHOT_MODE)  # one shot

    @property
    def alert_mode(self) -> int:
        """Sets the behavior of the `low_limit`, `high_limit`, and `alert_status` properties.

        When set to :py:const:`AlertMode.WINDOW`, the `high_limit` property will unset when the
        measured temperature goes below `high_limit`. Similarly `low_limit` will be True or False
        depending on if the measured temperature is below (`False`) or above(`True`) `low_limit`.

        When set to :py:const:`AlertMode.HYSTERESIS`, the `high_limit` property will be set to
        `False` when the measured temperature goes below `low_limit`. In this mode, the `low_limit`
        property of `alert_status` will not be set.

        The default is :py:const:`AlertMode.WINDOW`

        :return: the current `AlertMode` register code.
        :rtype: int
        """

        return self._raw_alert_mode

    @alert_mode.setter
    def alert_mode(self, value: int):
        if not AlertMode.is_valid(value):
            raise AttributeError("alert_mode must be an `AlertMode`")
        self._raw_alert_mode = value

    @property
    def serial_number(self) -> int:
        """A 48-bit, factory-set unique identifier for the device.

        :return: the 48-bit unique ID from EEPROM as an integer.
        :rtype: int

        .. note::
            This reads the factory NIST-traceability ID stored in EEPROM1-3. It is only
            meaningful if those EEPROM locations have not been reprogrammed for
            general-purpose use.
        """
        eeprom1_data = bytearray(2)
        eeprom2_data = bytearray(2)
        eeprom3_data = bytearray(2)
        # Fetch EEPROM registers
        with self.i2c_device as i2c:
            i2c.write_then_readinto(bytearray([_EEPROM1]), eeprom1_data)
            i2c.write_then_readinto(bytearray([_EEPROM2]), eeprom2_data)
            i2c.write_then_readinto(bytearray([_EEPROM3]), eeprom3_data)
        # Combine the 2-byte portions
        combined_id = bytearray(
            [
                eeprom1_data[0],
                eeprom1_data[1],
                eeprom2_data[0],
                eeprom2_data[1],
                eeprom3_data[0],
                eeprom3_data[1],
            ]
        )
        # Convert to an integer
        return _convert_to_integer(combined_id)

    def _set_mode_and_wait_for_measurement(self, mode: int) -> float:
        self._mode = mode
        # NOTE: in any one-shot / terminal mode (one that ends in SHUTDOWN), do NOT poll a
        # clear-on-read status flag to detect completion. Reading the config register
        # clears Data_Ready (clear-on-read), and one-shot drops back to SHUTDOWN the
        # instant its single conversion completes -- so if a poll read lands on the
        # conversion-complete edge and clears the just-set flag, it is never re-asserted
        # and the loop hangs forever (Adafruit_CircuitPython_TMP117 issue #10). Continuous
        # mode re-asserts Data_Ready every cycle, so a flag lost to the same race is
        # harmlessly re-set next conversion; a bounded poll stays correct there and gives
        # the lowest latency, so it is kept for continuous.
        if mode == _ONE_SHOT_MODE:
            # One-shot duration depends only on AVG (CONV is ignored in one-shot), so wait
            # the deterministic worst-case conversion time for the current averaging
            # setting, then read -- no Data_Ready involved, no race. (DS Sec 7.3.2 Averaging)
            samples = AverageCount.string[self._raw_averaged_measurements]
            time.sleep(samples * _MAX_SINGLE_CONVERSION_S + _CONVERSION_WAIT_MARGIN_S)
        elif mode == _CONTINUOUS_CONVERSION_MODE:
            # poll for data ready (safe and low-latency in continuous; see note above)
            while not self._read_status()[2]:
                time.sleep(0.001)
        # SHUTDOWN (or any non-converting mode): no new conversion is coming, so don't
        # wait for a Data_Ready that will never arrive -- return the last stored result.
        # (This also removes a latent hang when measurement_mode is set to SHUTDOWN.)
        return self._read_temperature()

    def _read_status(self) -> Tuple[bool, bool, bool]:
        # 3 bits: high_alert, low_alert, data_ready
        status_flags = self._alert_status_data_ready

        high_alert = 0b100 & status_flags > 0
        low_alert = 0b010 & status_flags > 0
        data_ready = 0b001 & status_flags > 0

        return (high_alert, low_alert, data_ready)

    def _read_temperature(self) -> float:
        return self._raw_temperature * _TMP117_RESOLUTION
