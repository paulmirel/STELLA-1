# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
`adafruit_yoto.cr95hf`
================================================================================

CR95HF NFC/RFID Transceiver Driver for CircuitPython


* Author(s): Liz Clark

"""

import time

# Command Codes
CMD_IDN = 0x01
CMD_PROTOCOL = 0x02
CMD_SENDRECV = 0x04
CMD_ECHO = 0x55

# Response Codes
RSP_SUCCESS = 0x00
RSP_DATA = 0x80

# Protocol Codes
PROTO_OFF = 0x00
PROTO_ISO14443A = 0x02

# ISO14443-A Commands
ISO14443A_REQA = 0x26
ISO14443A_WUPA = 0x52
ISO14443A_CT = 0x88
ISO14443A_SEL_CL1 = 0x93
ISO14443A_SEL_CL2 = 0x95
ISO14443A_NVB_ANTICOLL = 0x20
ISO14443A_NVB_SELECT = 0x70

# Transmit Flags
FLAG_SHORTFRAME = 0x07
FLAG_STD = 0x08
FLAG_STD_CRC = 0x28

# SAK Card Types
SAK_MIFARE_UL = 0x00
SAK_MIFARE_1K = 0x08
SAK_MIFARE_MINI = 0x09
SAK_MIFARE_4K = 0x18


class CR95HF:
    """CR95HF NFC/RFID driver for CircuitPython"""

    def __init__(self, uart, wake_pulse_ms=100):
        self.uart = uart
        self._device_name = ""
        self._last_atqa = bytearray(2)
        self._initialize(wake_pulse_ms)

    def _flush_rx(self):
        while self.uart.in_waiting:
            self.uart.read(self.uart.in_waiting)

    def _send_cmd(self, cmd, data=b""):
        frame = bytes([cmd, len(data)]) + data
        self._flush_rx()
        self.uart.write(frame)

    def _read_response(self, timeout_ms=100):
        start = time.monotonic()
        timeout_s = timeout_ms / 1000.0

        while self.uart.in_waiting == 0:
            if time.monotonic() - start > timeout_s:
                raise TimeoutError("Timeout waiting for result code")
        result_code = self.uart.read(1)[0]

        while self.uart.in_waiting == 0:
            if time.monotonic() - start > timeout_s:
                raise TimeoutError("Timeout waiting for length byte")
        length = self.uart.read(1)[0]

        data = bytearray()
        while len(data) < length:
            available = self.uart.in_waiting
            if available > 0:
                chunk = self.uart.read(min(available, length - len(data)))
                data.extend(chunk)
            elif time.monotonic() - start > timeout_s:
                raise TimeoutError(f"Timeout reading data")

        return result_code, bytes(data)

    def echo_test(self):
        self._flush_rx()
        self.uart.write(bytes([CMD_ECHO]))

        start = time.monotonic()
        while time.monotonic() - start < 0.1:
            if self.uart.in_waiting > 0:
                resp = self.uart.read(1)[0]
                if resp == CMD_ECHO:
                    return
                raise OSError(f"Echo test failed: expected 0x55, got 0x{resp:02X}")
        raise OSError("Echo test failed: no response")

    def _initialize(self, wake_pulse_ms=100):
        self._flush_rx()
        wake_bytes = bytes([0x00] * 20)
        start = time.monotonic()
        while time.monotonic() - start < wake_pulse_ms / 1000.0:
            self.uart.write(wake_bytes)
            time.sleep(0.001)

        time.sleep(0.015)
        self._flush_rx()

        self.echo_test()

        self._send_cmd(CMD_IDN)
        code, data = self._read_response(100)

        if code != RSP_SUCCESS or not data or len(data) < 13:
            raise OSError(f"Invalid IDN response")

        device_bytes = data[:13]
        self._device_name = ""
        for b in device_bytes:
            if b == 0:
                break
            if 32 <= b <= 126:
                self._device_name += chr(b)

        self._send_cmd(CMD_PROTOCOL, bytes([PROTO_ISO14443A, 0x00]))
        code, data = self._read_response(100)

        if code != RSP_SUCCESS:
            raise OSError(f"Protocol selection failed")

    def _sendrecv(self, rf_data, flags):
        cmd_data = rf_data + bytes([flags])
        self._send_cmd(CMD_SENDRECV, cmd_data)
        return self._read_response(50)

    def _reqa_wupa(self, cmd):
        code, data = self._sendrecv(bytes([cmd]), FLAG_SHORTFRAME)
        if code == RSP_DATA and data and len(data) >= 2:
            return data[0], data[1]
        return None, None

    def _anticoll_cl1(self):
        rf_data = bytes([ISO14443A_SEL_CL1, ISO14443A_NVB_ANTICOLL])
        code, data = self._sendrecv(rf_data, FLAG_STD)
        if code == RSP_DATA and data and len(data) >= 5:
            return data[:5]
        return None

    def _select_cl1(self, uid_bcc):
        rf_data = bytes([ISO14443A_SEL_CL1, ISO14443A_NVB_SELECT]) + uid_bcc
        code, data = self._sendrecv(rf_data, FLAG_STD_CRC)
        if code == RSP_DATA and data and len(data) >= 1:
            return data[0]
        return None

    def _anticoll_cl2(self):
        rf_data = bytes([ISO14443A_SEL_CL2, ISO14443A_NVB_ANTICOLL])
        code, data = self._sendrecv(rf_data, FLAG_STD)
        if code == RSP_DATA and data and len(data) >= 5:
            return data[:5]
        return None

    def _select_cl2(self, uid_bcc):
        rf_data = bytes([ISO14443A_SEL_CL2, ISO14443A_NVB_SELECT]) + uid_bcc
        code, data = self._sendrecv(rf_data, FLAG_STD_CRC)
        if code == RSP_DATA and data and len(data) >= 1:
            return data[0]
        return None

    def read_tag(self):  # noqa: PLR0911
        """Read ISO14443-A tag UID. Returns (uid_bytes, sak_byte) or (None, None)"""
        atqa1, atqa2 = self._reqa_wupa(ISO14443A_WUPA)
        if atqa1 is None:
            atqa1, atqa2 = self._reqa_wupa(ISO14443A_REQA)

        if atqa1 is None:
            return None, None

        self._last_atqa[0] = atqa1
        self._last_atqa[1] = atqa2

        cl1 = self._anticoll_cl1()
        if cl1 is None:
            return None, None

        sak1 = self._select_cl1(cl1)
        if sak1 is None:
            return None, None

        if cl1[0] != ISO14443A_CT:
            return bytes(cl1[:4]), sak1

        uid = bytearray(cl1[1:4])

        cl2 = self._anticoll_cl2()
        if cl2 is None:
            return None, None

        sak2 = self._select_cl2(cl2)
        if sak2 is None:
            return None, None

        uid.extend(cl2[:4])
        return bytes(uid), sak2

    @staticmethod
    def card_type(sak):
        """Card type from SAK byte"""
        card_types = {
            SAK_MIFARE_UL: "MIFARE Ultralight/NTAG",
            SAK_MIFARE_1K: "MIFARE Classic 1K",
            SAK_MIFARE_MINI: "MIFARE Mini",
            SAK_MIFARE_4K: "MIFARE Classic 4K",
        }
        return card_types.get(sak, f"Unknown (SAK=0x{sak:02X})")

    def field_off(self):
        """Turn off RF field"""
        self._send_cmd(CMD_PROTOCOL, bytes([PROTO_OFF, 0x00]))
        self._read_response(50)

    @property
    def device_name(self):
        """Device identification string"""
        return self._device_name
