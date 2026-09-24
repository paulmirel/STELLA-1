# SPDX-FileCopyrightText: Copyright (c) 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
:py:class:`~adafruit_ay8912.ay8912_emulator.AY8912`
================================================================================

AY-3-8910 / AY-8912 emulator for CircuitPython with :py:mod:`synthio`.

Translates AY-3-8910 register writes into ``synthio.Note`` property updates. Three
synthesizers (one per channel) feed an :py:class:`audiomixer.Mixer` for
per-channel volume and stereo panning.

* Author(s): Liz Clark

Implementation Notes
--------------------

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads
"""

import array
from random import randint

import audiomixer
import synthio
import ulab.numpy as np

try:
    from typing import Tuple
except ImportError:
    pass

__version__ = "1.0.0"
__repo__ = "https://github.com/your-org/Adafruit_CircuitPython_AY8912_Emulator.git"


class AY8912:
    """AY-3-8910 / AY-8912 emulator backed by :py:mod:`synthio`.

    :param int sample_rate: Output sample rate in Hz.
    :param int clock_rate: AY chip clock frequency in Hz. Defaults to the ZX
        Spectrum 128K clock (1773400 Hz).
    :param int waveform_size: Number of samples in the square waveform.
    :param int noise_size: Number of samples in the noise waveform.
    :param int volume: Peak sample amplitude used when building the waveforms.
    """

    # AY DAC volume table -- 16 levels
    DAC = (
        0.0,
        0.00999,
        0.01445,
        0.02106,
        0.03070,
        0.04555,
        0.06450,
        0.10736,
        0.12659,
        0.20499,
        0.29221,
        0.37284,
        0.49253,
        0.63532,
        0.80558,
        1.0,
    )

    # Envelope segment functions per shape: (segment0, segment1)
    # 0=decay (start high), 1=attack (start low), 2=hold, 3=hold-alt
    _ENV_SEG = (
        (0, 2),
        (0, 2),
        (0, 2),
        (0, 2),  # shapes 0-3:   \___
        (1, 2),
        (1, 2),
        (1, 2),
        (1, 2),  # shapes 4-7:   /|__
        (0, 0),
        (0, 2),
        (0, 1),
        (0, 3),  # shapes 8-11:  \\\\  \___  \/\/  \^^^
        (1, 1),
        (1, 3),
        (1, 0),
        (1, 2),  # shapes 12-15: ////  /^^^  /\/\  /|__
    )

    def __init__(
        self,
        sample_rate: int = 22050,
        clock_rate: int = 1773400,
        waveform_size: int = 256,
        noise_size: int = 256,
        volume: int = 32000,
    ) -> None:
        self._clock = clock_rate
        self._sample_rate = sample_rate

        self._regs = bytearray(16)

        self._square = array.array(
            "h",
            [volume] * (waveform_size // 2) + [-volume] * (waveform_size // 2),
        )
        self._noise = np.array(
            [randint(-volume, volume) for _ in range(noise_size)],
            dtype=np.int16,
        )

        self._synths = []
        self._notes = []
        for _ in range(3):
            s = synthio.Synthesizer(sample_rate=sample_rate, channel_count=2)
            n = synthio.Note(
                frequency=440.0,
                waveform=self._square,
                amplitude=1.0,
            )
            s.press(n)
            self._synths.append(s)
            self._notes.append(n)

        self._mixer = audiomixer.Mixer(
            voice_count=3,
            sample_rate=sample_rate,
            channel_count=2,
            buffer_size=2048,
        )

        self._started = False

        self._tone_on = [False, False, False]
        self._noise_on = [False, False, False]
        self._env_enabled = [False, False, False]

        self._env_shape = 0
        self._env_period = 1
        self._env_level = 0  # 0..31
        self._env_segment = 0  # 0 or 1
        self._env_accumulator = 0.0
        self._env_steps_per_tick = 0.0
        self._compute_env_rate()

    @property
    def mixer(self) -> "audiomixer.Mixer":
        """The :py:class:`audiomixer.Mixer`. Connect to audio output
        with ``audio.play(ay.mixer)`` (or just call :meth:`begin`)."""
        return self._mixer

    def begin(self, audio_out) -> None:
        """Begin audio signal chain.

        Handles ``audio_out.play(mixer)`` first, then connects the synth voices::

            ay = AY8912(sample_rate=22050)
            ay.begin(audio)

        :param audio_out: The audio output object
        """
        audio_out.play(self._mixer)

        for i in range(3):
            self._mixer.voice[i].play(self._synths[i], loop=True)
            self._mixer.voice[i].level = 0.0

        # Default ACB stereo panning
        self._mixer.voice[0].panning = -0.4  # A -> left
        self._mixer.voice[1].panning = 0.0  # B -> center
        self._mixer.voice[2].panning = 0.4  # C -> right

        self._started = True

    @property
    def notes(self) -> "Tuple[synthio.Note, ...]":
        """Direct access to the three ``synthio.Note`` objects (read-only
        tuple)."""
        return tuple(self._notes)

    def read_register(self, reg: int) -> int:
        """Read an AY register.

        :param int reg: Register index (0-15).
        :return: The stored register value, or 0 if ``reg`` is out of range.
        """
        if reg > 15:
            return 0
        return self._regs[reg]

    def write_register(self, reg: int, value: int) -> None:
        """Write an AY register (0-13). R14/R15 (I/O ports) are stored but
        otherwise ignored.

        :param int reg: Register index (0-15). Out-of-range writes are ignored.
        :param int value: Byte value to write (masked to 0-255).
        """
        if reg > 15:
            return
        value &= 0xFF
        self._regs[reg] = value
        self._apply_reg(reg)

    def set_pan(self, channel: int, pan: float) -> None:
        """Stereo panning for a channel.

        :param int channel: Channel index (0-2).
        :param float pan: Pan position: ``-1.0`` = hard left, ``0.0`` = center,
            ``1.0`` = hard right. Values are clamped to that range.
        """
        if 0 <= channel <= 2:
            self._mixer.voice[channel].panning = max(-1.0, min(1.0, pan))

    def set_tone_period(self, channel: int, period: int) -> None:
        """The 12-bit tone period directly (R0/R1, R2/R3, R4/R5).

        :param int channel: Channel index (0-2).
        :param int period: Tone period, clamped to 1-4095.
        """
        if channel > 2:
            return
        period = max(1, min(4095, period))
        r = channel * 2
        self.write_register(r, period & 0xFF)
        self.write_register(r + 1, (period >> 8) & 0x0F)

    def set_noise_period(self, period: int) -> None:
        """The 5-bit noise period (R6).

        :param int period: Noise period (only the low 5 bits are used).
        """
        self.write_register(6, period & 0x1F)

    def set_volume(self, channel: int, volume: int, envelope: bool = False) -> None:
        """Set a channel's volume (R8/R9/R10).

        :param int channel: Channel index (0-2).
        :param int volume: Fixed volume level (0-15).
        :param bool envelope: If ``True``, the hardware envelope controls the
            channel volume instead of the fixed level.
        """
        if channel > 2:
            return
        val = min(15, volume) & 0x0F
        if envelope:
            val |= 0x10
        self.write_register(8 + channel, val)

    def enable_tone(self, channel: int, enable: bool = True) -> None:
        """Enable or disable tone output for a channel via the mixer (R7).

        :param int channel: Channel index (0-2).
        :param bool enable: ``True`` to enable tone, ``False`` to disable.
        """
        if channel > 2:
            return
        bit = 1 << channel
        mixer = self._regs[7]
        if enable:
            mixer &= ~bit  # bit=0 means ON in the AY mixer
        else:
            mixer |= bit
        self.write_register(7, mixer)

    def enable_noise(self, channel: int, enable: bool = True) -> None:
        """Enable or disable noise output for a channel via the mixer (R7).

        :param int channel: Channel index (0-2).
        :param bool enable: ``True`` to enable noise, ``False`` to disable.
        """
        if channel > 2:
            return
        bit = 1 << (channel + 3)
        mixer = self._regs[7]
        if enable:
            mixer &= ~bit
        else:
            mixer |= bit
        self.write_register(7, mixer)

    def set_envelope(self, period: int, shape: int) -> None:
        """Set the envelope period (R11/R12) and shape (R13).

        Writing R13 resets the envelope generator.

        :param int period: 16-bit envelope period.
        :param int shape: Envelope shape (0-15).
        """
        self.write_register(11, period & 0xFF)
        self.write_register(12, (period >> 8) & 0xFF)
        self.write_register(13, shape & 0x0F)

    def reset(self) -> None:
        """Reset all registers and state to power-on defaults."""
        self._regs = bytearray(16)
        self._env_level = 0
        self._env_segment = 0
        self._env_shape = 0
        self._env_period = 1
        self._env_accumulator = 0.0
        self._compute_env_rate()

        for ch in range(3):
            self._notes[ch].frequency = 440.0
            self._notes[ch].amplitude = 1.0
            self._notes[ch].waveform = self._square
            self._notes[ch].ring_waveform = None
            self._mixer.voice[ch].level = 0.0
            self._tone_on[ch] = False
            self._noise_on[ch] = False
            self._env_enabled[ch] = False

    def tick(self) -> None:
        """Advance the envelope generator.

        Call this at ~50 Hz from your main loop or a timer interrupt.
        """
        self._env_accumulator += self._env_steps_per_tick
        while self._env_accumulator >= 1.0:
            self._env_accumulator -= 1.0
            self._step_envelope()

        for ch in range(3):
            if self._env_enabled[ch]:
                self._apply_volume(ch)

    def _apply_reg(self, reg: int) -> None:
        """React to a register write."""
        if reg <= 5:
            # Tone period (R0/R1 -> ch0, R2/R3 -> ch1, R4/R5 -> ch2)
            ch = reg // 2
            self._update_channel_freq(ch)

        elif reg == 6:
            # Noise period -- update noise frequency on relevant channels
            self._update_mixer_state()

        elif reg == 7:
            # Mixer enable bits
            self._update_mixer_state()

        elif 8 <= reg <= 10:
            # Volume / envelope-enable
            ch = reg - 8
            vreg = self._regs[reg]
            self._env_enabled[ch] = bool(vreg & 0x10)
            self._apply_volume(ch)

        elif reg in {11, 12}:
            # Envelope period
            self._env_period = self._regs[11] | (self._regs[12] << 8)
            self._env_period = max(self._env_period, 1)
            self._compute_env_rate()

        elif reg == 13:
            # Envelope shape -- reset envelope generator
            self._env_shape = self._regs[13] & 0x0F
            self._env_segment = 0
            self._env_accumulator = 0.0
            self._env_reset_segment()
            self._compute_env_rate()

    def _period_to_hz(self, period: int) -> float:
        """Convert an AY tone/noise period to Hz, clamped to synthio's valid
        range of 0-32767 Hz."""
        period = max(period, 1)
        freq = self._clock / (16.0 * period)
        freq = min(freq, 32767.0)
        freq = max(freq, 1.0)
        return freq

    def _update_channel_freq(self, ch: int) -> None:
        """Set a note's frequency from the current tone registers, but only if
        tone is active on that channel."""
        if self._tone_on[ch]:
            lo = self._regs[ch * 2]
            hi = self._regs[ch * 2 + 1] & 0x0F
            period = lo | (hi << 8)
            period = max(period, 1)
            self._notes[ch].frequency = self._period_to_hz(period)

    def _update_mixer_state(self) -> None:
        """Read the mixer register (R7) and update waveforms & frequencies."""
        mixer_reg = self._regs[7]
        noise_period = self._regs[6] & 0x1F
        noise_period = max(noise_period, 1)
        noise_hz = self._period_to_hz(noise_period)

        for ch in range(3):
            tone_on = not bool(mixer_reg & (1 << ch))
            noise_on = not bool(mixer_reg & (1 << (ch + 3)))

            self._tone_on[ch] = tone_on
            self._noise_on[ch] = noise_on

            if tone_on and noise_on:
                self._notes[ch].waveform = self._square
                self._notes[ch].ring_waveform = self._noise
                self._notes[ch].ring_frequency = noise_hz
                self._update_channel_freq(ch)

            elif tone_on:
                self._notes[ch].waveform = self._square
                self._notes[ch].ring_waveform = None
                self._update_channel_freq(ch)

            elif noise_on:
                self._notes[ch].waveform = self._noise
                self._notes[ch].ring_waveform = None
                self._notes[ch].frequency = noise_hz

            self._apply_volume(ch)

    def _apply_volume(self, ch: int) -> None:
        """Set the mixer voice level for a channel based on current state."""
        # If the channel is fully off (no tone, no noise), silence it
        if not self._tone_on[ch] and not self._noise_on[ch]:
            self._mixer.voice[ch].level = 0.0
            return

        if self._env_enabled[ch]:
            # Envelope: 0-31 mapped to the 16-entry DAC (pairs)
            self._mixer.voice[ch].level = self.DAC[self._env_level >> 1]
        else:
            vol = self._regs[8 + ch] & 0x0F
            self._mixer.voice[ch].level = self.DAC[vol]

    def _compute_env_rate(self) -> None:
        """Compute how many envelope steps to advance per 50 Hz tick."""
        # The AY envelope steps once per (256 * period) clock cycles:
        #   steps_per_second = clock / (256 * period)
        #   steps_per_tick   = steps_per_second / 50
        self._env_steps_per_tick = self._clock / (256.0 * self._env_period * 50.0)

    def _env_reset_segment(self) -> None:
        """Set the envelope level to the starting value for the current
        segment."""
        func = self._ENV_SEG[self._env_shape][self._env_segment & 1]
        # Decay (0) and hold-alt (3) start at max; attack (1) and hold (2)
        # start at 0.
        self._env_level = 31 if func in {0, 3} else 0

    def _step_envelope(self) -> None:
        """Advance the envelope by one step."""
        func = self._ENV_SEG[self._env_shape][self._env_segment & 1]
        if func == 0:  # Decay
            self._env_level -= 1
            if self._env_level < 0:
                self._env_segment ^= 1
                self._env_reset_segment()
        elif func == 1:  # Attack
            self._env_level += 1
            if self._env_level > 31:
                self._env_segment ^= 1
                self._env_reset_segment()
        # func 2 & 3 = hold -- do nothing
