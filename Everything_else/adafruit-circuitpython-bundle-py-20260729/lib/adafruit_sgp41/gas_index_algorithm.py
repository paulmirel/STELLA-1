# SPDX-FileCopyrightText: Copyright (c) 2022 Sensirion AG
# SPDX-FileCopyrightText: Copyright (c) 2026 Adafruit Industries
#
# SPDX-License-Identifier: BSD-3-Clause
"""
`gas_index_algorithm`
================================================================================

Pure-Python port of Sensirion's Gas Index Algorithm (fixpoint reference) used by
the SGP41 to convert raw VOC and NOx tick values into the 0..500 gas index
signals described in the SGP41 datasheet.

Ported from:
https://github.com/Sensirion/gas-index-algorithm (v3.2.0, BSD-3-Clause).

* Author(s): Sensirion AG (original C), Adafruit Industries (Python port)
"""

try:
    from typing import Tuple
except ImportError:
    pass

_LIBRARY_VERSION_NAME = "3.2.0"

ALGORITHM_TYPE_VOC = 0
ALGORITHM_TYPE_NOX = 1

_SAMPLING_INTERVAL = 1.0
_INITIAL_BLACKOUT = 45.0
_INDEX_GAIN = 230.0
_SRAW_STD_INITIAL = 50.0
_SRAW_STD_BONUS_VOC = 220.0
_SRAW_STD_NOX = 2000.0
_TAU_MEAN_HOURS = 12.0
_TAU_VARIANCE_HOURS = 12.0
_TAU_INITIAL_MEAN_VOC = 20.0
_TAU_INITIAL_MEAN_NOX = 1200.0
_INIT_DURATION_MEAN_VOC = 3600.0 * 0.75
_INIT_DURATION_MEAN_NOX = 3600.0 * 4.75
_INIT_TRANSITION_MEAN = 0.01
_TAU_INITIAL_VARIANCE = 2500.0
_INIT_DURATION_VARIANCE_VOC = 3600.0 * 1.45
_INIT_DURATION_VARIANCE_NOX = 3600.0 * 5.70
_INIT_TRANSITION_VARIANCE = 0.01
_GATING_THRESHOLD_VOC = 340.0
_GATING_THRESHOLD_NOX = 30.0
_GATING_THRESHOLD_INITIAL = 510.0
_GATING_THRESHOLD_TRANSITION = 0.09
_GATING_VOC_MAX_DURATION_MINUTES = 60.0 * 3.0
_GATING_NOX_MAX_DURATION_MINUTES = 60.0 * 12.0
_GATING_MAX_RATIO = 0.3
_SIGMOID_L = 500.0
_SIGMOID_K_VOC = -0.0065
_SIGMOID_X0_VOC = 213.0
_SIGMOID_K_NOX = -0.0101
_SIGMOID_X0_NOX = 614.0
_VOC_INDEX_OFFSET_DEFAULT = 100.0
_NOX_INDEX_OFFSET_DEFAULT = 1.0
_LP_TAU_FAST = 20.0
_LP_TAU_SLOW = 500.0
_LP_ALPHA = -0.2
_VOC_SRAW_MINIMUM = 20000
_NOX_SRAW_MINIMUM = 10000
_PERSISTENCE_UPTIME_GAMMA = 3.0 * 3600.0
_MEAN_VARIANCE_ESTIMATOR__GAMMA_SCALING = 64.0
_MEAN_VARIANCE_ESTIMATOR__ADDITIONAL_GAMMA_MEAN_SCALING = 8.0
_MEAN_VARIANCE_ESTIMATOR__FIX16_MAX = 32767.0

_FIX16_MAXIMUM = 0x7FFFFFFF
_FIX16_MINIMUM = -0x80000000
_FIX16_OVERFLOW = -0x80000000
_FIX16_ONE = 0x00010000


def _f16(x: float) -> int:
    """Convert float to Q16.16 fixed-point int (matches the C F16 macro)."""
    if x >= 0:
        v = int(x * 65536.0 + 0.5)
    else:
        v = int(x * 65536.0 - 0.5)
    # clamp into int32 range just in case
    if v > _FIX16_MAXIMUM:
        v = _FIX16_MAXIMUM
    elif v < _FIX16_MINIMUM:
        v = _FIX16_MINIMUM
    return v


