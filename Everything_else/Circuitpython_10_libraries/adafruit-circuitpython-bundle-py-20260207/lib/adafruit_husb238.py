# SPDX-FileCopyrightText: Copyright (c) 2023 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
# Written by ladyada (Adafruit Industries) and Liz Clark (Adafruit Industries)
# with OpenAI ChatGPT v4 September 25, 2023 build
# https://help.openai.com/en/articles/6825453-chatgpt-release-notes

# https://chat.openai.com/share/67b3bd79-ddc0-471b-91e9-9b15342fa62b
# https://chat.openai.com/share/653e461a-ec7a-4a03-93ee-db2ee3ebdb74
"""
`adafruit_husb238`
================================================================================

CircuitPython helper library for the HUSB238 Type C Power Delivery Dummy Breakout


* Author(s): Liz Clark

Implementation Notes
--------------------

**Hardware:**

* `Adafruit USB Type C PD Breakout - HUSB238 <https://www.adafruit.com/product/5807>`_"

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
* Adafruit's Register library: https://github.com/adafruit/Adafruit_CircuitPython_Register
"""

import time

from adafruit_bus_device.i2c_device import I2CDevice
from adafruit_register.i2c_bit import ROBit
from adafruit_register.i2c_bits import ROBits, RWBits
from adafruit_register.i2c_struct import UnaryStruct
from micropython import const

try:
    import typing

    from busio import I2C
except ImportError:
    pass

__version__ = "1.0.6"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_HUSB238.git"

_I2CADDR_DEFAULT = const(0x08)

_PD_STATUS0 = const(0x00)
_PD_STATUS1 = const(0x01)
_SRC_PDO_5V = const(0x02)
_SRC_PDO_9V = const(0x03)
_SRC_PDO_12V = const(0x04)
_SRC_PDO_15V = const(0x05)
_SRC_PDO_18V = const(0x06)
_SRC_PDO_20V = const(0x07)
_SRC_PDO = const(0x08)
_GO_COMMAND = const(0x09)


class Adafruit_HUSB238:
    """
    Instantiates a new HUSB238 class.
    """

    cc_direction = ROBit(_PD_STATUS1, 7)
    """
    CC direction
    """
    attached = ROBit(_PD_STATUS1, 6)
    """
    Attachment status
    """
    response = ROBits(3, _PD_STATUS1, 3)
    """
    PD response
    """
    contract_v_5v = ROBit(_PD_STATUS1, 2)
    """
    5V contract voltage status
    """
    contract_a_5v = ROBits(2, _PD_STATUS1, 0)
    """
    5V contract current status
    """
    _pd_src_voltage = ROBits(4, _PD_STATUS0, 4)
    _pd_src_current = ROBits(4, _PD_STATUS0, 0)
    _voltage_detected_5v = ROBit(_SRC_PDO_5V, 7)
    _voltage_detected_9v = ROBit(_SRC_PDO_9V, 7)
    _voltage_detected_12v = ROBit(_SRC_PDO_12V, 7)
    _voltage_detected_15v = ROBit(_SRC_PDO_15V, 7)
    _voltage_detected_18v = ROBit(_SRC_PDO_18V, 7)
    _voltage_detected_20v = ROBit(_SRC_PDO_20V, 7)
    _selected_pd = RWBits(4, _SRC_PDO, 4)
    _go_command = UnaryStruct(_GO_COMMAND, "<B")
    _src_pdo = UnaryStruct(_SRC_PDO, "<B")

    # Voltage to PDO mapping
    _VOLTAGE_TO_PDO = {
        5: 0b0001,  # 5V
        9: 0b0010,  # 9V
        12: 0b0011,  # 12V
        15: 0b1000,  # 15V
        18: 0b1001,  # 18V
        20: 0b1010,  # 20V
    }
    # PDO to voltage mapping
    _PDO_TO_VOLTAGE = [
        None,  # Unattached
        5,  # 5V
        9,  # 9V
        12,  # 12V
        15,  # 15V
        18,  # 18V
        20,  # 20V
    ]
    # PDO to current mapping
    _PDO_TO_CURRENT = [
        0.5,
        0.7,
        1.0,
        1.25,
        1.5,
        1.75,
        2.0,
        2.25,
        2.5,
        2.75,
        3.0,
        3.25,
        3.5,
        4.0,
        4.5,
        5.0,
    ]
    # PDO response codes
    _PDO_RESPONSE_CODES = [
        "NO RESPONSE",
        None,  # Success
        None,  # Reserved
        "INVALID COMMAND OR ARGUMENT",
        "COMMAND NOT SUPPORTED",
        "TRANSACTION FAILED, NO GOOD CRC",
    ]

    def __init__(self, i2c: typing.Type[I2C], i2c_address: int = _I2CADDR_DEFAULT) -> None:
        """
        :param i2c: The I2C device we'll use to communicate.
        :type i2c: Type[I2C]
        :param i2c_address: The 7-bit I2C address of the HUSB238, defaults to 0x40.
        :type i2c_address: int
        """
        self.i2c_device = I2CDevice(i2c, i2c_address)

    @property
    def available_voltages(self) -> typing.List[int]:
        """
        List of available voltages

        :return: List of available voltages.
        :rtype: List[int]
        """
        _available_voltages = []

        for voltage, detected in [
            (5, self._voltage_detected_5v),
            (9, self._voltage_detected_9v),
            (12, self._voltage_detected_12v),
            (15, self._voltage_detected_15v),
            (18, self._voltage_detected_18v),
            (20, self._voltage_detected_20v),
        ]:
            if detected:
                _available_voltages.append(voltage)

        return _available_voltages

    @property
    def current(self) -> int:
        """
        Source current

        :return: The source current
        :rtype: int
        """
        return self._PDO_TO_CURRENT[self._pd_src_current]

    def reset(self) -> None:
        """
        Reset command to the HUSB238 device.
        """
        self._go_command = 0x01

    @property
    def voltage(self) -> int:
        """
        PD voltage

        :rtype: int
        """
        return self._PDO_TO_VOLTAGE[self._pd_src_voltage]

    @voltage.setter
    def voltage(self, value: int) -> None:
        if value not in self._VOLTAGE_TO_PDO:
            raise ValueError(f"Invalid voltage: {value}V")
        pdo_value = self._VOLTAGE_TO_PDO[value]
        self._selected_pd = pdo_value
        self._go_command = 0b00001
        time.sleep(0.01)  # 10 milliseconds delay
        if self.response != 1:
            raise RuntimeError(self._PDO_RESPONSE_CODES[self.response])
