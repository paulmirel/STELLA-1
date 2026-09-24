# SPDX-FileCopyrightText: Copyright (c) 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
:py:class:`~adafruit_ay8912.vgm_player.VGMFile`
================================================================================

VGM chiptune file parser and player for CircuitPython.

Plays VGM (and gzip-compressed VGZ) files through an
:py:class:`~adafruit_ay8912.ay8912_emulator.AY8912` instance.

Only files with a non-zero AY-3-8910 clock (header offset ``0x74``) are
supported. Files targeting other chips (SN76489, YM2612, etc.) are rejected.

* Author(s): Liz Clark

Implementation Notes
--------------------

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads
"""

import struct
import time

try:
    from typing import TYPE_CHECKING, Optional, Tuple

    if TYPE_CHECKING:
        from .ay8912_emulator import AY8912
except ImportError:
    pass

try:
    import zlib
except ImportError:
    zlib = None

__version__ = "1.0.0"
__repo__ = "https://github.com/your-org/Adafruit_CircuitPython_AY8912.git"

# VGM runs on a 44100 Hz sample clock for all wait commands
_VGM_RATE = 44100


class VGMFile:
    """Parse and play an AY8912 VGM/VGZ file.

    :param str filename: Path to a ``.vgm`` or ``.vgz`` file to load
        immediately. Pass ``None`` to create an empty object and call
        :meth:`load` later.
    """

    def __init__(self, filename: Optional[str] = None) -> None:
        self._data = None
        self._ay = None

        # Metadata
        self._title = ""
        self._author = ""
        self._game = ""

        # Header info
        self._clock_hz = 1773400
        self._total_samples = 0
        self._loop_offset = 0
        self._loop_samples = 0
        self._data_offset = 0
        self._eof_offset = 0
        self._version = 0

        # Playback state
        self._pos = 0  # current byte position in command stream
        self._playing = False
        self._sample_clock = 0  # cumulative samples played
        self._wait_remaining = 0  # samples still to wait
        self._next_time = 0.0  # monotonic time of next command batch
        self._loop_count = 0  # how many times we've looped

        if filename:
            self.load(filename)

    @property
    def title(self) -> str:
        """Track title from the GD3 tag, or ``""`` if absent."""
        return self._title

    @property
    def author(self) -> str:
        """Track author from the GD3 tag, or ``""`` if absent."""
        return self._author

    @property
    def game(self) -> str:
        """Game/source name from the GD3 tag, or ``""`` if absent."""
        return self._game

    @property
    def clock_hz(self) -> int:
        """AY chip clock in Hz."""
        return self._clock_hz

    @property
    def version(self) -> int:
        """VGM format version as a packed BCD integer"""
        return self._version

    @property
    def total_samples(self) -> int:
        """Total length of the song in 44100 Hz samples."""
        return self._total_samples

    @property
    def duration(self) -> float:
        """Song duration in seconds."""
        if self._total_samples:
            return self._total_samples / _VGM_RATE
        return 0

    @property
    def elapsed(self) -> float:
        """Elapsed playback time in seconds."""
        return self._sample_clock / _VGM_RATE

    @property
    def progress(self) -> float:
        """Playback progress as a fraction from ``0.0`` to ``1.0``."""
        if self._total_samples:
            p = self._sample_clock / self._total_samples
            return p if p < 1.0 else 1.0
        return 0

    @property
    def loop_count(self) -> int:
        """How many times the song has looped back."""
        return self._loop_count

    @property
    def loops(self) -> bool:
        """``True`` if this song defines a loop point."""
        return bool(self._loop_offset and self._loop_samples)

    @property
    def playing(self) -> bool:
        """``True`` while playback is active."""
        return self._playing

    def load(self, filename: str) -> None:
        """Load a ``.vgm`` or ``.vgz`` file, decompressing gzip natively.

        :param str filename: Path to the file to load.
        :raises RuntimeError: If the file is not a VGM, cannot be decompressed,
            or does not target the AY-3-8910.
        """
        with open(filename, "rb") as f:
            raw = f.read()

        # Detect gzip (VGZ) -- magic bytes 0x1F 0x8B
        if raw[0] == 0x1F and raw[1] == 0x8B:
            raw = self._gunzip(raw)

        # Check the VGM magic
        if bytes(raw[0:4]) != b"Vgm ":
            raise RuntimeError("Not a VGM file (bad magic)")

        self._data = raw
        self._parse_header()

    @staticmethod
    def _gunzip(data: bytes) -> bytes:
        """Decompress gzip (VGZ) data"""
        if zlib is None:
            raise RuntimeError(
                "Playing compressed .vgz files needs the 'zlib' module, which is "
                "not present in this build. Use an uncompressed .vgm, or a build "
                "that includes zlib."
            )
        # wbits=31 tells zlib to expect a gzip header/trailer
        return zlib.decompress(data, 31)

    def _parse_header(self) -> None:
        """Parse the VGM header and locate the command stream."""
        data = self._data

        eof_rel = struct.unpack("<I", data[0x04:0x08])[0]
        self._eof_offset = 0x04 + eof_rel if eof_rel else len(data)
        self._eof_offset = min(self._eof_offset, len(data))

        self._version = struct.unpack("<I", data[0x08:0x0C])[0]
        self._total_samples = struct.unpack("<I", data[0x18:0x1C])[0]

        loop_rel = struct.unpack("<I", data[0x1C:0x20])[0]
        self._loop_offset = (0x1C + loop_rel) if loop_rel else 0
        self._loop_samples = struct.unpack("<I", data[0x20:0x24])[0]

        # AY-3-8910 clock at offset 0x74 (VGM 1.51+)
        ay_clock = 0
        if len(data) >= 0x78:
            ay_clock = struct.unpack("<I", data[0x74:0x78])[0]

        # Mask off the top bits (flags), keep the clock value
        ay_clock &= 0x3FFFFFFF

        if ay_clock == 0:
            raise RuntimeError(
                "No AY-3-8910 clock in this VGM (offset 0x74 is 0). "
                "This file targets a different chip."
            )

        self._clock_hz = ay_clock

        if self._version >= 0x150:
            data_rel = struct.unpack("<I", data[0x34:0x38])[0]
            self._data_offset = 0x34 + data_rel if data_rel else 0x40
        else:
            self._data_offset = 0x40

        gd3_rel = struct.unpack("<I", data[0x14:0x18])[0]
        if gd3_rel:
            self._parse_gd3(0x14 + gd3_rel)

        self._pos = self._data_offset

    def _parse_gd3(self, offset: int) -> None:
        """Parse the GD3 metadata tag (UTF-16LE null-terminated strings)."""
        data = self._data
        if bytes(data[offset : offset + 4]) != b"Gd3 ":
            return

        ptr = offset + 12

        fields = []
        for _ in range(11):
            s, ptr = self._read_utf16(data, ptr)
            fields.append(s)

        if len(fields) >= 7:
            self._title = fields[0]
            self._game = fields[2]
            self._author = fields[6]

    @staticmethod
    def _read_utf16(data: bytes, offset: int) -> "Tuple[str, int]":
        """Read a UTF-16LE null-terminated string.

        :param bytes data: Buffer to read from.
        :param int offset: Byte offset to start reading at.
        :return: A ``(string, next_offset)`` tuple.
        """
        chars = []
        ptr = offset
        while ptr + 1 < len(data):
            lo = data[ptr]
            hi = data[ptr + 1]
            ptr += 2
            if lo == 0 and hi == 0:
                break
            code = lo | (hi << 8)
            if 32 <= code < 127:
                chars.append(chr(code))
            elif code >= 127:
                chars.append("?")
        return "".join(chars), ptr

    def play(self, ay: "AY8912") -> None:
        """Start playback through the AY8912 instance.

        :param ~adafruit_ay8912.ay8912_emulator.AY8912 ay: The emulator that
            register writes will be sent to. It is reset before playback.
        """
        self._ay = ay
        self._pos = self._data_offset
        self._sample_clock = 0
        self._wait_remaining = 0
        self._loop_count = 0
        self._playing = True
        self._next_time = time.monotonic()
        self._ay.reset()

    def stop(self) -> None:
        """Stop playback and reset the attached AY8912"""
        self._playing = False
        if self._ay:
            self._ay.reset()

    def update(self) -> None:
        """Process the command stream with correct timing.

        Call repeatedly in the playback loop. It tracks real time internally
        and only advances the command stream when the accumulated wait has
        elapsed.
        """
        if not self._playing or self._data is None:
            return

        now = time.monotonic()
        if now < self._next_time:
            return

        wait_samples = self._process_until_wait()

        if wait_samples < 0:
            if self._loop_offset and self._loop_samples:
                self._pos = self._loop_offset
                self._loop_count += 1
                self._sample_clock = self._total_samples - self._loop_samples
                wait_samples = 0
            else:
                self._playing = False
                return

        self._sample_clock += wait_samples
        self._next_time += wait_samples / _VGM_RATE

        self._next_time = max(self._next_time, now)

    def _process_until_wait(self) -> int:  # noqa: PLR0912
        """Execute commands until a wait.

        :return: The number of samples to wait, or ``-1`` at end of stream.
        """
        data = self._data
        ay = self._ay

        end = self._eof_offset if self._eof_offset else len(data)
        while self._pos < end:
            cmd = data[self._pos]
            self._pos += 1

            # AY-3-8910 register write: 0xA0 aa dd
            if cmd == 0xA0:
                reg = data[self._pos]
                val = data[self._pos + 1]
                self._pos += 2
                reg &= 0x0F if reg < 0x10 else 0xFF
                if reg <= 13:
                    ay.write_register(reg, val)

            # Wait n samples: 0x61 nn nn
            elif cmd == 0x61:
                n = data[self._pos] | (data[self._pos + 1] << 8)
                self._pos += 2
                return n

            # Wait 1/60 second (735 samples)
            elif cmd == 0x62:
                return 735

            # Wait 1/50 second (882 samples)
            elif cmd == 0x63:
                return 882

            # End of sound data
            elif cmd == 0x66:
                return -1

            # Wait n+1 samples (0x70-0x7F)
            elif 0x70 <= cmd <= 0x7F:
                return (cmd & 0x0F) + 1

            # --- Commands to skip (other chips / unsupported) ---

            # 0x4F dd / 0x50 dd -- SN76489 (Game Gear / SMS): 1 data byte
            elif cmd in {0x4F, 0x50}:
                self._pos += 1

            # 0x51-0x5F -- YM chips: 2 data bytes
            elif 0x51 <= cmd <= 0x5F:
                self._pos += 2

            # 0xA1-0xBF -- various chip writes: 2 data bytes
            elif 0xA1 <= cmd <= 0xBF:
                self._pos += 2

            # 0xC0-0xDF -- various: 3 data bytes
            elif 0xC0 <= cmd <= 0xDF:
                self._pos += 3

            # 0xE0-0xFF -- various: 4 data bytes
            elif 0xE0 <= cmd <= 0xFF:
                self._pos += 4

            # 0x90-0x95 -- DAC stream control (various lengths)
            elif cmd == 0x90:
                self._pos += 4
            elif cmd == 0x91:
                self._pos += 4
            elif cmd == 0x92:
                self._pos += 5
            elif cmd == 0x93:
                self._pos += 10
            elif cmd == 0x94:
                self._pos += 1
            elif cmd == 0x95:
                self._pos += 4

            # 0x67 -- data block: 0x67 0x66 tt ss ss ss ss [data]
            elif cmd == 0x67:
                self._pos += 1  # skip 0x66
                self._pos += 1  # skip the type byte
                size = struct.unpack("<I", data[self._pos : self._pos + 4])[0]
                self._pos += 4 + size

            else:
                # Unknown command
                pass
        return -1

    def __str__(self) -> str:
        title = self._title or "Untitled"
        author = self._author or "Unknown"
        return f"VGM v{self._version:X} | {title} -- {author} ({self.duration:.1f}s)"
