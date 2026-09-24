# SPDX-FileCopyrightText: 2026 Pedro Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
`adafruit_meshfruit`
================================================================================

Decode LoRa mesh packets compatible with the Meshtastic protocol.

* Author(s): Pedro Ruiz

Implementation Notes
--------------------

**Hardware:**

* `Adafruit RFM95W LoRa Radio Transceiver Breakout <https://www.adafruit.com/product/3072>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

"""

import aesio
from micropython import const

try:
    from typing import Dict, Optional, Tuple, Union
except ImportError:
    pass

__version__ = "1.0.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_Meshfruit.git"

HEADER_LEN = const(16)
_CHANNEL_HASH_OFFSET = const(13)

PORT_TEXT_MESSAGE = const(1)
PORT_POSITION = const(3)
PORT_NODEINFO = const(4)


class MeshtasticPacket_Compatible:
    """One received Meshtastic compatible packet

    :param bytes raw: A complete packet, header included
    :param bytes key: The expanded channel key
    """

    def __init__(self, raw: Union[bytes, bytearray], key: Optional[bytes]) -> None:
        self._raw = raw
        self._key = key
        self._plaintext = None
        self._parsed = False
        self._portnum = None
        self._payload = None

    @property
    def raw(self) -> Union[bytes, bytearray]:
        """The packet as received, header included.

        :rtype: bytes
        """
        return self._raw

    @property
    def sender_id(self) -> str:
        """Sender node ID as a bang-prefixed hex string.

        :rtype: str
        """
        return f"!{int.from_bytes(self._raw[4:8], 'little'):08x}"

    @property
    def channel_hash(self) -> int:
        """Channel hash byte used to filter incoming packets.

        :rtype: int
        """
        return self._raw[_CHANNEL_HASH_OFFSET]

    @property
    def nonce(self) -> bytes:
        """The 16-byte AES-CTR initialization vector for this packet.

        :rtype: bytes
        """
        packet_id = bytes(self._raw[8:12])
        sender = bytes(self._raw[4:8])
        return packet_id + bytes(4) + sender + bytes(4)

    @property
    def plaintext(self) -> bytearray:
        """The decrypted payload, decrypted on first access.

        :rtype: bytearray
        """
        if self._plaintext is None:
            ciphertext = self._raw[HEADER_LEN:]
            plaintext = bytearray(len(ciphertext))
            aesio.AES(self._key, aesio.MODE_CTR, self.nonce).encrypt_into(ciphertext, plaintext)
            self._plaintext = plaintext
        return self._plaintext

    @property
    def portnum(self) -> Optional[int]:
        """The port number. None if the field was absent.

        :rtype: int
        """
        self._parse()
        return self._portnum

    @property
    def payload(self) -> Optional[bytearray]:
        """The payload bytes. None if the field was absent.

        :rtype: bytearray
        """
        self._parse()
        return self._payload

    @property
    def text(self) -> Optional[str]:
        """The payload decoded as text.

        :rtype: str
        """
        raw = self.payload
        if raw is None:
            return None
        try:
            return raw.decode("utf-8")
        except UnicodeError:
            return None

    @property
    def user(self) -> Dict[str, bytearray]:
        """The User fields of a :const:`PORT_NODEINFO` payload.

        Any of ``id``, ``long_name`` and ``short_name`` that were
        present, each as raw bytes.

        :rtype: dict
        """
        result = {}
        buf = self.payload
        if buf is None:
            return result
        index = 0
        while index < len(buf):
            tag, index = self._read_varint(buf, index)
            wire = tag & 0x07
            if index >= len(buf) and wire in {0, 2}:
                break
            field = tag >> 3
            if wire == 0:
                _, index = self._read_varint(buf, index)
            elif wire == 2:
                length, index = self._read_varint(buf, index)
                chunk = buf[index : index + length]
                index += length
                if field == 1:
                    result["id"] = chunk
                elif field == 2:
                    result["long_name"] = chunk
                elif field == 3:
                    result["short_name"] = chunk
            elif wire == 5:
                index += 4
            elif wire == 1:
                index += 8
            else:
                break
        return result

    @staticmethod
    def _read_varint(buf: Union[bytes, bytearray], index: int) -> Tuple[int, int]:
        """Read a protobuf varint.

        :param bytes buf: Buffer to read from
        :param int index: Offset to start reading at
        :return: The decoded value and the offset just past it
        :rtype: tuple
        """
        value = 0
        shift = 0
        while index < len(buf):
            byte = buf[index]
            index += 1
            value |= (byte & 0x7F) << shift
            if not byte & 0x80:
                break
            shift += 7
        return value, index

    def _parse(self) -> None:
        """Walk the Data protobuf once and remember what it held."""
        if self._parsed:
            return
        self._parsed = True
        buf = self.plaintext
        index = 0
        while index < len(buf):
            tag, index = self._read_varint(buf, index)
            wire = tag & 0x07
            # A tag with no room left for its value means the buffer
            # was truncated. Stop rather than inventing an empty field.
            if index >= len(buf) and wire in {0, 2}:
                break
            field = tag >> 3
            if wire == 0:
                value, index = self._read_varint(buf, index)
                if field == 1:
                    self._portnum = value
            elif wire == 2:
                length, index = self._read_varint(buf, index)
                chunk = buf[index : index + length]
                index += length
                if field == 2:
                    self._payload = chunk
            elif wire == 5:
                index += 4
            elif wire == 1:
                index += 8
            else:
                break


class Meshtastic_Compatible:
    """Settings for one Meshtastic compatible channel.

    :param bytes psk: The channel pre-shared key, 0, 1, 16 or 32 bytes.
        Defaults to :attr:`DEFAULT_KEY`

    :raises ValueError: if the PSK is not one of the accepted lengths
    """

    DEFAULT_KEY = bytes.fromhex("d4f1bb3a20290759f0bcffabcf4e6901")

    def __init__(self, psk: Optional[Union[bytes, bytearray]] = None) -> None:
        self._psk = None
        self._key = None
        self.psk = self.DEFAULT_KEY if psk is None else psk

    @property
    def psk(self) -> bytes:
        """Channel pre-shared key

        :rtype: bytes

        :raises ValueError: if the PSK is not one of the accepted
            lengths
        """
        return self._psk

    @psk.setter
    def psk(self, value: Union[bytes, bytearray]) -> None:
        value = bytes(value)
        if len(value) == 0 or (len(value) == 1 and value[0] == 0):
            key = None
        elif len(value) == 1:
            key = self.DEFAULT_KEY[:-1] + value
        elif len(value) in {16, 32}:
            key = value
        else:
            raise ValueError("PSK must be 0, 1, 16, or 32 bytes")
        self._key = key
        self._psk = value

    @property
    def key(self) -> Optional[bytes]:
        """Expanded AES key.

        None if the channel is unencrypted.

        :rtype: bytes
        """
        return self._key

    def decode(self, raw: Union[bytes, bytearray]) -> MeshtasticPacket_Compatible:
        """Wrap a received buffer as a packet on this channel.

        Nothing is decrypted here. The work happens when a property of
        the returned packet asks for it.

        :param bytes raw: A complete packet, header included
        :return: The packet, holding this channel's key
        :rtype: MeshtasticPacket_Compatible
        """
        return MeshtasticPacket_Compatible(raw, self._key)
