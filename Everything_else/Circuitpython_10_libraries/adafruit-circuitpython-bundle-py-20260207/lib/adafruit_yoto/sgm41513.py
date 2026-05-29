# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
`adafruit_yoto.sgm41513`
================================================================================

CircuitPython driver for SGM41513 Battery Charger IC


* Author(s): Liz Clark

"""

from adafruit_bus_device.i2c_device import I2CDevice
from adafruit_register.i2c_bit import RWBit
from adafruit_register.i2c_bits import ROBits, RWBits
from micropython import const

_DEFAULT_ADDRESS = const(0x1A)
_INPUT_SOURCE = const(0x00)
_POWER_ON_CONFIG = const(0x01)
_CHARGE_CURRENT = const(0x02)
_CHARGE_VOLTAGE = const(0x04)
_SYSTEM_STATUS = const(0x08)
_PART_INFO = const(0x0B)


class SGM41513:
    """Driver for SGM41513 Battery Charger IC"""

    hiz_mode = RWBit(_INPUT_SOURCE, 7)
    """Enable HIZ mode (disconnect VBUS from internal circuit)"""
    charge_enabled = RWBit(_POWER_ON_CONFIG, 4)
    """Enable or disable battery charging"""
    _ichg_raw = RWBits(6, _CHARGE_CURRENT, 0)
    _vreg_raw = RWBits(5, _CHARGE_VOLTAGE, 3)
    _vbus_stat = ROBits(3, _SYSTEM_STATUS, 5)
    _chrg_stat = ROBits(2, _SYSTEM_STATUS, 3)
    _pg_stat = ROBits(1, _SYSTEM_STATUS, 2)
    _pn = ROBits(4, _PART_INFO, 3)
    _dev_rev = ROBits(2, _PART_INFO, 0)

    def __init__(self, i2c, address=_DEFAULT_ADDRESS):
        self.i2c_device = I2CDevice(i2c, address)

    @property
    def part_info(self):
        """Part number and revision information

        :return: Dictionary with part_number and revision
        :rtype: dict
        """
        pn = self._pn
        rev = self._dev_rev
        part_names = {0b0000: "SGM41513", 0b0001: "SGM41513A/SGM41513D"}
        return {"part_number": part_names.get(pn, f"Unknown (0x{pn:X})"), "revision": rev}

    @property
    def system_status(self):
        """Current system status

        :return: Dictionary with VBUS status, charge status,
                 power good, thermal regulation, and VSYS regulation

        :rtype: dict
        """
        vbus_stat = self._vbus_stat
        chrg_stat = self._chrg_stat

        vbus_names = {
            0b000: "No Input",
            0b001: "USB SDP",
            0b010: "Adapter",
            0b011: "USB CDP",
        }

        chrg_names = {0b00: "Disabled", 0b01: "Pre-charge", 0b10: "Fast Charge", 0b11: "Complete"}

        return {
            "vbus_status": vbus_names.get(vbus_stat, f"Unknown"),
            "vbus_stat_code": vbus_stat,
            "charge_status": chrg_names.get(chrg_stat, f"Unknown"),
            "charge_stat_code": chrg_stat,
            "power_good": bool(self._pg_stat),
        }

    @property
    def charge_current(self):
        """Charge current setting in mA

        :return: Charge current in milliamps
        :rtype: int
        """
        code = self._ichg_raw
        if code <= 0x0F:
            currents = [0, 5, 10, 15, 20, 25, 30, 35, 40, 50, 60, 70, 80, 90, 100, 110]
            return currents[code] if code < len(currents) else 110
        elif code <= 0x1F:
            return 130 + (code - 0x10) * 20
        elif code <= 0x2F:
            return 540 + (code - 0x20) * 60
        else:
            return min(1500 + (code - 0x30) * 120, 3000)

    @property
    def charge_voltage(self):
        """Charge voltage setting in mV

        :return: Charge voltage in millivolts
        :rtype: int
        """
        code = self._vreg_raw
        if code == 0x0F:
            return 4350
        elif code <= 24:
            return 3856 + (code * 32)
        else:
            return 4624