def _fix16_from_int(a: int) -> int:
    return (a * _FIX16_ONE) & 0xFFFFFFFF if a >= 0 else _to_int32((a * _FIX16_ONE) & 0xFFFFFFFF)


def _to_int32(u: int) -> int:
    u &= 0xFFFFFFFF
    return u if u < 0x80000000 else u - 0x100000000


def _fix16_cast_to_int(a: int) -> int:
    if a >= 0:
        return a >> 16
    return -((-a) >> 16)


def _fix16_mul(a: int, b: int) -> int:
    """Bit-exact port of libfixmath fix16_mul with FIXMATH_NO_OVERFLOW undefined."""
    neg = (a < 0) != (b < 0)
    ua = a if a >= 0 else -a
    ub = b if b >= 0 else -b
    prod = ua * ub  # up to 64-bit unsigned
    # overflow: upper 17 bits of 64-bit product must be zero
    if (prod >> 47) != 0:
        return _FIX16_OVERFLOW
    # rounding: + 0.5 in Q16.16
    prod += 0x8000
    result = (prod >> 16) & 0xFFFFFFFF
    if neg:
        result = (-result) & 0xFFFFFFFF
    return _to_int32(result)


def _fix16_div(a: int, b: int) -> int:
    """Bit-exact port of libfixmath fix16_div."""
    if b == 0:
        return _FIX16_MINIMUM
    remainder = a if a >= 0 else -a
    divider = b if b >= 0 else -b
    quotient = 0
    bit = 0x10000
    while divider < remainder:
        divider <<= 1
        bit <<= 1
    if not bit:
        return _FIX16_OVERFLOW
    if divider & 0x80000000:
        if remainder >= divider:
            quotient |= bit
            remainder -= divider
        divider >>= 1
        bit >>= 1
    while bit and remainder:
        if remainder >= divider:
            quotient |= bit
            remainder -= divider
        remainder <<= 1
        bit >>= 1
    # rounding
    if remainder >= divider:
        quotient += 1
    result = quotient
    if (a < 0) != (b < 0):
        if result == 0x80000000:
            return _FIX16_OVERFLOW
        result = -result
    return _to_int32(result & 0xFFFFFFFF)


def _fix16_sqrt(x: int) -> int:
    """Bit-exact port of libfixmath fix16_sqrt (assumes x >= 0)."""
    num = x & 0xFFFFFFFF
    result = 0
    bit = 1 << 30
    while bit > num:
        bit >>= 2
    for n in range(2):
        while bit:
            if num >= result + bit:
                num -= result + bit
                result = (result >> 1) + bit
            else:
                result >>= 1
            bit >>= 2
        if n == 0:
            if num > 65535:
                num -= result
                num = ((num << 16) - 0x8000) & 0xFFFFFFFF
                result = ((result << 16) + 0x8000) & 0xFFFFFFFF
            else:
                num = (num << 16) & 0xFFFFFFFF
                result = (result << 16) & 0xFFFFFFFF
            bit = 1 << 14
    if num > result:
        result += 1
    return _to_int32(result & 0xFFFFFFFF)


_EXP_POS = [_f16(2.7182818), _f16(1.1331485), _f16(1.0157477), _f16(1.0019550)]
_EXP_NEG = [_f16(0.3678794), _f16(0.8824969), _f16(0.9844964), _f16(0.9980488)]


def _fix16_exp(x: int) -> int:
    if x >= _f16(10.3972):
        return _FIX16_MAXIMUM
    if x <= _f16(-11.7835):
        return 0
    if x < 0:
        x = -x
        values = _EXP_NEG
    else:
        values = _EXP_POS
    res = _FIX16_ONE
    arg = _FIX16_ONE
    for i in range(4):
        while x >= arg:
            res = _fix16_mul(res, values[i])
            x -= arg
        arg >>= 3
    return res


