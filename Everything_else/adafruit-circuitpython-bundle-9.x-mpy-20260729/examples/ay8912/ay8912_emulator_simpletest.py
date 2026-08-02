# SPDX-FileCopyrightText: Copyright (c) 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time

import audiobusio
import board

from adafruit_ay8912.ay8912_emulator import AY8912
from adafruit_ay8912.vgm_player import VGMFile

audio = audiobusio.I2SOut(board.D9, board.D10, board.D11)

# --- Load VGM/VGZ file ---
VGM_FILE = "song.vgz"  # .vgm or .vgz both work

vgm = VGMFile(VGM_FILE)

# --- Create AY8912 with the file's clock rate ---
ay = AY8912(sample_rate=22050, clock_rate=vgm.clock_hz)
ay.begin(audio)

# --- Play ---
print("Playing...")
if vgm.loops:
    print("  (song loops — will play through once then loop)")
vgm.play(ay)

STOP_AFTER_FIRST_LOOP = True
last_status = time.monotonic()

while vgm.playing:
    vgm.update()

    if STOP_AFTER_FIRST_LOOP and vgm.loop_count >= 1:
        print("  Reached loop point — stopping.")
        break

    now = time.monotonic()
    if now - last_status >= 5.0:
        last_status = now
        print(f"  {vgm.elapsed:.0f}s / {vgm.duration:.0f}s ({int(vgm.progress * 100)}%)")

ay.reset()
print("Done.")
