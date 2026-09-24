# SPDX-FileCopyrightText: Copyright (c) 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_tsl2585`
================================================================================

CircuitPython driver for the Adafruit TSL2585 Digital UVA and Ambient Light Sensor - STEMMA QT


* Author(s): Liz Clark

Implementation Notes
--------------------

**Hardware:**

* `Adafruit TSL2585 Digital UVA and Ambient Light Sensor - STEMMA QT <https://www.adafruit.com/product/6524>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads
* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
* Adafruit's Register library: https://github.com/adafruit/Adafruit_CircuitPython_Register
"""

import time
from struct import unpack_from

from adafruit_bus_device.i2c_device import I2CDevice
from adafruit_register.i2c_bit import ROBit, RWBit
from adafruit_register.i2c_bits import RWBits
from adafruit_register.i2c_struct import ROUnaryStruct, UnaryStruct
from micropython import const

try:
    from typing import Tuple

    from busio import I2C
except ImportError:
    pass

__version__ = "1.0.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_TSL2585.git"

_DEFAULT_ADDR = const(0x39)
_DEVICE_ID = const(0x5C)

_UV_CALIB = const(0x08)
_ENABLE = const(0x80)
_MEAS_MODE0 = const(0x81)
_MEAS_MODE1 = const(0x82)
_SAMPLE_TIME0 = const(0x83)
_NR_SAMPLES0 = const(0x85)
_THRESH_LOW = const(0x8A)
_THRESH_HIGH = const(0x8D)
_AUX_ID = const(0x90)
_REV_ID = const(0x91)
_ID = const(0x92)
_STATUS = const(0x93)
_ALS_STATUS = const(0x94)
_STATUS2 = const(0x9D)
_CFG3 = const(0xA4)
_CFG4 = const(0xA5)
_CFG5 = const(0xA6)
_CFG8 = const(0xA9)
_CONTROL = const(0xB1)
_INTENAB = const(0xBA)
_SEQR_FD0 = const(0xCF)
_SEQR_ALS_FD1 = const(0xD0)
_SEQR_APERS = const(0xD1)
_SEQR_RES0 = const(0xD2)
_SEQR_RES1 = const(0xD3)
_GAIN_L = const(0xD4)
_GAIN_H = const(0xD5)
_SMUX_L = const(0xDC)
_SMUX_H = const(0xDD)
_STEP1_SMUX_H = const(0xDF)
_STEP2_SMUX_H = const(0xE1)
_CALIB_CFG0 = const(0xE4)
_CALIB_CFG2 = const(0xE6)
_GPIO_INT = const(0xF8)

_AINT = const(0x08)
_PHO_SAT = const(0x20)
_IR_SAT = const(0x10)
_UVA_SAT = const(0x08)

_FULL_COUNTS = const(0x00)
_MSB_POS_12 = const(0x0C)
_SEQ_OFF = const(0x00)
_SEQ_STEP0 = const(0x01)
_CALIB_EVERY_ROUND = const(0x01)
_REC_SMUX_L = const(0xE6)
_REC_SMUX_H = const(0x07)

_SAMPLE_TIME_250US = const(179)
_DEFAULT_SAMPLES = const(200)
_MAX_SAMPLE_TIME = const(2047)
_MAX_SAMPLES = const(2048)
_MAX_SMUX_H = const(0x0F)
_MAX_THRESH = const(0xFFFFFF)
_MAX_PERSIST = const(0x0F)

_MOD_CLOCK_US = 1.388889
_STARTUP_DELAY = 0.001
_RESET_DELAY = 0.001

PHOTOPIC = const(0)
"""Human eye response channel, modulator 0."""

IR = const(1)
"""Near infrared channel, modulator 1."""

UVA = const(2)
"""315nm to 400nm channel, modulator 2."""

GAIN_VALUES = (0.5, 1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096)
"""The selectable modulator gains, ordered by their register code."""

_TYPICAL_GAINS = (
    0.49713,
    1.0,
    1.96681,
    3.90448,
    7.97489,
    15.53952,
    31.0401,
    61.61692,
    123.85,
    239.0305,
    470.63,
    918.967,
    1741.331,
    3139.5975,
)


def _gain_code(gain: float) -> int:
    try:
        return GAIN_VALUES.index(gain)
    except ValueError:
        raise ValueError(f"Gain must be one of {GAIN_VALUES}") from None


class Measurement:
    """Three channel TSL2585 measurement.

    :param raw: Raw photopic, infrared and UVA full counts.
    :param float uva_calibrated: UVA counts corrected with the OTP factor.
    :param normalized: Typical 1x equivalent photopic, infrared and UVA counts.
    :param gains: The gains actually used for each channel.
    :param saturated: True for each channel whose result is invalid.
    """

    def __init__(
        self,
        raw: Tuple[int, int, int],
        uva_calibrated: float,
        normalized: Tuple[float, float, float],
        gains: Tuple[float, float, float],
        saturated: Tuple[bool, bool, bool],
    ) -> None:
        self.photopic, self.infrared, self.uva = raw
        self.uva_calibrated = uva_calibrated
        self.photopic_1x, self.infrared_1x, self.uva_1x = normalized
        self.photopic_gain, self.infrared_gain, self.uva_gain = gains
        self.photopic_saturated, self.infrared_saturated, self.uva_saturated = saturated

    def __repr__(self) -> str:
        return f"<Measurement photopic={self.photopic} infrared={self.infrared} uva={self.uva}>"


class TSL2585:  # noqa: PLR0904
    """Driver for the TSL2585 Digital UVA and Ambient Light Sensor.

    :param ~busio.I2C i2c: The I2C bus the TSL2585 is connected to.
    :param int address: The sensor I2C address. Default is 0x39.
    """

    device_id = ROUnaryStruct(_ID, "<B")
    """The device identification byte, which is 0x5C for the TSL2585."""

    revision_id = ROUnaryStruct(_REV_ID, "<B")
    """The silicon revision identification byte."""

    auxiliary_id = ROUnaryStruct(_AUX_ID, "<B")
    """The auxiliary identification byte."""

    uv_calibration = ROUnaryStruct(_UV_CALIB, "<B")
    """The factory UVA calibration byte, where 127 is nominal."""

    calibration_interval = UnaryStruct(_CALIB_CFG0, "<B")
    """How often the enabled calibration features, including AGC and auto-zero,
    run. 0 to disable scheduled calibration, 1 through 254 to run every
    nth sequencer round, or 255 to run once when measurements start."""

    data_ready = ROBit(_STATUS2, 6)
    """True when a new ALS measurement is available."""

    interrupt_active = ROBit(_STATUS, 3)
    """True while an ALS threshold interrupt is pending."""

    gpio_input = ROBit(_GPIO_INT, 0)
    """The logic level currently present on the VSYNC/GPIO pin."""

    _pon = RWBit(_ENABLE, 0)
    _aen = RWBit(_ENABLE, 1)
    _soft_reset = RWBit(_CONTROL, 3)
    _status_flags = UnaryStruct(_STATUS, "<B")
    _digital_saturation = ROBit(_STATUS2, 4)

    _mode0 = UnaryStruct(_MEAS_MODE0, "<B")
    _mode1 = UnaryStruct(_MEAS_MODE1, "<B")
    _sample_time = UnaryStruct(_SAMPLE_TIME0, "<H")
    _nr_samples = UnaryStruct(_NR_SAMPLES0, "<H")

    _photopic_gain_code = RWBits(4, _GAIN_L, 0)
    _ir_gain_code = RWBits(4, _GAIN_L, 4)
    _uva_gain_code = RWBits(4, _GAIN_H, 0)
    _max_gain_code = RWBits(4, _CFG8, 4)

    _seqr_fd0 = UnaryStruct(_SEQR_FD0, "<B")
    _seqr_als_fd1 = UnaryStruct(_SEQR_ALS_FD1, "<B")
    _seqr_apers = UnaryStruct(_SEQR_APERS, "<B")
    _seqr_res0 = UnaryStruct(_SEQR_RES0, "<B")
    _seqr_res1 = UnaryStruct(_SEQR_RES1, "<B")
    _smux_low = UnaryStruct(_SMUX_L, "<B")
    _smux_high = UnaryStruct(_SMUX_H, "<B")

    _calib_per_step = RWBit(_CFG4, 6)
    _sat_agc_steps = RWBits(4, _STEP1_SMUX_H, 4)
    _pred_agc_steps = RWBits(4, _STEP2_SMUX_H, 4)
    _agc_enable = RWBit(_CALIB_CFG2, 5)

    _low_thresh = RWBits(24, _THRESH_LOW, 0, register_width=3)
    _high_thresh = RWBits(24, _THRESH_HIGH, 0, register_width=3)
    _thresh_channel = RWBits(2, _CFG5, 4)
    _persistence = RWBits(4, _CFG5, 0)
    _aien = RWBit(_INTENAB, 3)
    _int_pinmap = RWBits(2, _CFG3, 4)
    _int_input_enable = RWBit(_GPIO_INT, 5)
    _int_invert = RWBit(_GPIO_INT, 6)

    _gpio_pinmap = RWBits(2, _CFG3, 0)
    _gpio_invert = RWBit(_GPIO_INT, 3)
    _gpio_input_enable = RWBit(_GPIO_INT, 2)
    _gpio_output = RWBit(_GPIO_INT, 1)

    def __init__(self, i2c: I2C, address: int = _DEFAULT_ADDR) -> None:
        self.i2c_device = I2CDevice(i2c, address)
        self._result_buf = bytearray(9)
        self._result_addr = bytearray((_ALS_STATUS,))
        self._uv_factor = 127

        if self.device_id != _DEVICE_ID:
            raise RuntimeError("Failed to find TSL2585 sensor")

        self.reset()

        self._uv_factor = self.uv_calibration
        self.enabled = False

        self.result_format(_FULL_COUNTS, _MSB_POS_12)
        self.sample_time = _SAMPLE_TIME_250US
        self.integration_samples = _DEFAULT_SAMPLES
        self.sequencer(_SEQ_OFF, _SEQ_STEP0, _SEQ_STEP0, _SEQ_OFF, _SEQ_OFF)
        self.calibration_interval = _CALIB_EVERY_ROUND
        self.max_gain = 4096
        self.photopic_gain = 128
        self.ir_gain = 128
        self.uva_gain = 128
        self.smux(_REC_SMUX_L, _REC_SMUX_H)
        self.agc_enabled = True
        self.enabled = True

    def _write_while_idle(self, *writes: Tuple[str, int]) -> None:
        was_enabled = self.enabled
        if was_enabled:
            self.enabled = False
        for name, value in writes:
            setattr(self, name, value)
        if was_enabled:
            self.enabled = True

    def reset(self) -> None:
        """Reset the sensor registers to their power-on values."""
        self._pon = True
        time.sleep(_STARTUP_DELAY)
        self._soft_reset = True
        time.sleep(_RESET_DELAY)

    @property
    def enabled(self) -> bool:
        """True while continuous ALS measurements are running."""
        return self._aen

    @enabled.setter
    def enabled(self, value: bool) -> None:
        if value:
            self._pon = True
            time.sleep(_STARTUP_DELAY)
            self._aen = True
        else:
            self._aen = False
            self._pon = False

    @property
    def _sample_period(self) -> float:
        return (self.sample_time + 1) * _MOD_CLOCK_US / 1000.0

    @property
    def integration_time(self) -> float:
        """The ALS integration time in milliseconds, from 0.25 through 90."""
        return self.integration_samples * self._sample_period

    @integration_time.setter
    def integration_time(self, value: float) -> None:
        if not 0.25 <= value <= 90.0:
            raise ValueError("Integration time must be 0.25ms to 90ms")
        samples = int(value / self._sample_period + 0.5)
        if not 1 <= samples <= _MAX_SAMPLES:
            raise ValueError("Integration time is out of range at this sample time")
        self.integration_samples = samples

    @property
    def sample_time(self) -> int:
        """The raw 11-bit modulator sample time value, from 0 through 2047."""
        return self._sample_time

    @sample_time.setter
    def sample_time(self, value: int) -> None:
        if not 0 <= value <= _MAX_SAMPLE_TIME:
            raise ValueError(f"Sample time must be 0 to {_MAX_SAMPLE_TIME}")
        self._write_while_idle(("_sample_time", value))

    @property
    def integration_samples(self) -> int:
        """The ALS integration length in samples, from 1 through 2048."""
        return self._nr_samples + 1

    @integration_samples.setter
    def integration_samples(self, value: int) -> None:
        if not 1 <= value <= _MAX_SAMPLES:
            raise ValueError(f"Sample count must be 1 to {_MAX_SAMPLES}")
        self._write_while_idle(("_nr_samples", value - 1))

    @property
    def photopic_gain(self) -> float:
        """The starting photopic gain, one of :data:`GAIN_VALUES`."""
        return GAIN_VALUES[self._photopic_gain_code]

    @photopic_gain.setter
    def photopic_gain(self, value: float) -> None:
        self._write_while_idle(("_photopic_gain_code", _gain_code(value)))

    @property
    def ir_gain(self) -> float:
        """The starting infrared gain, one of :data:`GAIN_VALUES`."""
        return GAIN_VALUES[self._ir_gain_code]

    @ir_gain.setter
    def ir_gain(self, value: float) -> None:
        self._write_while_idle(("_ir_gain_code", _gain_code(value)))

    @property
    def uva_gain(self) -> float:
        """The starting UVA gain, one of :data:`GAIN_VALUES`."""
        return GAIN_VALUES[self._uva_gain_code]

    @uva_gain.setter
    def uva_gain(self, value: float) -> None:
        self._write_while_idle(("_uva_gain_code", _gain_code(value)))

    @property
    def max_gain(self) -> float:
        """The largest gain available to every sequencer channel, one of :data:`GAIN_VALUES`"""
        return GAIN_VALUES[self._max_gain_code]

    @max_gain.setter
    def max_gain(self, value: float) -> None:
        self._write_while_idle(("_max_gain_code", _gain_code(value)))

    @property
    def agc_enabled(self) -> bool:
        """True when automatic gain control is enabled."""
        return self._agc_enable

    @agc_enabled.setter
    def agc_enabled(self, value: bool) -> None:
        was_enabled = self.enabled
        if was_enabled:
            self.enabled = False
        if value:
            self._calib_per_step = False
            self._sat_agc_steps = _SEQ_STEP0
            self._pred_agc_steps = _SEQ_STEP0
            self._agc_enable = True
        else:
            self._agc_enable = False
            self._sat_agc_steps = _SEQ_OFF
            self._pred_agc_steps = _SEQ_OFF
        if was_enabled:
            self.enabled = True

    @property
    def measurement(self) -> Measurement:
        """The latest coherent three channel :class:`Measurement`."""
        digital_saturation = self._digital_saturation

        with self.i2c_device as i2c:
            i2c.write_then_readinto(self._result_addr, self._result_buf)
        status, photopic, infrared, uva, gain01, gain2 = unpack_from("<BHHHBB", self._result_buf)

        photopic_code = gain01 & 0x0F
        infrared_code = gain01 >> 4
        uva_code = gain2 & 0x0F
        uva_calibrated = self.calibrate_uva(uva)

        return Measurement(
            (photopic, infrared, uva),
            uva_calibrated,
            (
                self._normalize_to_1x(photopic, photopic_code),
                self._normalize_to_1x(infrared, infrared_code),
                self._normalize_to_1x(uva_calibrated, uva_code),
            ),
            (
                GAIN_VALUES[photopic_code],
                GAIN_VALUES[infrared_code],
                GAIN_VALUES[uva_code],
            ),
            (
                digital_saturation or bool(status & _PHO_SAT),
                digital_saturation or bool(status & _IR_SAT),
                digital_saturation or bool(status & _UVA_SAT),
            ),
        )

    def calibrate_uva(self, raw_uva: int) -> float:
        """Apply the factory OTP correction to a raw UVA count.

        :param int raw_uva: Raw UVA full counts from the coherent result block.
        :return: The factory corrected UVA counts.
        """
        divisor = 1.0 - ((self._uv_factor - 127.0) / 100.0)
        if divisor <= 0.0:
            return float(raw_uva)
        return raw_uva / divisor

    def _normalize_to_1x(counts: float, gain_code: int) -> float:
        return counts / _TYPICAL_GAINS[gain_code]

    @property
    def low_threshold(self) -> int:
        """The inclusive low ALS interrupt threshold, from 0 through 0xFFFFFF."""
        return self._low_thresh

    @low_threshold.setter
    def low_threshold(self, value: int) -> None:
        if not 0 <= value <= _MAX_THRESH:
            raise ValueError("Threshold must be 0 to 0xFFFFFF")
        self._write_while_idle(("_low_thresh", value))

    @property
    def high_threshold(self) -> int:
        """The inclusive high ALS interrupt threshold, from 0 through 0xFFFFFF."""
        return self._high_thresh

    @high_threshold.setter
    def high_threshold(self, value: int) -> None:
        if not 0 <= value <= _MAX_THRESH:
            raise ValueError("Threshold must be 0 to 0xFFFFFF")
        self._write_while_idle(("_high_thresh", value))

    @property
    def interrupt_channel(self) -> int:
        """The channel compared against the interrupt thresholds.

        Must be one of :data:`PHOTOPIC`, :data:`IR` or :data:`UVA`.
        """
        return self._thresh_channel

    @interrupt_channel.setter
    def interrupt_channel(self, value: int) -> None:
        if value not in {PHOTOPIC, IR, UVA}:
            raise ValueError("Channel must be PHOTOPIC, IR or UVA")
        self._write_while_idle(("_thresh_channel", value))

    @property
    def interrupt_persistence(self) -> int:
        """Consecutive out of range results needed to raise an ALS interrupt.

        Ranges from 0 through 15.
        """
        return self._persistence

    @interrupt_persistence.setter
    def interrupt_persistence(self, value: int) -> None:
        if not 0 <= value <= _MAX_PERSIST:
            raise ValueError(f"Persistence must be 0 to {_MAX_PERSIST}")
        self._write_while_idle(("_persistence", value))

    @property
    def interrupt_enabled(self) -> bool:
        """True when ALS threshold events drive the open drain INT pin."""
        return self._aien

    @interrupt_enabled.setter
    def interrupt_enabled(self, value: bool) -> None:
        if not value:
            self._aien = False
            return
        self._int_pinmap = 0
        self._int_input_enable = False
        self._int_invert = False
        self._aien = True

    def clear_interrupt(self) -> None:
        """Clear the pending ALS threshold interrupt."""
        self._status_flags = _AINT

    @property
    def gpio_output(self) -> bool:
        """True when the open drain SYNC output is released.

        False means the output is pulled low.
        """
        return self._gpio_output

    @gpio_output.setter
    def gpio_output(self, value: bool) -> None:
        self._gpio_pinmap = 0
        self._gpio_invert = False
        self._gpio_input_enable = False
        self._gpio_output = bool(value)

    @property
    def gpio_input_enabled(self) -> bool:
        """True when the SYNC pin is configured as an input."""
        return self._gpio_input_enable

    @gpio_input_enabled.setter
    def gpio_input_enabled(self, value: bool) -> None:
        self._gpio_output = True
        self._gpio_input_enable = bool(value)

    def result_format(self, mode0: int, mode1: int) -> None:
        """Set the raw ALS result format and bit alignment.

        :param int mode0: The complete MEAS_MODE0 register value.
        :param int mode1: The complete MEAS_MODE1 register value.
        """
        self._write_while_idle(("_mode0", mode0), ("_mode1", mode1))

    def sequencer(
        self,
        fd_mod01: int,
        als_fd_mod2: int,
        apers_vsync: int,
        residual_mod01: int,
        residual_mod2_wait: int,
    ) -> None:
        """The raw ALS and flicker sequencer patterns.

        :param int fd_mod01: Flicker use by modulators 0 and 1, MEAS_SEQR_FD_0.
        :param int als_fd_mod2: ALS and modulator 2 flicker use,
            MEAS_SEQR_ALS_FD_1.
        :param int apers_vsync: Persistence and VSYNC wait,
            MEAS_SEQR_APERS_AND_VSYNC_WAIT.
        :param int residual_mod01: Residual use by modulators 0 and 1,
            MEAS_SEQR_RESIDUAL_0.
        :param int residual_mod2_wait: Residual use by modulator 2 plus timer
            wait, MEAS_SEQR_RESIDUAL_1_AND_WAIT.
        """
        self._write_while_idle(
            ("_seqr_fd0", fd_mod01),
            ("_seqr_als_fd1", als_fd_mod2),
            ("_seqr_apers", apers_vsync),
            ("_seqr_res0", residual_mod01),
            ("_seqr_res1", residual_mod2_wait),
        )

    def smux(self, smux_low: int, smux_high: int) -> None:
        """Set the raw step 0 photodiode to modulator routing.

        :param int smux_low: The complete MEAS_SEQR_STEP0_MOD_PHDX_SMUX_L value.
        :param int smux_high: The MEAS_SEQR_STEP0_MOD_PHDX_SMUX_H value, from 0
            through 0x0F.
        """
        if not 0 <= smux_high <= _MAX_SMUX_H:
            raise ValueError("SMUX high byte must be 0 to 0x0F")
        self._write_while_idle(("_smux_low", smux_low), ("_smux_high", smux_high))