class GasIndexAlgorithm:
    """
    Gas Index Algorithm for Sensirion SGP4x sensors.

    :param int algorithm_type: ``ALGORITHM_TYPE_VOC`` (0, default) for the VOC
        index or ``ALGORITHM_TYPE_NOX`` (1) for the NOx index.

    Call :meth:`process` exactly once per second with the raw tick value from
    the sensor. During the first 45 seconds the algorithm returns ``0`` while
    it warms up; after that it returns the gas index in the range ``1..500``.
    """

    ALGORITHM_TYPE_VOC = ALGORITHM_TYPE_VOC
    ALGORITHM_TYPE_NOX = ALGORITHM_TYPE_NOX

    def __init__(self, algorithm_type: int = ALGORITHM_TYPE_VOC) -> None:
        # Top-level parameters
        self._algorithm_type = algorithm_type
        self._index_offset = 0
        self._sraw_minimum = 0
        self._gating_max_duration_minutes = 0
        self._init_duration_mean = 0
        self._init_duration_variance = 0
        self._gating_threshold = 0
        self._index_gain = 0
        self._tau_mean_hours = 0
        self._tau_variance_hours = 0
        self._sraw_std_initial = 0
        self._uptime = 0
        self._sraw = 0
        self._gas_index = 0
        # Mean / variance estimator state
        self._mve_initialized = False
        self._mve_mean = 0
        self._mve_sraw_offset = 0
        self._mve_std = 0
        self._mve_gamma_mean = 0
        self._mve_gamma_variance = 0
        self._mve_gamma_initial_mean = 0
        self._mve_gamma_initial_variance = 0
        self._mve_out_gamma_mean = 0
        self._mve_out_gamma_variance = 0
        self._mve_uptime_gamma = 0
        self._mve_uptime_gating = 0
        self._mve_gating_duration_minutes = 0
        self._mve_sigmoid_k = 0
        self._mve_sigmoid_x0 = 0
        # MOX model
        self._mox_sraw_std = 0
        self._mox_sraw_mean = 0
        # Sigmoid scaled
        self._sig_k = 0
        self._sig_x0 = 0
        self._sig_offset_default = 0
        # Adaptive lowpass
        self._lp_a1 = 0
        self._lp_a2 = 0
        self._lp_initialized = False
        self._lp_x1 = 0
        self._lp_x2 = 0
        self._lp_x3 = 0

        self._init(algorithm_type)

    @staticmethod
    def get_version() -> str:
        return _LIBRARY_VERSION_NAME

    def _init(self, algorithm_type: int) -> None:
        self._algorithm_type = algorithm_type
        if algorithm_type == ALGORITHM_TYPE_NOX:
            self._index_offset = _f16(_NOX_INDEX_OFFSET_DEFAULT)
            self._sraw_minimum = _NOX_SRAW_MINIMUM
            self._gating_max_duration_minutes = _f16(_GATING_NOX_MAX_DURATION_MINUTES)
            self._init_duration_mean = _f16(_INIT_DURATION_MEAN_NOX)
            self._init_duration_variance = _f16(_INIT_DURATION_VARIANCE_NOX)
            self._gating_threshold = _f16(_GATING_THRESHOLD_NOX)
        else:
            self._index_offset = _f16(_VOC_INDEX_OFFSET_DEFAULT)
            self._sraw_minimum = _VOC_SRAW_MINIMUM
            self._gating_max_duration_minutes = _f16(_GATING_VOC_MAX_DURATION_MINUTES)
            self._init_duration_mean = _f16(_INIT_DURATION_MEAN_VOC)
            self._init_duration_variance = _f16(_INIT_DURATION_VARIANCE_VOC)
            self._gating_threshold = _f16(_GATING_THRESHOLD_VOC)
        self._index_gain = _f16(_INDEX_GAIN)
        self._tau_mean_hours = _f16(_TAU_MEAN_HOURS)
        self._tau_variance_hours = _f16(_TAU_VARIANCE_HOURS)
        self._sraw_std_initial = _f16(_SRAW_STD_INITIAL)
        self.reset()

    def reset(self) -> None:
        """Reset internal state; tuning parameters are preserved."""
        self._uptime = _f16(0.0)
        self._sraw = _f16(0.0)
        self._gas_index = 0
        self._init_instances()

    def _init_instances(self) -> None:
        self._mve_set_parameters()
        self._mox_set_parameters(self._mve_get_std(), self._mve_get_mean())
        if self._algorithm_type == ALGORITHM_TYPE_NOX:
            self._sigmoid_scaled_set_parameters(
                _f16(_SIGMOID_X0_NOX), _f16(_SIGMOID_K_NOX), _f16(_NOX_INDEX_OFFSET_DEFAULT)
            )
        else:
            self._sigmoid_scaled_set_parameters(
                _f16(_SIGMOID_X0_VOC), _f16(_SIGMOID_K_VOC), _f16(_VOC_INDEX_OFFSET_DEFAULT)
            )
        self._adaptive_lowpass_set_parameters()

    def get_states(self) -> "Tuple[int, int]":
        """Return (mean, std) internal states."""
        return self._mve_get_mean(), self._mve_get_std()

    def set_states(self, state0: int, state1: int) -> None:
        """Restore internal states from a prior :meth:`get_states` call. VOC only."""
        self._mve_set_states(state0, state1, _f16(_PERSISTENCE_UPTIME_GAMMA))
        self._mox_set_parameters(self._mve_get_std(), self._mve_get_mean())
        self._sraw = state0

    def set_tuning_parameters(
        self,
        index_offset: int,
        learning_time_offset_hours: int,
        learning_time_gain_hours: int,
        gating_max_duration_minutes: int,
        std_initial: int,
        gain_factor: int,
    ) -> None:
        self._index_offset = _fix16_from_int(index_offset)
        self._tau_mean_hours = _fix16_from_int(learning_time_offset_hours)
        self._tau_variance_hours = _fix16_from_int(learning_time_gain_hours)
        self._gating_max_duration_minutes = _fix16_from_int(gating_max_duration_minutes)
        self._sraw_std_initial = _fix16_from_int(std_initial)
        self._index_gain = _fix16_from_int(gain_factor)
        self._init_instances()

    def get_tuning_parameters(self) -> "Tuple[int, int, int, int, int, int]":
        return (
            _fix16_cast_to_int(self._index_offset),
            _fix16_cast_to_int(self._tau_mean_hours),
            _fix16_cast_to_int(self._tau_variance_hours),
            _fix16_cast_to_int(self._gating_max_duration_minutes),
            _fix16_cast_to_int(self._sraw_std_initial),
            _fix16_cast_to_int(self._index_gain),
        )

    def process(self, sraw: int) -> int:
        """Compute the gas index for a raw sensor tick value.

        :param int sraw: Raw VOC or NOx tick from the SGP41.
        :return: 0 during the initial 45 s blackout, otherwise 1..500.
        """
        if self._uptime <= _f16(_INITIAL_BLACKOUT):
            self._uptime += _f16(_SAMPLING_INTERVAL)
        else:
            if 0 < sraw < 65000:
                if sraw < self._sraw_minimum + 1:
                    sraw = self._sraw_minimum + 1
                elif sraw > self._sraw_minimum + 32767:
                    sraw = self._sraw_minimum + 32767
                self._sraw = _fix16_from_int(sraw - self._sraw_minimum)
            if self._algorithm_type == ALGORITHM_TYPE_VOC or self._mve_initialized:
                self._gas_index = self._mox_process(self._sraw)
                self._gas_index = self._sigmoid_scaled_process(self._gas_index)
            else:
                self._gas_index = self._index_offset
            self._gas_index = self._adaptive_lowpass_process(self._gas_index)
            self._gas_index = max(self._gas_index, _f16(0.5))
            if self._sraw > _f16(0.0):
                self._mve_process(self._sraw)
                self._mox_set_parameters(self._mve_get_std(), self._mve_get_mean())
        return _fix16_cast_to_int(self._gas_index + _f16(0.5))

    # ---------- Mean / variance estimator ----------

    def _mve_set_parameters(self) -> None:
        self._mve_initialized = False
        self._mve_mean = _f16(0.0)
        self._mve_sraw_offset = _f16(0.0)
        self._mve_std = self._sraw_std_initial
        self._mve_gamma_mean = _fix16_div(
            _f16(
                _MEAN_VARIANCE_ESTIMATOR__ADDITIONAL_GAMMA_MEAN_SCALING
                * _MEAN_VARIANCE_ESTIMATOR__GAMMA_SCALING
                * (_SAMPLING_INTERVAL / 3600.0)
            ),
            self._tau_mean_hours + _f16(_SAMPLING_INTERVAL / 3600.0),
        )
        self._mve_gamma_variance = _fix16_div(
            _f16(_MEAN_VARIANCE_ESTIMATOR__GAMMA_SCALING * (_SAMPLING_INTERVAL / 3600.0)),
            self._tau_variance_hours + _f16(_SAMPLING_INTERVAL / 3600.0),
        )
        if self._algorithm_type == ALGORITHM_TYPE_NOX:
            self._mve_gamma_initial_mean = _f16(
                (
                    _MEAN_VARIANCE_ESTIMATOR__ADDITIONAL_GAMMA_MEAN_SCALING
                    * _MEAN_VARIANCE_ESTIMATOR__GAMMA_SCALING
                    * _SAMPLING_INTERVAL
                )
                / (_TAU_INITIAL_MEAN_NOX + _SAMPLING_INTERVAL)
            )
        else:
            self._mve_gamma_initial_mean = _f16(
                (
                    _MEAN_VARIANCE_ESTIMATOR__ADDITIONAL_GAMMA_MEAN_SCALING
                    * _MEAN_VARIANCE_ESTIMATOR__GAMMA_SCALING
                    * _SAMPLING_INTERVAL
                )
                / (_TAU_INITIAL_MEAN_VOC + _SAMPLING_INTERVAL)
            )
        self._mve_gamma_initial_variance = _f16(
            (_MEAN_VARIANCE_ESTIMATOR__GAMMA_SCALING * _SAMPLING_INTERVAL)
            / (_TAU_INITIAL_VARIANCE + _SAMPLING_INTERVAL)
        )
        self._mve_out_gamma_mean = _f16(0.0)
        self._mve_out_gamma_variance = _f16(0.0)
        self._mve_uptime_gamma = _f16(0.0)
        self._mve_uptime_gating = _f16(0.0)
        self._mve_gating_duration_minutes = _f16(0.0)

    def _mve_set_states(self, mean: int, std: int, uptime_gamma: int) -> None:
        self._mve_mean = mean
        self._mve_std = std
        self._mve_uptime_gamma = uptime_gamma
        self._mve_initialized = True

    def _mve_get_std(self) -> int:
        return self._mve_std

    def _mve_get_mean(self) -> int:
        return self._mve_mean + self._mve_sraw_offset

    def _mve_calculate_gamma(self) -> None:
        uptime_limit = _f16(_MEAN_VARIANCE_ESTIMATOR__FIX16_MAX - _SAMPLING_INTERVAL)
        if self._mve_uptime_gamma < uptime_limit:
            self._mve_uptime_gamma += _f16(_SAMPLING_INTERVAL)
        if self._mve_uptime_gating < uptime_limit:
            self._mve_uptime_gating += _f16(_SAMPLING_INTERVAL)

        self._mve_sigmoid_set_parameters(self._init_duration_mean, _f16(_INIT_TRANSITION_MEAN))
        sigmoid_gamma_mean = self._mve_sigmoid_process(self._mve_uptime_gamma)
        gamma_mean = self._mve_gamma_mean + _fix16_mul(
            self._mve_gamma_initial_mean - self._mve_gamma_mean, sigmoid_gamma_mean
        )
        gating_threshold_mean = self._gating_threshold + _fix16_mul(
            _f16(_GATING_THRESHOLD_INITIAL) - self._gating_threshold,
            self._mve_sigmoid_process(self._mve_uptime_gating),
        )
        self._mve_sigmoid_set_parameters(gating_threshold_mean, _f16(_GATING_THRESHOLD_TRANSITION))
        sigmoid_gating_mean = self._mve_sigmoid_process(self._gas_index)
        self._mve_out_gamma_mean = _fix16_mul(sigmoid_gating_mean, gamma_mean)

        self._mve_sigmoid_set_parameters(
            self._init_duration_variance, _f16(_INIT_TRANSITION_VARIANCE)
        )
        sigmoid_gamma_variance = self._mve_sigmoid_process(self._mve_uptime_gamma)
        gamma_variance = self._mve_gamma_variance + _fix16_mul(
            self._mve_gamma_initial_variance - self._mve_gamma_variance,
            sigmoid_gamma_variance - sigmoid_gamma_mean,
        )
        gating_threshold_variance = self._gating_threshold + _fix16_mul(
            _f16(_GATING_THRESHOLD_INITIAL) - self._gating_threshold,
            self._mve_sigmoid_process(self._mve_uptime_gating),
        )
        self._mve_sigmoid_set_parameters(
            gating_threshold_variance, _f16(_GATING_THRESHOLD_TRANSITION)
        )
        sigmoid_gating_variance = self._mve_sigmoid_process(self._gas_index)
        self._mve_out_gamma_variance = _fix16_mul(sigmoid_gating_variance, gamma_variance)

        self._mve_gating_duration_minutes += _fix16_mul(
            _f16(_SAMPLING_INTERVAL / 60.0),
            _fix16_mul(_f16(1.0) - sigmoid_gating_mean, _f16(1.0 + _GATING_MAX_RATIO))
            - _f16(_GATING_MAX_RATIO),
        )
        self._mve_gating_duration_minutes = max(self._mve_gating_duration_minutes, _f16(0.0))
        if self._mve_gating_duration_minutes > self._gating_max_duration_minutes:
            self._mve_uptime_gating = _f16(0.0)

    def _mve_process(self, sraw: int) -> None:
        if not self._mve_initialized:
            self._mve_initialized = True
            self._mve_sraw_offset = sraw
            self._mve_mean = _f16(0.0)
            return
        if self._mve_mean >= _f16(100.0) or self._mve_mean <= _f16(-100.0):
            self._mve_sraw_offset += self._mve_mean
            self._mve_mean = _f16(0.0)
        sraw -= self._mve_sraw_offset
        self._mve_calculate_gamma()
        delta_sgp = _fix16_div(sraw - self._mve_mean, _f16(_MEAN_VARIANCE_ESTIMATOR__GAMMA_SCALING))
        if delta_sgp < _f16(0.0):
            c = self._mve_std - delta_sgp
        else:
            c = self._mve_std + delta_sgp
        additional_scaling = _f16(1.0)
        if c > _f16(1440.0):
            additional_scaling = _fix16_mul(
                _fix16_div(c, _f16(1440.0)), _fix16_div(c, _f16(1440.0))
            )
        self._mve_std = _fix16_mul(
            _fix16_sqrt(
                _fix16_mul(
                    additional_scaling,
                    _f16(_MEAN_VARIANCE_ESTIMATOR__GAMMA_SCALING) - self._mve_out_gamma_variance,
                )
            ),
            _fix16_sqrt(
                _fix16_mul(
                    self._mve_std,
                    _fix16_div(
                        self._mve_std,
                        _fix16_mul(
                            _f16(_MEAN_VARIANCE_ESTIMATOR__GAMMA_SCALING), additional_scaling
                        ),
                    ),
                )
                + _fix16_mul(
                    _fix16_div(
                        _fix16_mul(self._mve_out_gamma_variance, delta_sgp), additional_scaling
                    ),
                    delta_sgp,
                )
            ),
        )
        self._mve_mean += _fix16_div(
            _fix16_mul(self._mve_out_gamma_mean, delta_sgp),
            _f16(_MEAN_VARIANCE_ESTIMATOR__ADDITIONAL_GAMMA_MEAN_SCALING),
        )

    def _mve_sigmoid_set_parameters(self, x0: int, k: int) -> None:
        self._mve_sigmoid_k = k
        self._mve_sigmoid_x0 = x0

    def _mve_sigmoid_process(self, sample: int) -> int:
        x = _fix16_mul(self._mve_sigmoid_k, sample - self._mve_sigmoid_x0)
        if x < _f16(-50.0):
            return _f16(1.0)
        if x > _f16(50.0):
            return _f16(0.0)
        return _fix16_div(_f16(1.0), _f16(1.0) + _fix16_exp(x))

    # ---------- MOX model ----------

    def _mox_set_parameters(self, sraw_std: int, sraw_mean: int) -> None:
        self._mox_sraw_std = sraw_std
        self._mox_sraw_mean = sraw_mean

    def _mox_process(self, sraw: int) -> int:
        if self._algorithm_type == ALGORITHM_TYPE_NOX:
            return _fix16_mul(
                _fix16_div(sraw - self._mox_sraw_mean, _f16(_SRAW_STD_NOX)), self._index_gain
            )
        return _fix16_mul(
            _fix16_div(
                sraw - self._mox_sraw_mean, -(self._mox_sraw_std + _f16(_SRAW_STD_BONUS_VOC))
            ),
            self._index_gain,
        )

    # ---------- Scaled sigmoid ----------

    def _sigmoid_scaled_set_parameters(self, x0: int, k: int, offset_default: int) -> None:
        self._sig_k = k
        self._sig_x0 = x0
        self._sig_offset_default = offset_default

    def _sigmoid_scaled_process(self, sample: int) -> int:
        x = _fix16_mul(self._sig_k, sample - self._sig_x0)
        if x < _f16(-50.0):
            return _f16(_SIGMOID_L)
        if x > _f16(50.0):
            return _f16(0.0)
        if sample >= _f16(0.0):
            if self._sig_offset_default == _f16(1.0):
                shift = _fix16_mul(_f16(500.0 / 499.0), _f16(1.0) - self._index_offset)
            else:
                shift = _fix16_div(
                    _f16(_SIGMOID_L) - _fix16_mul(_f16(5.0), self._index_offset), _f16(4.0)
                )
            return _fix16_div(_f16(_SIGMOID_L) + shift, _f16(1.0) + _fix16_exp(x)) - shift
        return _fix16_mul(
            _fix16_div(self._index_offset, self._sig_offset_default),
            _fix16_div(_f16(_SIGMOID_L), _f16(1.0) + _fix16_exp(x)),
        )

    # ---------- Adaptive lowpass ----------

    def _adaptive_lowpass_set_parameters(self) -> None:
        self._lp_a1 = _f16(_SAMPLING_INTERVAL / (_LP_TAU_FAST + _SAMPLING_INTERVAL))
        self._lp_a2 = _f16(_SAMPLING_INTERVAL / (_LP_TAU_SLOW + _SAMPLING_INTERVAL))
        self._lp_initialized = False

    def _adaptive_lowpass_process(self, sample: int) -> int:
        if not self._lp_initialized:
            self._lp_x1 = sample
            self._lp_x2 = sample
            self._lp_x3 = sample
            self._lp_initialized = True
        self._lp_x1 = _fix16_mul(_f16(1.0) - self._lp_a1, self._lp_x1) + _fix16_mul(
            self._lp_a1, sample
        )
        self._lp_x2 = _fix16_mul(_f16(1.0) - self._lp_a2, self._lp_x2) + _fix16_mul(
            self._lp_a2, sample
        )
        abs_delta = self._lp_x1 - self._lp_x2
        if abs_delta < _f16(0.0):
            abs_delta = -abs_delta
        f1 = _fix16_exp(_fix16_mul(_f16(_LP_ALPHA), abs_delta))
        tau_a = _fix16_mul(_f16(_LP_TAU_SLOW - _LP_TAU_FAST), f1) + _f16(_LP_TAU_FAST)
        a3 = _fix16_div(_f16(_SAMPLING_INTERVAL), _f16(_SAMPLING_INTERVAL) + tau_a)
        self._lp_x3 = _fix16_mul(_f16(1.0) - a3, self._lp_x3) + _fix16_mul(a3, sample)
        return self._lp_x3
