# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2025 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_spa06_003`
================================================================================

CircuitPython driver for SPA06-003 temperature and pressure sensor breakout.


* Author(s): Tim Cocks

Implementation Notes
--------------------

**Hardware:**

* `Adafruit SPA06-003 Temperature + Pressure Sensor - STEMMA QT <https://www.adafruit.com/product/6420>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
* Adafruit's Register library: https://github.com/adafruit/Adafruit_CircuitPython_Register
"""

import time

from adafruit_bus_device.i2c_device import I2CDevice
from adafruit_bus_device.spi_device import SPIDevice
from adafruit_register.register_accessor import I2CRegisterAccessor, SPIRegisterAccessor
from adafruit_register.register_bit import ROBit, RWBit
from adafruit_register.register_bits import ROBits, RWBits
from busio import I2C
from micropython import const

try:
    from typing import Union

    from busio import SPI
    from digitalio import DigitalInOut
except ImportError:
    pass

__version__ = "1.1.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_SPA06_003.git"

SPA06_003_DEFAULT_ADDR = const(0x77)
SPA06_003_ALTERNATE_ADDR = const(0x76)
SPA06_003_DEFAULT_SPIFREQ = const(1000000)  # 1 MHz

# Pressure data registers
SPA06_003_REG_PSR_B2 = const(0x00)  # Pressure data byte 2 (MSB)
SPA06_003_REG_PSR_B1 = const(0x01)  # Pressure data byte 1
SPA06_003_REG_PSR_B0 = const(0x02)  # Pressure data byte 0 (LSB)

# Temperature data registers
SPA06_003_REG_TMP_B2 = const(0x03)  # Temperature data byte 2 (MSB)
SPA06_003_REG_TMP_B1 = const(0x04)  # Temperature data byte 1
SPA06_003_REG_TMP_B0 = const(0x05)  # Temperature data byte 0 (LSB)

# Configuration registers
SPA06_003_REG_PRS_CFG = const(0x06)  # Pressure configuration register
SPA06_003_REG_TMP_CFG = const(0x07)  # Temperature configuration register
SPA06_003_REG_MEAS_CFG = const(0x08)  # Measurement configuration register
SPA06_003_REG_CFG_REG = const(0x09)  # General configuration register

# Status registers
SPA06_003_REG_INT_STS = const(0x0A)  # Interrupt status register
SPA06_003_REG_FIFO_STS = const(0x0B)  # FIFO status register

# Control registers
SPA06_003_REG_RESET = const(0x0C)  # Reset register
SPA06_003_REG_ID = const(0x0D)  # Chip ID register

# Calibration coefficient registers
SPA06_003_REG_COEF_C0 = const(0x10)  # Calibration coefficients C0 start address
SPA06_003_REG_COEF_C1 = const(0x11)  # Calibration coefficients C1 start address
SPA06_003_REG_COEF_C00 = const(0x13)  # Calibration coefficients C00 start address
SPA06_003_REG_COEF_C10 = const(0x15)  # Calibration coefficients C10 start address
SPA06_003_REG_COEF_C01 = const(0x18)  # Calibration coefficients C01 start address
SPA06_003_REG_COEF_C11 = const(0x1A)  # Calibration coefficients C11 start address
SPA06_003_REG_COEF_C20 = const(0x1C)  # Calibration coefficients C20 start address
SPA06_003_REG_COEF_C21 = const(0x1E)  # Calibration coefficients C21 start address
SPA06_003_REG_COEF_C30 = const(0x20)  # Calibration coefficients C30 start address
SPA06_003_REG_COEF_C31 = const(0x22)  # Calibration coefficients C31 start address
SPA06_003_REG_COEF_C40 = const(0x23)  # Calibration coefficients C40 start address

# Interrupt status flag definitions
SPA06_003_INT_FIFO_FULL = const(0x04)  # FIFO full flag
SPA06_003_INT_TMP_RDY = const(0x02)  # Temperature measurement ready flag
SPA06_003_INT_PRS_RDY = const(0x01)  # Pressure measurement ready flag

SPA06_003_CMD_RESET = const(0x09)

# Measurement rate options
SPA06_003_RATE_1 = const(0x00)  # 1 measurements per second
SPA06_003_RATE_2 = const(0x01)  # 2 measurements per second
SPA06_003_RATE_4 = const(0x02)  # 4 measurements per second
SPA06_003_RATE_8 = const(0x03)  # 8 measurements per second
SPA06_003_RATE_16 = const(0x04)  # 16 measurements per second
SPA06_003_RATE_32 = const(0x05)  # 32 measurements per second
SPA06_003_RATE_64 = const(0x06)  # 64 measurements per second
SPA06_003_RATE_128 = const(0x07)  # 128 measurements per second
SPA06_003_RATE_25_16 = const(0x08)  # 25/16 samples per second
SPA06_003_RATE_25_8 = const(0x09)  # 25/8 samples per second
SPA06_003_RATE_25_4 = const(0x0A)  # 25/4 samples per second
SPA06_003_RATE_25_2 = const(0x0B)  # 25/2 samples per second
SPA06_003_RATE_25 = const(0x0C)  # 25 samples per second
SPA06_003_RATE_50 = const(0x0D)  # 50 samples per second
SPA06_003_RATE_100 = const(0x0E)  # 100 samples per second
SPA06_003_RATE_200 = const(0x0F)  # 200 samples per second

# Oversampling rate options (shared by pressure and temperature)
SPA06_003_OVERSAMPLE_1 = const(0x00)  # Single
SPA06_003_OVERSAMPLE_2 = const(0x01)  # 2 times
SPA06_003_OVERSAMPLE_4 = const(0x02)  # 4 times
SPA06_003_OVERSAMPLE_8 = const(0x03)  # 8 times
SPA06_003_OVERSAMPLE_16 = const(0x04)  # 16 times
SPA06_003_OVERSAMPLE_32 = const(0x05)  # 32 times
SPA06_003_OVERSAMPLE_64 = const(0x06)  # 64 times
SPA06_003_OVERSAMPLE_128 = const(0x07)  # 128 times

# Measurement mode options
SPA06_003_MEAS_MODE_IDLE = const(0x00)  # Idle / Stop background measurement
SPA06_003_MEAS_MODE_PRESSURE = const(0x01)  # Pressure measurement (Command Mode)
SPA06_003_MEAS_MODE_TEMPERATURE = const(0x02)  # Temperature measurement (Command Mode)
SPA06_003_MEAS_MODE_CONTINUOUS_PRESSURE = const(
    0x05
)  # Continuous pressure measurement (Background Mode)
SPA06_003_MEAS_MODE_CONTINUOUS_TEMPERATURE = const(
    0x06
)  # Continuous temperature measurement (Background Mode)
SPA06_003_MEAS_MODE_CONTINUOUS_BOTH = const(
    0x07
)  # Continuous pressure and temperature measurement (Background Mode)

# Interrupt polarity options
SPA06_003_INT_ACTIVE_LOW = const(0x00)  # Interrupt active low
SPA06_003_INT_ACTIVE_HIGH = const(0x01)  # Interrupt active high

# Scaling factor lookup dictionary
SPA06_003_SCALING_FACTORS_LUT = {
    SPA06_003_OVERSAMPLE_1: 524288,  # Single
    SPA06_003_OVERSAMPLE_2: 1572864,  # 2x
    SPA06_003_OVERSAMPLE_4: 3670016,  # 4x
    SPA06_003_OVERSAMPLE_8: 7864320,  # 8x
    SPA06_003_OVERSAMPLE_16: 253952,  # 16x
    SPA06_003_OVERSAMPLE_32: 516096,  # 32x
    SPA06_003_OVERSAMPLE_64: 1040384,  # 64x
    SPA06_003_OVERSAMPLE_128: 2088960,  # 128x
}


class SPA06_003:
    """
    SPA06-003 temperature and pressure sensor breakout CircuitPython driver.

    :param bus_device: Instance of I2CDevice or SPIDevice

    .. _measurement-rate-options:

    Measurement Rate Options
    =========================

    .. list-table::
       :header-rows: 1
       :widths: 35 15 50

       * - Constant Name
         - Value
         - Description
       * - ``SPA06_003_RATE_1``
         - ``0x00``
         - 1 measurements per second
       * - ``SPA06_003_RATE_2``
         - ``0x01``
         - 2 measurements per second
       * - ``SPA06_003_RATE_4``
         - ``0x02``
         - 4 measurements per second
       * - ``SPA06_003_RATE_8``
         - ``0x03``
         - 8 measurements per second
       * - ``SPA06_003_RATE_16``
         - ``0x04``
         - 16 measurements per second
       * - ``SPA06_003_RATE_32``
         - ``0x05``
         - 32 measurements per second
       * - ``SPA06_003_RATE_64``
         - ``0x06``
         - 64 measurements per second
       * - ``SPA06_003_RATE_128``
         - ``0x07``
         - 128 measurements per second
       * - ``SPA06_003_RATE_25_16``
         - ``0x08``
         - 25/16 samples per second
       * - ``SPA06_003_RATE_25_8``
         - ``0x09``
         - 25/8 samples per second
       * - ``SPA06_003_RATE_25_4``
         - ``0x0A``
         - 25/4 samples per second
       * - ``SPA06_003_RATE_25_2``
         - ``0x0B``
         - 25/2 samples per second
       * - ``SPA06_003_RATE_25``
         - ``0x0C``
         - 25 samples per second
       * - ``SPA06_003_RATE_50``
         - ``0x0D``
         - 50 samples per second
       * - ``SPA06_003_RATE_100``
         - ``0x0E``
         - 100 samples per second
       * - ``SPA06_003_RATE_200``
         - ``0x0F``
         - 200 samples per second

    .. _oversampling-rate-options:

    Oversampling Rate Options
    =========================

    .. list-table::
       :header-rows: 1
       :widths: 35 15 50

       * - Constant Name
         - Value
         - Description
       * - ``SPA06_003_OVERSAMPLE_1``
         - ``0x00``
         - Single (no oversampling)
       * - ``SPA06_003_OVERSAMPLE_2``
         - ``0x01``
         - 2 times oversampling
       * - ``SPA06_003_OVERSAMPLE_4``
         - ``0x02``
         - 4 times oversampling
       * - ``SPA06_003_OVERSAMPLE_8``
         - ``0x03``
         - 8 times oversampling
       * - ``SPA06_003_OVERSAMPLE_16``
         - ``0x04``
         - 16 times oversampling
       * - ``SPA06_003_OVERSAMPLE_32``
         - ``0x05``
         - 32 times oversampling
       * - ``SPA06_003_OVERSAMPLE_64``
         - ``0x06``
         - 64 times oversampling
       * - ``SPA06_003_OVERSAMPLE_128``
         - ``0x07``
         - 128 times oversampling

    Interrupt Polarity Options
    ===========================

    .. list-table::
       :header-rows: 1
       :widths: 35 15 50

       * - Constant Name
         - Value
         - Description
       * - ``SPA06_003_INT_ACTIVE_LOW``
         - ``0x00``
         - Interrupt active low
       * - ``SPA06_003_INT_ACTIVE_HIGH``
         - ``0x01``
         - Interrupt active high

    """

    chip_id = ROBits(8, SPA06_003_REG_ID, 0)
    """Chip ID of the sensor"""

    soft_reset_cmd = RWBits(4, SPA06_003_REG_RESET, 0)
    """Soft reset command"""

    coeff_ready = ROBit(SPA06_003_REG_MEAS_CFG, 7)
    """Coefficient ready flag"""

    sensor_ready = ROBit(SPA06_003_REG_MEAS_CFG, 6)
    """Sensor ready flag"""

    _coeff_c0 = ROBits(12, SPA06_003_REG_COEF_C0, 4, register_width=2, lsb_first=False, signed=True)
    _coeff_c1 = ROBits(12, SPA06_003_REG_COEF_C1, 0, register_width=2, lsb_first=False, signed=True)
    _coeff_c00 = ROBits(
        20, SPA06_003_REG_COEF_C00, 4, register_width=3, lsb_first=False, signed=True
    )
    _coeff_c10 = ROBits(
        20, SPA06_003_REG_COEF_C10, 0, register_width=3, lsb_first=False, signed=True
    )
    _coeff_c01 = ROBits(
        16, SPA06_003_REG_COEF_C01, 0, register_width=2, lsb_first=False, signed=True
    )
    _coeff_c11 = ROBits(
        16, SPA06_003_REG_COEF_C11, 0, register_width=2, lsb_first=False, signed=True
    )
    _coeff_c20 = ROBits(
        16, SPA06_003_REG_COEF_C20, 0, register_width=2, lsb_first=False, signed=True
    )
    _coeff_c21 = ROBits(
        16, SPA06_003_REG_COEF_C21, 0, register_width=2, lsb_first=False, signed=True
    )
    _coeff_c30 = ROBits(
        16, SPA06_003_REG_COEF_C30, 0, register_width=2, lsb_first=False, signed=True
    )
    _coeff_c31 = ROBits(
        12, SPA06_003_REG_COEF_C31, 4, register_width=2, lsb_first=False, signed=True
    )
    _coeff_c40 = ROBits(
        12, SPA06_003_REG_COEF_C40, 0, register_width=2, lsb_first=False, signed=True
    )

    _pressure_oversampling = RWBits(3, SPA06_003_REG_PRS_CFG, 0)
    _pressure_shift_enabled = RWBit(SPA06_003_REG_CFG_REG, 2)

    pressure_measure_rate = RWBits(4, SPA06_003_REG_PRS_CFG, 4)
    """Pressure measurement rate.
    Must be one of the :ref:`RATE constants. <measurement-rate-options>`"""

    _temperature_oversampling = RWBits(3, SPA06_003_REG_TMP_CFG, 0)
    _temperature_shift_enabled = RWBit(SPA06_003_REG_CFG_REG, 3)

    temperature_measure_rate = RWBits(4, SPA06_003_REG_TMP_CFG, 4)
    """Temperature measurement rate.
    Must be one of the :ref:`RATE constants. <measurement-rate-options>`"""

    fifo_interrupt = RWBit(SPA06_003_REG_CFG_REG, 6)
    """FIFO interrupt enable flag"""

    temperature_interrupt = RWBit(SPA06_003_REG_CFG_REG, 5)
    """Temperature interrupt enable flag"""

    pressure_interrupt = RWBit(SPA06_003_REG_CFG_REG, 4)
    """Pressure interrupt enable flag"""

    measurement_mode = RWBits(3, SPA06_003_REG_MEAS_CFG, 0)
    """Measurement mode. Must be one of the MODE constants.

    Measurement Mode Options
    ========================

    .. list-table::
       :header-rows: 1
       :widths: 45 15 40

       * - Constant Name
         - Value
         - Description
       * - ``SPA06_003_MEAS_MODE_IDLE``
         - ``0x00``
         - Idle / Stop background measurement
       * - ``SPA06_003_MEAS_MODE_PRESSURE``
         - ``0x01``
         - Pressure measurement (Command Mode)
       * - ``SPA06_003_MEAS_MODE_TEMPERATURE``
         - ``0x02``
         - Temperature measurement (Command Mode)
       * - ``SPA06_003_MEAS_MODE_CONTINUOUS_PRESSURE``
         - ``0x05``
         - Continuous pressure measurement (Background Mode)
       * - ``SPA06_003_MEAS_MODE_CONTINUOUS_TEMPERATURE``
         - ``0x06``
         - Continuous temperature measurement (Background Mode)
       * - ``SPA06_003_MEAS_MODE_CONTINUOUS_BOTH``
         - ``0x07``
         - Continuous pressure and temperature measurement (Background Mode)"""

    temperature_data_ready = ROBit(SPA06_003_REG_MEAS_CFG, 5)
    """Temperature data ready flag"""

    pressure_data_ready = ROBit(SPA06_003_REG_MEAS_CFG, 4)
    """Pressure data ready flag"""

    _temperature_bits = ROBits(
        24, SPA06_003_REG_TMP_B2, 0, register_width=3, lsb_first=False, signed=True
    )
    _pressure_bits = ROBits(
        24, SPA06_003_REG_PSR_B2, 0, register_width=3, lsb_first=False, signed=True
    )

    @staticmethod
    def over_spi(spi: SPI, cs: DigitalInOut):
        """
        Initialize SPA06_003 breakout over SPI bus.

        :param spi: busio.SPI instance to communicate over
        :param cs: DigitalInOut instance to use for chip select
        :return: Initialized SPA06_003 object
        """
        spi_device = SPIDevice(spi, cs, phase=1, polarity=1)
        return SPA06_003(spi_device)

    @staticmethod
    def over_i2c(i2c: I2C, address=SPA06_003_DEFAULT_ADDR):
        """
        Initialize SPA06_003 breakout over I2C bus.

        :param i2c: busio.I2C instance to communicate over
        :param address: The I2C address to use. Defaults to SPA06_003_DEFAULT_ADDR
        :return: Initialized SPA06_003 object
        """
        i2c_device = I2CDevice(i2c, address)
        return SPA06_003(i2c_device)

    def __init__(self, bus_device: Union[I2CDevice, SPIDevice]):
        if isinstance(bus_device, SPIDevice):
            self.register_accessor = SPIRegisterAccessor(bus_device)

        elif isinstance(bus_device, I2CDevice):
            self.register_accessor = I2CRegisterAccessor(bus_device)

        else:
            raise ValueError("bus_device must be an instance of I2CDevice or SPIDevice.")

        if self.chip_id != 0x11:
            raise ValueError("Error Reading Chip ID. Device not found.")

        self.reset()

        while not self.sensor_ready or not self.coeff_ready:
            time.sleep(0.01)

        # Coefficient values do not change, so just read them once
        self.coeff_c0 = float(self._coeff_c0)
        self.coeff_c1 = float(self._coeff_c1)
        self.coeff_c00 = float(self._coeff_c00)
        self.coeff_c10 = float(self._coeff_c10)
        self.coeff_c01 = float(self._coeff_c01)
        self.coeff_c11 = float(self._coeff_c11)
        self.coeff_c20 = float(self._coeff_c20)
        self.coeff_c21 = float(self._coeff_c21)
        self.coeff_c30 = float(self._coeff_c30)
        self.coeff_c31 = float(self._coeff_c31)
        self.coeff_c40 = float(self._coeff_c40)

        # Configure for highest precision and sample rate
        # Set pressure to highest oversampling (128x) and highest rate (200 Hz)
        self.pressure_oversampling = SPA06_003_OVERSAMPLE_128
        self.pressure_measure_rate = SPA06_003_RATE_200

        # Set temperature to highest oversampling (128x) and highest rate (200 Hz)
        self.temperature_oversampling = SPA06_003_OVERSAMPLE_128
        self.temperature_measure_rate = SPA06_003_RATE_200

        # Enable interrupts for temperature and pressure ready
        self.fifo_interrupt = False
        self.pressure_interrupt = True
        self.temperature_interrupt = True

        # Set measurement mode to continuous both
        self.measurement_mode = SPA06_003_MEAS_MODE_CONTINUOUS_BOTH

    @property
    def temperature(self):
        """Temperature in Celsius"""
        temp_raw_signed = self._temperature_bits
        kT = SPA06_003_SCALING_FACTORS_LUT.get(self.temperature_oversampling, 524288)
        temp_raw_sc = float(temp_raw_signed) / kT
        temp_comp = self.coeff_c0 * 0.5 + self.coeff_c1 * temp_raw_sc

        return temp_comp

    @property
    def pressure(self):
        """Pressure in hPa"""
        # Get raw temp and pressure values
        temp_raw_signed = self._temperature_bits
        pres_raw_signed = self._pressure_bits

        # Get scaling factors
        kP = SPA06_003_SCALING_FACTORS_LUT[self.pressure_oversampling]
        kT = SPA06_003_SCALING_FACTORS_LUT[self.temperature_oversampling]

        # Calculate scaled measurement results
        pres_raw_sc = float(pres_raw_signed) / kP
        temp_raw_sc = float(temp_raw_signed) / kT

        # Calculate powers of Praw_sc for the compensation formula
        pres_raw_sc_2 = pres_raw_sc * pres_raw_sc
        pres_raw_sc_3 = pres_raw_sc_2 * pres_raw_sc
        pres_raw_sc_4 = pres_raw_sc_3 * pres_raw_sc

        # Calculate compensated pressure using the formula:
        # Pcomp = c00 + c10*Praw_sc + c20*Praw_sc^2 + c30*Praw_sc^3 + c40*Praw_sc^4 +
        #        Traw_sc*(c01 + c11*Praw_sc + c21*Praw_sc^2 + c31*Praw_sc^3)
        pres_comp = (
            self.coeff_c00
            + self.coeff_c10 * pres_raw_sc
            + self.coeff_c20 * pres_raw_sc_2
            + self.coeff_c30 * pres_raw_sc_3
            + self.coeff_c40 * pres_raw_sc_4
            + temp_raw_sc
            * (
                self.coeff_c01
                + self.coeff_c11 * pres_raw_sc
                + self.coeff_c21 * pres_raw_sc_2
                + self.coeff_c31 * pres_raw_sc_3
            )
        )

        # Convert from Pa to hPa (divide by 100)
        return pres_comp / 100.0

    @property
    def pressure_oversampling(self):
        """Pressure oversampling rate.
        Must be one of the :ref:`OVERSAMPLE constants. <oversampling-rate-options>`"""
        return self._pressure_oversampling

    @pressure_oversampling.setter
    def pressure_oversampling(self, new_value):
        if new_value not in SPA06_003_SCALING_FACTORS_LUT.keys():
            raise ValueError("Oversampling must be one of the OVERSAMPLING constants")

        self._pressure_oversampling = new_value
        self._pressure_shift_enabled = new_value > SPA06_003_OVERSAMPLE_8

    @property
    def temperature_oversampling(self):
        """Temperature oversampling rate.
        Must be one of the :ref:`OVERSAMPLE constants. <oversampling-rate-options>`"""
        return self._temperature_oversampling

    @temperature_oversampling.setter
    def temperature_oversampling(self, new_value):
        if new_value not in SPA06_003_SCALING_FACTORS_LUT.keys():
            raise ValueError("Oversampling must be one of the OVERSAMPLING constants")

        self._temperature_oversampling = new_value
        self._temperature_shift_enabled = new_value > SPA06_003_OVERSAMPLE_8

    def reset(self):
        """Performs soft reset on the sensor."""
        self.soft_reset_cmd = SPA06_003_CMD_RESET
        time.sleep(0.01)


def SPA06_003_I2C(i2c: I2C, address: int = SPA06_003_DEFAULT_ADDR):
    """
    SPA06_003_I2C Deprecated fallback driver for warning message.

    :param i2c: busio.I2C instance to communicate over
    :param address: I2C address to use. Defaults to SPA06_003_DEFAULT_ADDR
    """

    import warnings  # noqa: PLC0415, import outside top level

    warnings.warn(
        "Warning: SPA06_003_I2C class is deprecated and will be removed in a future version. "
        "User code should be updated to use SPA06_003.over_i2c()"
    )

    return SPA06_003.over_i2c(i2c, address)
