# SPDX-FileCopyrightText: 2026 Scott Shawcroft for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""MP3 Player Demo
* Put your albums into folders in the /sd directory
ex: /sd/Yellow Submarine
* For the album cover art, make a 240x240 bitmap
* Name the bitmap cover.bmp and put it in the album folder
ex: /sd/Yellow Submarine/cover.bmp

Left knob controls volume
Right knob changes tracks
Headphone audio output"""

import os

import audiomp3

from adafruit_yoto import Yoto

yoto = Yoto(
    default_bg=0xFF00FF,
    rotation=0,
    debug=False,
    auto_refresh=False,
)
yoto.graphics.refresh()

dac = yoto.peripherals.dac
dac.mute = True
audio = yoto.peripherals.audio
dac.volume = 160

mp3 = None
folders = os.listdir("/sd")

last_left_knob = yoto.peripherals.encoder_left_position
print("starting loop")
while True:
    for folder in folders:
        full_path = "/sd/" + folder
        if (os.stat(full_path)[0] & 0x4000) == 0:
            continue
        files = os.listdir(full_path)
        tracks = [x for x in files if x.endswith("mp3")]
        if not tracks:
            continue
        if "cover.bmp" in files:
            yoto.set_background(full_path + "/cover.bmp")
        yoto.graphics.refresh()
        # Reset right knob after showing the album art to prevent overshoot
        last_right_knob = yoto.peripherals.encoder_right_position
        print(folder)
        track = 0
        while track < len(tracks):
            file_i = track
            file = tracks[track]
            print(file_i, file)
            file = full_path + "/" + file
            if mp3 is None:
                mp3 = audiomp3.MP3Decoder(file)
            else:
                mp3.open(file)
            audio.play(mp3)
            dac.mute = False
            while audio.playing:
                # board.PACTRL.value = not board.HEADPHONE_DETECT.value
                current_left_knob = yoto.peripherals.encoder_left_position
                current_right_knob = yoto.peripherals.encoder_right_position
                if last_left_knob != current_left_knob:
                    print("left", last_left_knob, current_left_knob)
                    dac.volume = max(
                        0, min(180, dac.volume + 10 * (current_left_knob - last_left_knob))
                    )
                    print("volume", dac.volume)
                    last_left_knob = current_left_knob
                if last_right_knob != current_right_knob:
                    print("right", last_right_knob, current_right_knob)
                    track += current_right_knob - last_right_knob - 1
                    track = max(track, 0)
                    last_right_knob = current_right_knob
                    print("next", track)
                    audio.stop()
            track += 1
