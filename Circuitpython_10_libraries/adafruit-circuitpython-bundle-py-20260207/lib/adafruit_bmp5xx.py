# SPDX-FileCopyrightText: Copyright (c) 2025 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_bmp5xx`
================================================================================

CircuitPython library for the BMP580 / BMP581 / BMP585 / etc barometric pressure sensors.


* Author(s): Tim Cocks

Implementation Notes
--------------------

**Hardware:**

`Purchase BMP580 from the Adafruit shop <http://www.adafruit.com/products/6411>`_
`Purchase BMP581 from the Adafruit shop <http://www.adafruit.com/products/6407>`_
`Purchase BMP585 from the Adafruit shop <http://www.adafruit.com/products/6413>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads


* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
* Adafruit's Register library: https://github.com/adafruit/Adafruit_CircuitPython_Register
"""

# imports
import time

from adafruit_bus_device.i2c_device import I2CDevice
from adafruit_bus_device.spi_device import SPIDevice  # noqa: PLC0415
from adafruit_register.register_accessor import I2CRegisterAccessor, SPIRegisterAccessor
from adafruit_register.register_bit import ROBit, RWBit
from adafruit_register.register_bits import ROBits, RWBits
from micropython import const

try:
    from typing import Optional, Union

    from busio import I2C, SPI
    from digitalio import DigitalInOut
except ImportError:
    pass

__version__ = "1.1.1"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_BMP5xx.git"

# I2C Address
ALTERNATE_ADAFRUIT_ADDR = const(0x46)
DEFAULT_ADAFRUIT_ADDR = const(0x47)

BMP5_OK = const(0x00)
BMP5XX_BEFORE_IIR_FILTER = const(0x00)
BMP5XX_AFTER_IIR_FILTER = const(0x01)

BMP5_SOFT_RESET_CMD = const(0xB6)

# Registers
BMP5_REG_CMD = const(0x7E)
BMP5_REG_ID = const(0x01)
BMP5_REG_STATUS = const(0x28)
BMP5_REG_INT_STATUS = const(0x27)
BMP5XX_REG_TEMP_DATA_XLSB = const(0x1D)
BMP5XX_REG_PRESS_DATA_XLSB = const(0x20)
BMP5XX_REG_OSR_CONFIG = const(0x36)
BMP5XX_REG_ODR_CONFIG = const(0x37)
BMP5XX_REG_DSP_IIR = const(0x31)
BMP5XX_REG_DSP_CONFIG = const(0x30)
BMP5XX_REG_INT_SOURCE = const(0x15)

# ODR settings
BMP5XX_ODR_240_HZ = const(0x00)
BMP5XX_ODR_218_5_HZ = const(0x01)
BMP5XX_ODR_199_1_HZ = const(0x02)
BMP5XX_ODR_179_2_HZ = const(0x03)
BMP5XX_ODR_160_HZ = const(0x04)
BMP5XX_ODR_149_3_HZ = const(0x05)
BMP5XX_ODR_140_HZ = const(0x06)
BMP5XX_ODR_129_8_HZ = const(0x07)
BMP5XX_ODR_120_HZ = const(0x08)
BMP5XX_ODR_110_1_HZ = const(0x09)
BMP5XX_ODR_100_2_HZ = const(0x0A)
BMP5XX_ODR_89_6_HZ = const(0x0B)
BMP5XX_ODR_80_HZ = const(0x0C)
BMP5XX_ODR_70_HZ = const(0x0D)
BMP5XX_ODR_60_HZ = const(0x0E)
BMP5XX_ODR_50_HZ = const(0x0F)
BMP5XX_ODR_45_HZ = const(0x10)
BMP5XX_ODR_40_HZ = const(0x11)
BMP5XX_ODR_35_HZ = const(0x12)
BMP5XX_ODR_30_HZ = const(0x13)
BMP5XX_ODR_25_HZ = const(0x14)
BMP5XX_ODR_20_HZ = const(0x15)
BMP5XX_ODR_15_HZ = const(0x16)
BMP5XX_ODR_10_HZ = const(0x17)
BMP5XX_ODR_05_HZ = const(0x18)
BMP5XX_ODR_04_HZ = const(0x19)
BMP5XX_ODR_03_HZ = const(0x1A)
BMP5XX_ODR_02_HZ = const(0x1B)
BMP5XX_ODR_01_HZ = const(0x1C)
BMP5XX_ODR_0_5_HZ = const(0x1D)
BMP5XX_ODR_0_250_HZ = const(0x1E)
BMP5XX_ODR_0_125_HZ = const(0x1F)

# Oversampling for temperature and pressure
BMP5XX_OVERSAMPLING_1X = const(0x00)
BMP5XX_OVERSAMPLING_2X = const(0x01)
BMP5XX_OVERSAMPLING_4X = const(0x02)
BMP5XX_OVERSAMPLING_8X = const(0x03)
BMP5XX_OVERSAMPLING_16X = const(0x04)
BMP5XX_OVERSAMPLING_32X = const(0x05)
BMP5XX_OVERSAMPLING_64X = const(0x06)
BMP5XX_OVERSAMPLING_128X = const(0x07)

# IIR filter for temperature and pressure
BMP5XX_IIR_FILTER_BYPASS = const(0x00)
BMP5XX_IIR_FILTER_COEFF_1 = const(0x01)
BMP5XX_IIR_FILTER_COEFF_3 = const(0x02)
BMP5XX_IIR_FILTER_COEFF_7 = const(0x03)
BMP5XX_IIR_FILTER_COEFF_15 = const(0x04)
BMP5XX_IIR_FILTER_COEFF_31 = const(0x05)
BMP5XX_IIR_FILTER_COEFF_63 = const(0x06)
BMP5XX_IIR_FILTER_COEFF_127 = const(0x07)

# Power modes
BMP5XX_POWERMODE_STANDBY = const(0x00)  # Standby powermode
BMP5XX_POWERMODE_NORMAL = const(0x01)  # Normal powermode
BMP5XX_POWERMODE_FORCED = const(0x02)  # Forced powermode
BMP5XX_POWERMODE_CONTINOUS = const(0x03)  # Continous powermode
BMP5XX_POWERMODE_DEEP_STANDBY = const(0x04)  # Deep standby powermode

BMP580_CHIP_ID = const(0x50)
BMP581_CHIP_ID = const(0x50)
BMP585_CHIP_ID = const(0x51)


class BMP5XX:
    """
    Bosche BMP5xx temperature and pressure sensor breakout CircuitPython driver.
    """

    chip_id: int = ROBits(8, BMP5_REG_ID, 0)

    # Status register bits
    status_nvm_ready: bool = ROBit(BMP5_REG_STATUS, 1)  # NVM ready
    """True if NVM is ready."""

    status_nvm_err: bool = ROBit(BMP5_REG_STATUS, 2)  # NVM error
    """True if NVM is has an error."""

    int_status_por: bool = ROBit(BMP5_REG_INT_STATUS, 4)  # INT_STATUS por
    """True if power on, or software reset complete."""

    data_ready_int_en: bool = RWBit(BMP5XX_REG_INT_SOURCE, 0)
    """Set to True to enable data_ready interrupt register."""

    fifo_full_int_en: bool = RWBit(BMP5XX_REG_INT_SOURCE, 1)
    """Set to True to enable FIFO full interrupt register."""

    fifo_threshold_int_en: bool = RWBit(BMP5XX_REG_INT_SOURCE, 2)
    """Set to True to enable FIFO threshold interrupt register."""

    pressure_oor_int_en: bool = RWBit(BMP5XX_REG_INT_SOURCE, 3)
    """Set to True to enable pressure OOR interrupt register."""

    data_ready: bool = ROBit(BMP5_REG_INT_STATUS, 0)
    """True if data is ready."""

    fifo_full_interrupt: bool = RWBit(BMP5_REG_INT_STATUS, 1)
    """True when FIFO is full."""

    fifo_threshold_interrupt: bool = RWBit(BMP5_REG_INT_STATUS, 2)
    """True when FIFO reached threshold."""

    pressure_oor_interrupt: bool = RWBit(BMP5_REG_INT_STATUS, 3)
    """True when pressure is OOR."""

    _temperature = ROBits(24, BMP5XX_REG_TEMP_DATA_XLSB, 0, 3, signed=True)
    _pressure = ROBits(24, BMP5XX_REG_PRESS_DATA_XLSB, 0, 3, signed=True)
    _mode = RWBits(2, BMP5XX_REG_ODR_CONFIG, 0)

    deep_disabled = RWBit(BMP5XX_REG_ODR_CONFIG, 7)
    """Deep standby disabled"""

    pressure_enabled = RWBit(BMP5XX_REG_OSR_CONFIG, 6)
    """Pressure readings enabled"""

    pressure_oversampling_rate = RWBits(3, BMP5XX_REG_OSR_CONFIG, 3)
    """Pressure oversampling rate. Must be one of the OVERSAMPLING constants."""

    temperature_oversampling_rate = RWBits(3, BMP5XX_REG_OSR_CONFIG, 0)
    """Temperature oversampling rate. Must be one of the OVERSAMPLING constants."""

    pressure_iir_filter = RWBits(3, BMP5XX_REG_DSP_IIR, 3)
    """Pressure IIR Filter. Must be one of the IIR_FILTER constants."""

    temperature_iir_filter = RWBits(3, BMP5XX_REG_DSP_IIR, 0)
    """Temperature IIR Filter. Must be one of the IIR_FILTER constants."""

    pressure_shadow_iir = RWBit(BMP5XX_REG_DSP_CONFIG, 5)
    """Pressure shadow IIR order. Must be BMP5XX_BEFORE_IIR_FILTER or BMP5XX_AFTER_IIR_FILTER"""

    temperature_shadow_iir = RWBit(BMP5XX_REG_DSP_CONFIG, 3)
    """Temperature shadow IIR order. Must be BMP5XX_BEFORE_IIR_FILTER or BMP5XX_AFTER_IIR_FILTER"""

    pressure_fifo_iir = RWBit(BMP5XX_REG_DSP_CONFIG, 6)
    """Pressure FIFO IIR order. Must be BMP5XX_BEFORE_IIR_FILTER or BMP5XX_AFTER_IIR_FILTER"""

    temperature_fifo_iir = RWBit(BMP5XX_REG_DSP_CONFIG, 4)
    """Temperature FIFO IIR order. Must be BMP5XX_BEFORE_IIR_FILTER or BMP5XX_AFTER_IIR_FILTER"""

    iir_flush_forced = RWBit(BMP5XX_REG_DSP_CONFIG, 2)
    """Use FORCED mode for IIR filter flush."""

    output_data_rate = RWBits(5, BMP5XX_REG_ODR_CONFIG, 2)
    """Output data rate. Must be one of the ODR constants."""

    command = RWBits(8, BMP5_REG_CMD, 0)  # command register
    """Command register"""

    @staticmethod
    def over_spi(spi: SPI, cs: DigitalInOut):
        """
        Initialize BMP5XX breakout over SPI bus.

        :param spi: busio.SPI instance to communicate over
        :param cs: DigitalInOut instance to use for chip select
        :return: Initialized BMP5XX object
        """
        spi_device = SPIDevice(spi, cs)
        return BMP5XX(spi_device)

    @staticmethod
    def over_i2c(i2c: I2C, address=DEFAULT_ADAFRUIT_ADDR):
        """
        Initialize BMP5XX breakout over I2C bus.

        :param i2c: busio.I2C instance to communicate over
        :param address: The I2C address to use. Defaults to DEFAULT_ADAFRUIT_ADDR
        :return: Initialized BMP5XX object
        """
        i2c_device = I2CDevice(i2c, address)
        return BMP5XX(i2c_device)

    def __init__(self, bus_device: Union[I2CDevice, SPIDevice]):
        if isinstance(bus_device, SPIDevice):
            self.register_accessor = SPIRegisterAccessor(bus_device)

        elif isinstance(bus_device, I2CDevice):
            self.register_accessor = I2CRegisterAccessor(bus_device)
        else:
            raise ValueError("bus_device must be an instance of I2CDevice or SPIDevice.")

        self.sea_level_pressure = 1013.25
        self.reset()
        time.sleep(0.0025)

        # Set default configuration
        self.temperature_oversampling_rate = BMP5XX_OVERSAMPLING_2X
        self.pressure_oversampling_rate = BMP5XX_OVERSAMPLING_16X
        self.output_data_rate = BMP5XX_ODR_50_HZ
        self.pressure_enabled = True

        self.temperature_iir_filter = BMP5XX_IIR_FILTER_COEFF_1
        self.pressure_iir_filter = BMP5XX_IIR_FILTER_COEFF_1
        self.temperature_shadow_iir = BMP5XX_AFTER_IIR_FILTER
        self.pressure_shadow_iir = BMP5XX_AFTER_IIR_FILTER
        self.iir_flush_forced = True

        self.mode = BMP5XX_POWERMODE_NORMAL
        self.data_ready_int_en = True
        self.fifo_full_int_en = False
        self.fifo_threshold_int_en = False
        self.pressure_oor_int_en = False

    @property
    def temperature(self) -> float:
        """Temperature in degress C."""
        raw_t = self._temperature
        return raw_t / 65536.0

    @property
    def pressure(self) -> float:
        """Pressure in hPa."""
        raw_p = self._pressure
        return raw_p / 64.0 / 100.0  # Convert raw_data->Pa->hPa

    @property
    def altitude(self) -> float:
        """The altitude in meters based on the currently set sea level pressure."""
        # see https://www.weather.gov/media/epz/wxcalc/pressureAltitude.pdf
        return 44307.7 * (1 - (self.pressure / self.sea_level_pressure) ** 0.190284)

    def reset(self) -> None:
        """Reset the BMP5xx device."""
        self.command = BMP5_SOFT_RESET_CMD
        time.sleep(0.012)
        _throwaway = self.chip_id

        if self.chip_id not in {BMP581_CHIP_ID, BMP585_CHIP_ID}:
            raise ValueError(f"CHIP_ID was incorrect")
        if not self.status_nvm_ready:
            raise ValueError("NVM not ready")
        if self.status_nvm_err:
            raise ValueError("NVM has an error")
        if not self.int_status_por:
            raise ValueError("POR Interrupt error")

    @property
    def mode(self) -> int:
        """Mode of operation. Must be one of the POWERMODE constants."""
        return self._mode

    @mode.setter
    def mode(self, new_mode: int) -> None:
        if new_mode not in {
            BMP5XX_POWERMODE_STANDBY,
            BMP5XX_POWERMODE_NORMAL,
            BMP5XX_POWERMODE_FORCED,
            BMP5XX_POWERMODE_CONTINOUS,
        }:
            raise ValueError("Invalid mode")

        old_mode = self._mode
        if old_mode != BMP5XX_POWERMODE_STANDBY:
            self.deep_disabled = True
            self._mode = BMP5XX_POWERMODE_STANDBY
            time.sleep(0.0025)

        if new_mode == BMP5XX_POWERMODE_STANDBY:
            # already set to standby mode above.
            return

        self.deep_disabled = True
        self._mode = new_mode


def BMP5XX_I2C(i2c: I2C, address: int = DEFAULT_ADAFRUIT_ADDR) -> BMP5XX:
    import warnings  # noqa: PLC0415, import outside top level

    warnings.warn(
        "Warning: BMP5XX_I2C class is deprecated and will be removed in a future version. "
        "User code should be updated to use BMP5XX.over_i2c()"
    )
    return BMP5XX.over_i2c(i2c, address)
