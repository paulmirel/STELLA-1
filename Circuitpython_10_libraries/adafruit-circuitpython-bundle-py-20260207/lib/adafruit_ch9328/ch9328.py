# SPDX-FileCopyrightText: Copyright (c) 2024 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
:py:class:`~adafruit_ch9328.ch9328.Adafruit_CH9328`
================================================================================

CircuitPython driver for the CH9328 UART to HID keyboard breakout


* Author(s): Liz Clark

Implementation Notes
--------------------

**Hardware:**

* `Adafruit CH9328 UART to HID Keyboard Breakout <https://www.adafruit.com/product/5973>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

"""

from adafruit_ch9328.ch9328_keymap import Keymap

try:
    import typing

    from busio import UART
except ImportError:
    pass

__version__ = "1.0.6"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_CH9328.git"


class Adafruit_CH9328:
    """Adafruit CH9328 UART to HID keyboard driver"""

    def __init__(self, uart: UART) -> None:
        """Constructor for the Adafruit_CH9328 class."""
        self._uart = uart
        self._uart.baudrate = 9600

    def send_key_press(self, keys: typing.List[int], modifier: int = 0) -> None:
        """Sends a key press command to the CH9328 device.

        Args:
            keys (list): List of up to 6 key codes to be pressed simultaneously.
            modifier (int, optional): Modifier key code (e.g., Shift, Ctrl)
        """
        # Ensure keys has exactly 6 elements
        keys = keys + [0x00] * (6 - len(keys))
        data_packet = bytearray([modifier, 0x00] + keys[:6])
        self._write_command(data_packet)

    def _write_command(self, command: bytearray) -> None:
        """Writes a command to the CH9328 via the provided UART.

        This method is private and used internally by other methods.

        Args:
            command (bytearray): The array of bytes representing the command to be sent.
        """
        try:
            self._uart.write(command)
        except Exception as error:
            raise RuntimeError(f"Failed to write command to UART: {error}") from error

    def send_string(self, string: str) -> None:
        """Types out a string by sending key press commands for each character,
        handling upper/lower case and punctuation.

        Args:
            string (str): The string to be typed out.
        """
        no_keys_pressed = [0, 0, 0, 0, 0, 0]
        for char in string:
            modifier = self._modifier(char)
            key_code = self._key_code(char)
            keys = [key_code, 0, 0, 0, 0, 0]
            self.send_key_press(keys, modifier)
            self.send_key_press(no_keys_pressed, 0)  # Release all keys

    @staticmethod
    def _modifier(char: str) -> int:
        """Gets the modifier key required for a specific character.

        Args:
            char (str): The character for which the modifier key is determined.

        Returns:
            int: The modifier key code (0 if no modifier is needed).
        """
        if char.isupper() or char in '!@#$%^&*()_+{}|:"<>?~':
            return Keymap.LEFT_SHIFT
        return 0

    @staticmethod
    def _key_code(char: str) -> int:
        """Gets the USB HID keycode for a specific character.
        Args:
            char (str): The character to convert to a keycode.
        Returns:
            int: The corresponding keycode, or 0 if the character does not have a direct keycode.
        """
        # Mapping character to key code using ASCII values
        if char.isalpha():
            # Handle alphabetic characters with offset from 'a' or 'A'
            return Keymap.A + (ord(char.lower()) - ord("a"))
        if char.isdigit():
            # Handle numeric characters; numbers are continuous in ASCII from '0' to '9'
            return Keymap.ZERO if char == "0" else (Keymap.ONE + (ord(char) - ord("1")))
        # Handle punctuation and special characters explicitly
        return {
            " ": Keymap.SPACE,
            "!": Keymap.ONE,  # Shift is handled by get_modifier
            "@": Keymap.TWO,  # Shift is handled by get_modifier
            "#": Keymap.THREE,  # Shift is handled by get_modifier
            "$": Keymap.FOUR,  # Shift is handled by get_modifier
            "%": Keymap.FIVE,  # Shift is handled by get_modifier
            "^": Keymap.SIX,  # Shift is handled by get_modifier
            "&": Keymap.SEVEN,  # Shift is handled by get_modifier
            "*": Keymap.EIGHT,  # Shift is handled by get_modifier
            "(": Keymap.NINE,  # Shift is handled by get_modifier
            ")": Keymap.ZERO,  # Shift is handled by get_modifier
            "-": Keymap.MINUS,
            "_": Keymap.MINUS,  # Shift is handled by get_modifier
            "=": Keymap.EQUAL,
            "+": Keymap.EQUAL,  # Shift is handled by get_modifier
            "[": Keymap.LEFT_BRACE,
            "{": Keymap.LEFT_BRACE,  # Shift is handled by get_modifier
            "]": Keymap.RIGHT_BRACE,
            "}": Keymap.RIGHT_BRACE,  # Shift is handled by get_modifier
            "\\": Keymap.BACKSLASH,
            "|": Keymap.BACKSLASH,  # Shift is handled by get_modifier
            ";": Keymap.SEMICOLON,
            ":": Keymap.SEMICOLON,  # Shift is handled by get_modifier
            "'": Keymap.QUOTE,
            '"': Keymap.QUOTE,  # Shift is handled by get_modifier
            ",": Keymap.COMMA,
            "<": Keymap.COMMA,  # Shift is handled by get_modifier
            ".": Keymap.PERIOD,
            ">": Keymap.PERIOD,  # Shift is handled by get_modifier
            "/": Keymap.SLASH,
            "?": Keymap.SLASH,  # Shift is handled by get_modifier
            "`": Keymap.TILDE,
            "~": Keymap.TILDE,  # Shift is handled by get_modifier
        }.get(char, 0)  # Return 0 if no valid keycode
