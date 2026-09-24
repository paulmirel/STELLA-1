# SPDX-FileCopyrightText: 2026 Pedro Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""Listen for mesh broadcast messages and print them."""

import adafruit_rfm9x
import board
import digitalio

import adafruit_meshfruit

FREQUENCY = 906.875
CHANNEL_HASH = 0x08
SYNC_WORD_REG = 0x39
SYNC_WORD = 0x2B

rfm9x = adafruit_rfm9x.RFM9x(
    board.SPI(),
    digitalio.DigitalInOut(board.D11),
    digitalio.DigitalInOut(board.D12),
    FREQUENCY,
)
rfm9x.signal_bandwidth = 250000
rfm9x.spreading_factor = 11
rfm9x.coding_rate = 5
rfm9x.preamble_length = 16
rfm9x.enable_crc = True
rfm9x._write_u8(SYNC_WORD_REG, SYNC_WORD)  # noqa: SLF001

mesh = adafruit_meshfruit.Meshtastic_Compatible()

print("listening on", FREQUENCY, "MHz")

while True:
    raw = rfm9x.receive(with_header=True, timeout=5.0)
    if raw is None:
        continue
    if len(raw) <= adafruit_meshfruit.HEADER_LEN:
        continue

    packet = mesh.decode(raw)
    if packet.channel_hash != CHANNEL_HASH:
        continue

    if packet.portnum == adafruit_meshfruit.PORT_TEXT_MESSAGE and packet.payload:
        print(packet.sender_id, packet.text)
