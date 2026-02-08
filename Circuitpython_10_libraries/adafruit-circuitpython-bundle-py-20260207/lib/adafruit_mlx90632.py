# SPDX-FileCopyrightText: Copyright (c) 2025 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
`adafruit_mlx90632`
================================================================================

CircuitPython driver for the MLX90632 FIR Remote Thermal Temperature Sensor

* Author(s): Liz Clark

Implementation Notes
--------------------

**Hardware:**

* `Adafruit MLX90632 FIR Remote Thermal Temperature Sensor <https://www.adafruit.com/product/6403>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
"""

import struct
import time

from adafruit_bus_device import i2c_device
from micropython import const

try:
    import typing  # pylint: disable=unused-import

    from busio import I2C
except ImportError:
    pass

__version__ = "1.0.2"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_MLX90632.git"

# I2C Address
MLX90632_DEFAULT_ADDR = const(0x3A)

# EEPROM Registers
_REG_ID0 = const(0x2405)
_REG_ID1 = const(0x2406)
_REG_ID2 = const(0x2407)
_REG_EE_PRODUCT_CODE = const(0x2409)
_REG_EE_VERSION = const(0x240B)

# Calibration constant registers (32-bit values stored as LSW + MSW)
_REG_EE_P_R_LSW = const(0x240C)
_REG_EE_P_G_LSW = const(0x240E)
_REG_EE_P_T_LSW = const(0x2410)
_REG_EE_P_O_LSW = const(0x2412)
_REG_EE_AA_LSW = const(0x2414)
_REG_EE_AB_LSW = const(0x2416)
_REG_EE_BA_LSW = const(0x2418)
_REG_EE_BB_LSW = const(0x241A)
_REG_EE_CA_LSW = const(0x241C)
_REG_EE_CB_LSW = const(0x241E)
_REG_EE_DA_LSW = const(0x2420)
_REG_EE_DB_LSW = const(0x2422)
_REG_EE_EA_LSW = const(0x2424)
_REG_EE_EB_LSW = const(0x2426)
_REG_EE_FA_LSW = const(0x2428)
_REG_EE_FB_LSW = const(0x242A)
_REG_EE_GA_LSW = const(0x242C)

# 16-bit calibration constants
_REG_EE_GB = const(0x242E)
_REG_EE_KA = const(0x242F)
_REG_EE_KB = const(0x2430)
_REG_EE_HA = const(0x2481)
_REG_EE_HB = const(0x2482)

# Control and measurement registers
_REG_EE_MEAS_1 = const(0x24E1)
_REG_EE_MEAS_2 = const(0x24E2)
_REG_CONTROL = const(0x3001)
_REG_STATUS = const(0x3FFF)

# RAM registers
_REG_RAM_4 = const(0x4003)
_REG_RAM_5 = const(0x4004)
_REG_RAM_6 = const(0x4005)
_REG_RAM_7 = const(0x4006)
_REG_RAM_8 = const(0x4007)
_REG_RAM_9 = const(0x4008)
_REG_RAM_52 = const(0x4033)
_REG_RAM_53 = const(0x4034)
_REG_RAM_54 = const(0x4035)
_REG_RAM_55 = const(0x4036)
_REG_RAM_56 = const(0x4037)
_REG_RAM_57 = const(0x4038)
_REG_RAM_58 = const(0x4039)
_REG_RAM_59 = const(0x403A)

# Mode constants
MODE_HALT = const(0x00)
MODE_SLEEPING_STEP = const(0x01)
MODE_STEP = const(0x02)
MODE_CONTINUOUS = const(0x03)

# Measurement select constants
MEDICAL = const(0x00)
EXTENDED_RANGE = const(0x11)

# Refresh rate constants
REFRESH_0_5HZ = const(0)
REFRESH_1HZ = const(1)
REFRESH_2HZ = const(2)
REFRESH_4HZ = const(3)
REFRESH_8HZ = const(4)
REFRESH_16HZ = const(5)
REFRESH_32HZ = const(6)
REFRESH_64HZ = const(7)


class MLX90632:
    """Driver for the MLX90632 Far Infrared Temperature Sensor.

    :param ~busio.I2C i2c_bus: The I2C bus the MLX90632 is connected to.
    :param int address: The I2C device address. Default is 0x3A
    """

    def __init__(self, i2c_bus: I2C, address: int = MLX90632_DEFAULT_ADDR) -> None:
        self.i2c_device = i2c_device.I2CDevice(i2c_bus, address)

        # Initialize temperature history
        self._to0 = 25.0
        self._ta0 = 25.0

        # Check if device is responding
        if self.product_code in {0xFFFF, 0x0000}:
            raise RuntimeError("Failed to find MLX90632")

        # Load calibration constants
        self._load_calibrations()
        self.reset()
        self.mode = MODE_CONTINUOUS
        self.measurement_select = MEDICAL
        self.refresh_rate = REFRESH_2HZ
        self.reset_data_ready()

    def _read_register16(self, register: int) -> int:
        """Read a 16-bit register value."""
        # MLX90632 expects register address in big-endian format
        reg_bytes = struct.pack(">H", register)
        result = bytearray(2)
        with self.i2c_device as i2c:
            i2c.write_then_readinto(reg_bytes, result)
        return struct.unpack(">H", result)[0]

    def _read_register16_signed(self, register: int) -> int:
        """Read a 16-bit signed register value."""
        # MLX90632 expects register address in big-endian format
        reg_bytes = struct.pack(">H", register)
        result = bytearray(2)
        with self.i2c_device as i2c:
            i2c.write_then_readinto(reg_bytes, result)
        return struct.unpack(">h", result)[0]

    def _write_register16(self, register: int, value: int) -> None:
        """Write a 16-bit register value."""
        # MLX90632 expects register address and data in big-endian format
        data = struct.pack(">HH", register, value)
        with self.i2c_device as i2c:
            i2c.write(data)

    def _read_bits(self, register: int, num_bits: int, shift: int) -> int:
        """Read specific bits from a register."""
        value = self._read_register16(register)
        mask = ((1 << num_bits) - 1) << shift
        return (value & mask) >> shift

    def _write_bits(self, register: int, num_bits: int, shift: int, bits_value: int) -> None:
        """Write specific bits to a register."""
        value = self._read_register16(register)
        mask = ((1 << num_bits) - 1) << shift
        value = (value & ~mask) | ((bits_value << shift) & mask)
        self._write_register16(register, value)

    @property
    def product_id(self) -> int:
        """The 48-bit product ID."""
        id0 = self._read_register16(_REG_ID0)
        id1 = self._read_register16(_REG_ID1)
        id2 = self._read_register16(_REG_ID2)
        return (id2 << 32) | (id1 << 16) | id0

    @property
    def product_code(self) -> int:
        """The product code."""
        return self._read_register16(_REG_EE_PRODUCT_CODE)

    @property
    def eeprom_version(self) -> int:
        """The EEPROM version."""
        return self._read_register16(_REG_EE_VERSION)

    @property
    def mode(self) -> int:
        """The measurement mode.

        Can be one of:
        - MODE_HALT (0x00): Halt mode for EEPROM operations
        - MODE_SLEEPING_STEP (0x01): Sleeping step mode
        - MODE_STEP (0x02): Step mode
        - MODE_CONTINUOUS (0x03): Continuous mode
        """
        return self._read_bits(_REG_CONTROL, 2, 1)

    @mode.setter
    def mode(self, value: int) -> None:
        if value not in {MODE_HALT, MODE_SLEEPING_STEP, MODE_STEP, MODE_CONTINUOUS}:
            raise ValueError("Invalid mode")
        self._write_bits(_REG_CONTROL, 2, 1, value)

    @property
    def measurement_select(self) -> int:
        """The measurement type.

        Can be one of:
        - MEDICAL (0x00): Medical measurement
        - EXTENDED_RANGE (0x11): Extended range measurement
        """
        return self._read_bits(_REG_CONTROL, 5, 4)

    @measurement_select.setter
    def measurement_select(self, value: int) -> None:
        if value not in {MEDICAL, EXTENDED_RANGE}:
            raise ValueError("Invalid measurement select")
        self._write_bits(_REG_CONTROL, 5, 4, value)

    @property
    def refresh_rate(self) -> int:
        """The refresh rate.

        Can be one of:
        - REFRESH_0_5HZ (0): 0.5 Hz
        - REFRESH_1HZ (1): 1 Hz
        - REFRESH_2HZ (2): 2 Hz
        - REFRESH_4HZ (3): 4 Hz
        - REFRESH_8HZ (4): 8 Hz
        - REFRESH_16HZ (5): 16 Hz
        - REFRESH_32HZ (6): 32 Hz
        - REFRESH_64HZ (7): 64 Hz
        """
        return self._read_bits(_REG_EE_MEAS_1, 3, 8)

    @refresh_rate.setter
    def refresh_rate(self, value: int) -> None:
        if not 0 <= value <= 7:
            raise ValueError("Invalid refresh rate")
        self._write_bits(_REG_EE_MEAS_1, 3, 8, value)
        self._write_bits(_REG_EE_MEAS_2, 3, 8, value)

    @property
    def busy(self) -> bool:
        """True if device is busy with measurement."""
        return bool(self._read_bits(_REG_STATUS, 1, 10))

    @property
    def eeprom_busy(self) -> bool:
        """True if EEPROM is busy."""
        return bool(self._read_bits(_REG_STATUS, 1, 9))

    @property
    def cycle_position(self) -> int:
        """Current cycle position (0-31)."""
        return self._read_bits(_REG_STATUS, 5, 2)

    @property
    def data_ready(self) -> bool:
        """True if new measurement data is available."""
        return bool(self._read_bits(_REG_STATUS, 1, 0))

    def start_single_measurement(self) -> None:
        """Start a single measurement (SOC)."""
        self._write_bits(_REG_CONTROL, 1, 3, 1)

    def start_full_measurement(self) -> None:
        """Start a full measurement table (SOB)."""
        self._write_bits(_REG_CONTROL, 1, 11, 1)

    def reset_data_ready(self) -> None:
        """Reset the new data flag."""
        self._write_bits(_REG_STATUS, 1, 0, 0)

    def reset(self) -> None:
        """Reset the device using addressed reset command."""
        with self.i2c_device as i2c:
            i2c.write(bytes([0x30, 0x05, 0x00, 0x06]))
        time.sleep(0.001)  # Wait at least 150us

    def _read_32bit_register(self, lsw_addr: int) -> int:
        """Read a 32-bit value from consecutive registers."""
        lsw = self._read_register16(lsw_addr)
        msw = self._read_register16(lsw_addr + 1)
        return (msw << 16) | lsw

    def _load_calibrations(self) -> None:  # noqa: PLR0914
        """Load all calibration constants from EEPROM."""
        # Read 32-bit calibration constants
        ee_p_r = self._read_32bit_register(_REG_EE_P_R_LSW)
        ee_p_g = self._read_32bit_register(_REG_EE_P_G_LSW)
        ee_p_t = self._read_32bit_register(_REG_EE_P_T_LSW)
        ee_p_o = self._read_32bit_register(_REG_EE_P_O_LSW)
        ee_aa = self._read_32bit_register(_REG_EE_AA_LSW)
        ee_ab = self._read_32bit_register(_REG_EE_AB_LSW)
        ee_ba = self._read_32bit_register(_REG_EE_BA_LSW)
        ee_bb = self._read_32bit_register(_REG_EE_BB_LSW)
        ee_ca = self._read_32bit_register(_REG_EE_CA_LSW)
        ee_cb = self._read_32bit_register(_REG_EE_CB_LSW)
        ee_da = self._read_32bit_register(_REG_EE_DA_LSW)
        ee_db = self._read_32bit_register(_REG_EE_DB_LSW)
        ee_ea = self._read_32bit_register(_REG_EE_EA_LSW)
        ee_eb = self._read_32bit_register(_REG_EE_EB_LSW)
        ee_fa = self._read_32bit_register(_REG_EE_FA_LSW)
        ee_fb = self._read_32bit_register(_REG_EE_FB_LSW)
        ee_ga = self._read_32bit_register(_REG_EE_GA_LSW)

        # Convert to signed 32-bit
        def _to_signed32(val):
            if val & 0x80000000:
                return val - 0x100000000
            return val

        # Apply scaling factors from datasheet
        self._p_r = _to_signed32(ee_p_r) * pow(2, -8)
        self._p_g = _to_signed32(ee_p_g) * pow(2, -20)
        self._p_t = _to_signed32(ee_p_t) * pow(2, -44)
        self._p_o = _to_signed32(ee_p_o) * pow(2, -8)
        self._aa = _to_signed32(ee_aa) * pow(2, -16)
        self._ab = _to_signed32(ee_ab) * pow(2, -8)
        self._ba = _to_signed32(ee_ba) * pow(2, -16)
        self._bb = _to_signed32(ee_bb) * pow(2, -8)
        self._ca = _to_signed32(ee_ca) * pow(2, -16)
        self._cb = _to_signed32(ee_cb) * pow(2, -8)
        self._da = _to_signed32(ee_da) * pow(2, -16)
        self._db = _to_signed32(ee_db) * pow(2, -8)
        self._ea = _to_signed32(ee_ea) * pow(2, -16)
        self._eb = _to_signed32(ee_eb) * pow(2, -8)
        self._fa = _to_signed32(ee_fa) * pow(2, -46)
        self._fb = _to_signed32(ee_fb) * pow(2, -36)
        self._ga = _to_signed32(ee_ga) * pow(2, -36)

        # Read 16-bit calibration constants
        self._gb = self._read_register16_signed(_REG_EE_GB) * pow(2, -10)
        self._ka = self._read_register16_signed(_REG_EE_KA) * pow(2, -10)
        self._kb = self._read_register16_signed(_REG_EE_KB)  # No scaling
        self._ha = self._read_register16_signed(_REG_EE_HA) * pow(2, -14)
        self._hb = self._read_register16_signed(_REG_EE_HB) * pow(2, -10)

    @property
    def ambient_temperature(self) -> float:
        """The ambient temperature in degrees Celsius."""
        # Check measurement mode
        meas_mode = self.measurement_select

        if meas_mode == EXTENDED_RANGE:
            # Extended range mode: use RAM_54 and RAM_57
            ram_ambient = self._read_register16_signed(_REG_RAM_54)
            ram_ref = self._read_register16_signed(_REG_RAM_57)
        else:
            # Medical mode: use RAM_6 and RAM_9
            ram_ambient = self._read_register16_signed(_REG_RAM_6)
            ram_ref = self._read_register16_signed(_REG_RAM_9)

        # Pre-calculations for ambient temperature
        vrta = ram_ref + self._gb * (ram_ambient / 12.0)
        amb = (ram_ambient / 12.0) / vrta * pow(2, 19)

        # Calculate ambient temperature
        amb_diff = amb - self._p_r
        ambient_temp = self._p_o + (amb_diff / self._p_g) + self._p_t * (amb_diff * amb_diff)

        return ambient_temp

    @property
    def object_temperature(self) -> float:  # noqa: PLR0914
        """The object temperature in degrees Celsius."""
        # Check measurement mode
        meas_mode = self.measurement_select

        if meas_mode == EXTENDED_RANGE:
            # Extended range mode
            ram52 = self._read_register16_signed(_REG_RAM_52)
            ram53 = self._read_register16_signed(_REG_RAM_53)
            ram54 = self._read_register16_signed(_REG_RAM_54)
            ram55 = self._read_register16_signed(_REG_RAM_55)
            ram56 = self._read_register16_signed(_REG_RAM_56)
            ram57 = self._read_register16_signed(_REG_RAM_57)
            ram58 = self._read_register16_signed(_REG_RAM_58)
            ram59 = self._read_register16_signed(_REG_RAM_59)

            # Extended range S calculation
            s = (ram52 - ram53 - ram55 + ram56) / 2.0 + ram58 + ram59
            ram_ambient = ram54
            ram_ref = ram57
        else:
            # Medical mode
            cycle_pos = self.cycle_position

            ram4 = self._read_register16_signed(_REG_RAM_4)
            ram5 = self._read_register16_signed(_REG_RAM_5)
            ram6 = self._read_register16_signed(_REG_RAM_6)
            ram7 = self._read_register16_signed(_REG_RAM_7)
            ram8 = self._read_register16_signed(_REG_RAM_8)
            ram9 = self._read_register16_signed(_REG_RAM_9)

            # S calculation based on cycle position
            if cycle_pos == 2:
                s = (ram4 + ram5) / 2.0
            elif cycle_pos == 1:
                s = (ram7 + ram8) / 2.0
            else:
                # Invalid cycle position
                return float("nan")

            ram_ambient = ram6
            ram_ref = ram9

        # Pre-calculations for object temperature
        vrto = ram_ref + self._ka * (ram_ambient / 12.0)
        sto = ((s / 12.0) / vrto) * pow(2, 19)

        # Calculate AMB for TADUT
        vrta = ram_ref + self._gb * (ram_ambient / 12.0)
        amb = (ram_ambient / 12.0) / vrta * pow(2, 19)

        # Additional temperature calculations
        tadut = (amb - self._eb) / self._ea + 25.0
        tak = tadut + 273.15
        emissivity = 1.0

        # Use current TADUT as TODUT approximation for first iteration
        todut = tadut

        # Calculate final object temperature
        denominator = (
            emissivity
            * self._fa
            * self._ha
            * (1.0 + self._ga * (todut - self._to0) + self._fb * (tadut - self._ta0))
        )
        tak4 = pow(tak, 4)
        to_k4 = (sto / denominator) + tak4
        to = pow(to_k4, 0.25) - 273.15 - self._hb

        # Update temperature history for next calculation
        self._to0 = to
        self._ta0 = tadut

        return to
