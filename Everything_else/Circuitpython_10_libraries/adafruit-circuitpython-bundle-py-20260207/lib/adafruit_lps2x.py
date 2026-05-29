# SPDX-FileCopyrightText: 2020 Bryan Siepert for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
`adafruit_lps2x`
================================================================================

Library for the ST LPS2X family of pressure sensors

* Author(s): Bryan Siepert

Implementation Notes
--------------------

**Hardware:**

* Adafruit `LPS25 Pressure SensorLPS25HB Breakout
  <https://www.adafruit.com/product/4530>`_ (Product ID: 4530)

* Adafruit `LPS22 Pressure Sensor LPS22HB Breakout
  <https://www.adafruit.com/product/4633>`_ (Product ID: 4633)

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
    https://circuitpython.org/downloads

* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice

* Adafruit's Register library: https://github.com/adafruit/Adafruit_CircuitPython_Register

"""

__version__ = "3.0.13"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_LPS2X.git"
from time import sleep

import adafruit_bus_device.i2c_device as i2cdevice
from adafruit_register.i2c_bit import RWBit
from adafruit_register.i2c_bits import ROBits, RWBits
from adafruit_register.i2c_struct import ROUnaryStruct
from micropython import const

try:
    from typing import Iterable, Optional, Tuple

    from busio import I2C
    from typing_extensions import Literal
except ImportError:
    pass

# _LPS2X_I2CADDR_DEFAULT = 0x5D # LPS2X default i2c address
# _LPS2X_WHOAMI = 0x0F          # Chip ID register
# _LPS2X_PRESS_OUT_XL =(# | 0x80) ///< | 0x80 to set auto increment on multi-byte read
# _LPS2X_TEMP_OUT_L =  (0x2B # 0x80) ///< | 0x80 to set auto increment on
_LPS2X_WHO_AM_I = const(0x0F)
_LPS2X_PRESS_OUT_XL = const(0x28 | 0x80)  # | 0x80 to set auto increment on multi-byte read
_LPS2X_TEMP_OUT_L = const(0x2B | 0x80)  # | 0x80 to set auto increment on multi-byte read

_LPS25_CTRL_REG1 = const(0x20)  # First control register. Includes BD & ODR
_LPS25_CTRL_REG2 = const(0x21)  # Second control register. Includes SW Reset
# _LPS25_CTRL_REG3 = 0x22 # Third control register. Includes interrupt polarity
# _LPS25_CTRL_REG4 = 0x23 # Fourth control register. Includes DRDY INT control
# _LPS25_INTERRUPT_CFG = 0x24 # Interrupt control register
# _LPS25_THS_P_L_REG = 0xB0   # Pressure threshold value for int


# _LPS22_THS_P_L_REG = 0x0C # Pressure threshold value for int
_LPS22_CTRL_REG1 = 0x10  # First control register. Includes BD & ODR
_LPS22_CTRL_REG2 = 0x11  # Second control register. Includes SW Reset
# _LPS22_CTRL_REG3 = 0x12 # Third control register. Includes interrupt polarity

_LPS2X_DEFAULT_ADDRESS = 0x5D
_LPS25HB_CHIP_ID = 0xBD
_LPS22HB_CHIP_ID = 0xB1  # LPS22 default device id from WHOAMI


class CV:
    """struct helper"""

    @classmethod
    def add_values(
        cls, value_tuples: Iterable[Tuple[str, int, Optional[float], Optional[float]]]
    ) -> None:
        """creates CV entries"""
        cls.string = {}
        cls.lsb = {}

        for value_tuple in value_tuples:
            name, value, string, lsb = value_tuple
            setattr(cls, name, value)
            cls.string[value] = string
            cls.lsb[value] = lsb

    @classmethod
    def is_valid(cls, value: int) -> bool:
        """Returns true if the given value is a member of the CV"""
        return value in cls.string


class Rate(CV):
    """Options for ``data_rate``

    +-----------------------------+------------------------------------------------+
    | Rate                        | Description                                    |
    +-----------------------------+------------------------------------------------+
    | ``Rate.LPS25_SHUTDOWN``     | Setting `data_rate` to ``Rate.LPS25_SHUTDOWN`` |
    |                             | stops measurements from being taken            |
    +-----------------------------+------------------------------------------------+
    | ``Rate.LPS25_RATE_1_HZ``    | 1 Hz                                           |
    +-----------------------------+------------------------------------------------+
    | ``Rate.LPS25_RATE_7_HZ``    | 7 Hz                                           |
    +-----------------------------+------------------------------------------------+
    | ``Rate.LPS25_RATE_12_5_HZ`` | 12.5 Hz                                        |
    +-----------------------------+------------------------------------------------+
    | ``Rate.LPS25_RATE_25_HZ``   | 25 Hz                                          |
    +-----------------------------+------------------------------------------------+
    | ``Rate.LPS22_SHUTDOWN``     | Setting `data_rate` to ``Rate.LPS22_SHUTDOWN`` |
    |                             | stops measurements from being taken            |
    +-----------------------------+------------------------------------------------+
    | ``Rate.LPS22_RATE_1_HZ``    | 1 Hz                                           |
    +-----------------------------+------------------------------------------------+
    | ``Rate.LPS22_RATE_10_HZ``   | 10 Hz                                          |
    +-----------------------------+------------------------------------------------+
    | ``Rate.LPS22_RATE_25_HZ``   | 25 Hz                                          |
    +-----------------------------+------------------------------------------------+
    | ``Rate.LPS22_RATE_50_HZ``   | 50 Hz                                          |
    +-----------------------------+------------------------------------------------+
    | ``Rate.LPS22_RATE_75_HZ``   | 75 Hz                                          |
    +-----------------------------+------------------------------------------------+


    """


class LPS2X:
    """Base class ST LPS2x family of pressure sensors

    :param ~busio.I2C i2c_bus: The I2C bus the sensor is connected to.
    :param int address: The I2C device address for the sensor.
                        Default is :const:`0x5d` but will accept :const:`0x5c` when
                        the ``SDO`` pin is connected to Ground.

    """

    _chip_id = ROUnaryStruct(_LPS2X_WHO_AM_I, "<B")
    _raw_temperature = ROUnaryStruct(_LPS2X_TEMP_OUT_L, "<h")
    _raw_pressure = ROBits(24, _LPS2X_PRESS_OUT_XL, 0, 3)

    def __init__(
        self, i2c_bus: I2C, address: int = _LPS2X_DEFAULT_ADDRESS, chip_id: int = -1
    ) -> None:
        if chip_id == -1:
            raise ValueError("Must set the chip_id argument")
        self.i2c_device = i2cdevice.I2CDevice(i2c_bus, address)
        if self._chip_id not in {chip_id}:
            raise RuntimeError(f"Failed to find LPS2X! Found chip ID {hex(self._chip_id)}")
        self.reset()
        self.initialize()
        sleep(0.010)  # delay 10ms for first reading

    def initialize(self) -> None:
        """Configure the sensor with the default settings. For use after calling :meth:`reset`"""
        raise NotImplementedError(
            "LPS2X Base class cannot be instantiated directly. Use LPS22 or LPS25 instead"
        )  # override in subclass

    def reset(self) -> None:
        """Reset the sensor, restoring all configuration registers to their defaults"""
        self._reset = True
        # wait for the reset to finish
        while self._reset:
            pass

    @property
    def pressure(self) -> float:
        """The current pressure measurement in hPa"""
        raw = self._raw_pressure

        if raw & (1 << 23) != 0:
            raw = raw - (1 << 24)
        return raw / 4096.0

    @property
    def temperature(self) -> float:
        """The current temperature measurement in degrees Celsius"""

        raw_temperature = self._raw_temperature
        return (
            raw_temperature / self._temp_scaling  # pylint:disable=no-member
        ) + self._temp_offset  # pylint:disable=no-member

    @property
    def data_rate(self) -> int:
        """The rate at which the sensor measures :attr:`pressure` and
        :attr:`temperature`. :attr:`data_rate` should be set to one of
        the values of :class:`adafruit_lps2x.Rate`"""
        return self._data_rate

    @data_rate.setter
    def data_rate(self, value: int) -> None:
        if not Rate.is_valid(value):
            raise AttributeError("data_rate must be a `Rate`")

        self._data_rate = value


class LPS25(LPS2X):
    """Library for the ST LPS25 pressure sensors

    :param ~busio.I2C i2c_bus: The I2C bus the LPS25HB is connected to.
    :param int address: The I2C device address. Default is :const:`0x5d` but will accept
        :const:`0x5c` when the ``SDO`` pin is connected to Ground.

    """

    enabled = RWBit(_LPS25_CTRL_REG1, 7)
    """Controls the power down state of the sensor. Setting to `False` will shut the sensor down"""
    _reset = RWBit(_LPS25_CTRL_REG2, 2)
    _data_rate = RWBits(3, _LPS25_CTRL_REG1, 4)

    def __init__(self, i2c_bus: I2C, address: int = _LPS2X_DEFAULT_ADDRESS) -> None:
        Rate.add_values(
            (
                ("LPS25_RATE_ONE_SHOT", 0, 0, None),
                ("LPS25_RATE_1_HZ", 1, 1, None),
                ("LPS25_RATE_7_HZ", 2, 7, None),
                ("LPS25_RATE_12_5_HZ", 3, 12.5, None),
                ("LPS25_RATE_25_HZ", 4, 25, None),
            )
        )
        super().__init__(i2c_bus, address, chip_id=_LPS25HB_CHIP_ID)

        self._temp_scaling = 480
        self._temp_offset = 42.5
        # self._inc_spi_flag = 0x40

    def initialize(self) -> None:
        """Configure the sensor with the default settings.
        For use after calling :func:`LPS2X.reset`
        """
        self.enabled = True
        self.data_rate = Rate.LPS25_RATE_25_HZ  # pylint:disable=no-member

    # void configureInterrupt(bool activelow, bool opendrain,
    #                       bool pres_high = false, bool pres_low = false);


class LPS22(LPS2X):
    """Library for the ST LPS22 pressure sensors

    :param ~busio.I2C i2c_bus: The I2C bus the LPS22HB is connected to.
    :param address: The I2C device address. Default is :const:`0x5d` but will accept
        :const:`0x5c` when the ``SDO`` pin is connected to Ground.

    """

    _reset = RWBit(_LPS22_CTRL_REG2, 2)
    _data_rate = RWBits(3, _LPS22_CTRL_REG1, 4)

    def __init__(self, i2c_bus: I2C, address: Literal[0x5C, 0x5D] = _LPS2X_DEFAULT_ADDRESS) -> None:
        # Only adding Class-appropriate rates
        Rate.add_values(
            (
                ("LPS22_RATE_ONE_SHOT", 0, 0, None),
                ("LPS22_RATE_1_HZ", 1, 1, None),
                ("LPS22_RATE_10_HZ", 2, 10, None),
                ("LPS22_RATE_25_HZ", 3, 25, None),
                ("LPS22_RATE_50_HZ", 4, 50, None),
                ("LPS22_RATE_75_HZ", 5, 75, None),
            )
        )

        super().__init__(i2c_bus, address, chip_id=_LPS22HB_CHIP_ID)
        self._temp_scaling = 100
        self._temp_offset = 0

    def initialize(self) -> None:
        """Configure the sensor with the default settings.
        For use after calling :func:`LPS2X.reset`
        """
        self.data_rate = Rate.LPS22_RATE_75_HZ  # pylint:disable=no-member

    # void configureInterrupt(bool activelow, bool opendrain, bool data_ready,
    #                         bool pres_high = false, bool pres_low = false,
    #                         bool fifo_full = false, bool fifo_watermark = false,
    #                         bool fifo_overflow = false);
