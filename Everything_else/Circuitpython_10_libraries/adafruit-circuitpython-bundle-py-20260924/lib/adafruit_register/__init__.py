# SPDX-FileCopyrightText: 2016 Scott Shawcroft for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
`adafruit_register.__init__.py`
====================================================

Package-wide definitions

* Author(s): Scott Shawcroft

Package-wide scratch buffer shared by every register descriptor module. Grow it ONLY in place
with .extend() -- never rebind it (`_BUFFER = ...`). Submodules do `from adafruit_register import
_BUFFER`, which captures this exact object; a rebind would leave them on a stale copy.
"""

_BUFFER = bytearray(1)


def _fit(size: int) -> None:
    """
    Grow the shared buffer in place to hold a 1-byte address + ``size`` data bytes.
    The register_ versions don't use the extra byte but leaving there for simplicity
    """

    if len(_BUFFER) < 1 + size:
        _BUFFER.extend(bytes(1 + size - len(_BUFFER)))
