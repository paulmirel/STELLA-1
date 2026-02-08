# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
`adafruit_yoto.peripherals`
================================================================================

Helper Library for the Yoto Players


* Author(s): Liz Clark

Implementation Notes
--------------------

**Hardware:**

* Yoto Mini Player running CircuitPython

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://github.com/adafruit/circuitpython/releases

* Adafruit's PortalBase library: https://github.com/adafruit/Adafruit_CircuitPython_PortalBase

"""

import time

import audiobusio
import board
import busio
import rotaryio
from adafruit_pcf8563.pcf8563 import PCF8563

from adafruit_yoto.cr95hf import CR95HF
from adafruit_yoto.es8156 import ES8156
from adafruit_yoto.sgm41513 import SGM41513

__version__ = "1.0.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_YotoPlayer.git"


class Peripherals:  # noqa: PLR0904
    """Peripherals Helper Class for the Yoto Mini Library

    Provides access to:
    - NFC/RFID reader (CR95HF)
    - I2S DAC (ES8156) and audio playback
    - Battery charger (SGM41513)
    - RTC (PCF8563)
    - Two rotary encoders with buttons
    - IOExpander control pins
    """

    def __init__(self):
        """Initialize all Yoto Mini peripherals"""

        # I2C bus (shared by multiple peripherals)
        self._i2c = board.I2C()

        # Initialize IOExpander control pins
        self._init_control_pins()

        # Initialize NFC reader
        self._nfc = None
        try:
            uart = busio.UART(
                board.NFC_IN, board.NFC_OUT, baudrate=57600, bits=8, stop=2, timeout=0.1
            )
            self._nfc = CR95HF(uart)
        except Exception as e:
            print(f"Warning: NFC initialization failed: {e}")

        # Initialize audio DAC and I2S
        self._audio = None
        self._dac = None
        try:
            self._dac = ES8156(self._i2c, address=0x08)
            self._dac.configure(use_sclk_as_mclk=False)

            self._audio = audiobusio.I2SOut(
                board.I2S_BCLK, board.I2S_WORD_SELECT, board.I2S_DOUT, main_clock=board.I2S_MCLK
            )

            self._dac.volume = 150
            self._dac.mute = False
        except Exception as e:
            print(f"Warning: Audio initialization failed: {e}")

        # Initialize battery charger
        self._battery = None
        try:
            self._battery = SGM41513(self._i2c, address=0x1A)
        except Exception as e:
            print(f"Warning: Battery charger initialization failed: {e}")

        # Initialize RTC
        self._rtc = None
        try:
            self._rtc = PCF8563(self._i2c)
        except Exception as e:
            print(f"Warning: RTC initialization failed: {e}")

        # Initialize rotary encoders
        self._encoder_left = None
        self._encoder_right = None
        self._encoder_left_last_position = 0
        self._encoder_right_last_position = 0

        try:
            self._encoder_left = rotaryio.IncrementalEncoder(board.ENC1A, board.ENC1B)
            self._encoder_left_last_position = self._encoder_left.position

            self._encoder_right = rotaryio.IncrementalEncoder(board.ENC2A, board.ENC2B)
            self._encoder_right_last_position = self._encoder_right.position
        except Exception as e:
            print(f"Warning: Encoder initialization failed: {e}")

    def _init_control_pins(self):
        """Initialize IOExpander control pins"""
        self._pactrl = board.PACTRL
        self._level_converter = board.LEVEL_CONVERTER
        self._level_power_enable = board.LEVEL_POWER_ENABLE
        self._level_vinhold = board.LEVEL_VINHOLD
        self._headphone_detect = board.HEADPHONE_DETECT
        self._plug_status = board.PLUG_STATUS
        self._charge_status_pin = board.CHARGE_STATUS
        self._power_button = board.POWER_BUTTON
        self._tilt = board.TILT

        try:
            self._rtc_int = board.RTC_INT
        except AttributeError:
            self._rtc_int = None

    # NFC Properties
    @property
    def nfc(self):
        """Access the CR95HF NFC reader directly"""
        return self._nfc

    def read_nfc_tag(self):
        """Read an NFC tag if present. Returns (uid_bytes, sak_byte) or (None, None)"""
        if self._nfc is None:
            return None, None
        try:
            return self._nfc.read_tag()
        except (TimeoutError, OSError):
            return None, None

    def get_card_type(self, sak):
        """Get card type description from SAK byte"""
        if self._nfc is None:
            return "NFC not initialized"
        return self._nfc.card_type(sak)

    # Audio Properties
    @property
    def audio(self):
        """Access the I2SOut audio interface directly"""
        return self._audio

    @property
    def dac(self):
        """Access the ES8156 DAC directly"""
        return self._dac

    @property
    def volume(self):
        """Get/set the audio volume (0-255)"""
        if self._dac is None:
            return 0
        return self._dac.volume

    @volume.setter
    def volume(self, value):
        if self._dac is not None:
            self._dac.volume = max(0, min(255, value))

    @property
    def mute(self):
        """Get/set the mute state (True=muted, False=unmuted)"""
        if self._dac is None:
            return True
        return self._dac.mute

    @mute.setter
    def mute(self, value):
        if self._dac is not None:
            self._dac.mute = value

    def play(self, audio_sample, loop=False):
        """Play an audio sample"""
        if self._audio is not None:
            self._audio.play(audio_sample, loop=loop)

    def stop(self):
        """Stop audio playback"""
        if self._audio is not None:
            self._audio.stop()

    @property
    def playing(self):
        """Whether audio is currently playing"""
        if self._audio is None:
            return False
        return self._audio.playing

    # Battery Properties
    @property
    def battery(self):
        """Access the SGM41513 battery charger directly"""
        return self._battery

    @property
    def charge_status(self):
        """Get current battery and charging status"""
        if self._battery is None:
            return None
        return self._battery.system_status

    @property
    def charge_voltage(self):
        """Get the charge voltage setting in mV"""
        if self._battery is None:
            return None
        return self._battery.charge_voltage

    @property
    def charge_current(self):
        """Get the charge current setting in mA"""
        if self._battery is None:
            return None
        return self._battery.charge_current

    @property
    def charging(self):
        """Whether the battery is currently charging"""
        if self._battery is None:
            return False
        status = self._battery.system_status
        return status["charge_stat_code"] in {1, 2}

    @property
    def charge_complete(self):
        """Whether charging is complete"""
        if self._battery is None:
            return False
        status = self._battery.system_status
        return status["charge_stat_code"] == 3

    # RTC Properties
    @property
    def rtc(self):
        """Access the PCF8563 RTC directly"""
        return self._rtc

    @property
    def datetime(self):
        """Get/set the RTC datetime as time.struct_time"""
        if self._rtc is None:
            return None
        return self._rtc.datetime

    @datetime.setter
    def datetime(self, value):
        if self._rtc is not None:
            self._rtc.datetime = value

    @property
    def rtc_valid(self):
        """Whether the RTC has valid time (not compromised)"""
        if self._rtc is None:
            return False
        return not self._rtc.datetime_compromised

    # Encoder Properties
    @property
    def encoder_left(self):
        """Access encoder 1 directly"""
        return self._encoder_left

    @property
    def encoder_right(self):
        """Access encoder 2 directly"""
        return self._encoder_right

    @property
    def encoder_left_position(self):
        """Get the current position of encoder 1"""
        if self._encoder_left is None:
            return 0
        return self._encoder_left.position

    @property
    def encoder_right_position(self):
        """Get the current position of encoder 2"""
        if self._encoder_right is None:
            return 0
        return self._encoder_right.position

    @property
    def encoder_left_button(self):
        """Whether encoder 1 button is pressed (True=pressed)"""
        return board.ENC1_BUTTON.value

    @property
    def encoder_right_button(self):
        """Whether encoder 2 button is pressed (True=pressed)"""
        return board.ENC2_BUTTON.value

    # IOExpander Pin Properties
    @property
    def headphone_detect(self):
        """Headphone jack detection pin state"""
        return self._headphone_detect.value if self._headphone_detect else None

    @property
    def plug_status(self):
        """USB plug status pin state"""
        return self._plug_status.value if self._plug_status else None

    @property
    def charge_status_pin(self):
        """Charge status pin state"""
        return self._charge_status_pin.value if self._charge_status_pin else None

    @property
    def power_button(self):
        """Power button state"""
        return self._power_button.value if self._power_button else None

    @property
    def tilt(self):
        """Tilt sensor state"""
        return self._tilt.value if self._tilt else None

    @property
    def rtc_interrupt(self):
        """RTC interrupt pin state (if available)"""
        return self._rtc_int.value if self._rtc_int else None

    @property
    def pactrl(self):
        """Power amplifier control pin"""
        return self._pactrl

    @property
    def level_converter(self):
        """Level converter control pin"""
        return self._level_converter

    @property
    def level_power_enable(self):
        """Level shifter power enable pin"""
        return self._level_power_enable

    @property
    def level_vinhold(self):
        """Level shifter VINHOLD pin"""
        return self._level_vinhold

    def deinit(self):
        """Deinitialize all peripherals and release hardware resources"""
        if self._audio is not None:
            self._audio.stop()
            self._audio.deinit()

        if self._dac is not None:
            self._dac.mute = True

        if self._nfc is not None:
            self._nfc.field_off()

        if self._encoder_left is not None:
            self._encoder_left.deinit()

        if self._encoder_right is not None:
            self._encoder_right.deinit()
