# SPDX-FileCopyrightText: 2023 Jeff Epler for Adafruit Industries
# SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_dang`
================================================================================

A subset of the curses framework. Used for making terminal based applications.


* Author(s): Jeff Epler, Tim Cocks

Implementation Notes
--------------------

**Hardware:**

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

"""

# imports

__version__ = "1.0.1"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_Dang.git"

import select
import sys

import terminalio

try:
    from typing import Callable

    from terminalio import Terminal
except ImportError:
    pass

try:
    import termios

    _orig_attr = None

    def _nonblocking():
        global _orig_attr
        _orig_attr = termios.tcgetattr(sys.stdin)
        attr = termios.tcgetattr(sys.stdin)
        attr[3] &= ~(termios.ECHO | termios.ICANON)
        attr[6][termios.VMIN] = 1
        attr[6][termios.VTIME] = 0
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, attr)

    def _blocking():
        if _orig_attr is not None:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, _orig_attr)

except ImportError:

    def _nonblocking():
        pass

    def _blocking():
        pass

# LINES = 24
# COLS = 80

LINES = 33
COLS = 120

special_keys = {
    "\x1b": ...,  # all prefixes of special keys must be entered as Ellipsis
    "\x1b[": ...,
    "\x1b[3": ...,
    "\x1b[5": ...,
    "\x1b[6": ...,
    "\x1b[A": "KEY_UP",
    "\x1b[B": "KEY_DOWN",
    "\x1b[C": "KEY_RIGHT",
    "\x1b[D": "KEY_LEFT",
    "\x1b[H": "KEY_HOME",
    "\x1b[F": "KEY_END",
    "\x1b[5~": "KEY_PGUP",
    "\x1b[6~": "KEY_PGDN",
    "\x1b[3~": "KEY_DELETE",
}


class Screen:
    """
    Curses based Screen class. Can output to CIRCUITPYTHON_TERMINAL or a
    terminalio.Terminal instance created by code. Supports reading input
    from ``sys.stdin``

    :param terminalio.Terminal terminal: a Terminal instance to output the
      application to. Default is None which will cause output to CIRCUITPYTHON_TERMINAL.
    """

    def __init__(self, terminal=None):
        self._poll = select.poll()
        self._poll.register(sys.stdin, select.POLLIN)
        self._pending = ""
        self._terminal = terminal

    def _sys_stdin_readable(self) -> bool:
        return hasattr(sys.stdin, "readable") and sys.stdin.readable()

    def _sys_stdout_flush(self) -> None:
        if hasattr(sys.stdout, "flush"):
            sys.stdout.flush()

    def _terminal_read_blocking(self) -> str:
        return sys.stdin.read(1)

    def _terminal_read_timeout(self, timeout: int) -> str:
        """
        read from stdin with a timeout
        :param timeout: The timeout to use in ms
        :return: The value that was read or None if timeout occurred
        """
        if self._sys_stdin_readable() or self._poll.poll(timeout):
            r = sys.stdin.read(1)
            return r
        return None

    def move(self, y: int, x: int) -> None:
        """
        Move the cursor to the specified position.
        :param y: y position to move the cursor to
        :param x: x position to move the cursor to
        :return: None
        """
        if self._terminal is not None:
            self._terminal.write(f"\033[{y + 1};{x + 1}H")
        else:
            print(end=f"\033[{y + 1};{x + 1}H")

    def erase(self) -> None:
        """
        Erase the screen.
        :return: None
        """
        if self._terminal is not None:
            self._terminal.write("\033H\033[2J")

        else:
            print(end="\033H\033[2J")

    def addstr(self, y: int, x: int, text: str) -> None:
        """
        Add text to the screen at the given location.
        :param y: y location to add the text at
        :param x: x location to add the text at
        :param text: The text to add
        :return: None
        """
        self.move(y, x)
        if self._terminal is not None:
            self._terminal.write(text)
        else:
            print(end=text)

    def getkey(self) -> str:
        """
        Get a key input from the keyboard connected to sys.stdin.

        :return: The key that was pressed as a literal string, or one of
          the values in ``special_keys``.
        """
        self._sys_stdout_flush()
        pending = self._pending
        if pending and (code := special_keys.get(pending)) is None:
            self._pending = pending[1:]
            return pending[0]

        while True:
            if pending:
                c = self._terminal_read_timeout(50)
                if c is None:
                    self._pending = pending[1:]
                    return pending[0]
            else:
                c = self._terminal_read_timeout(50)
                if c is None:
                    return None
            c = pending + c

            code = special_keys.get(c)

            if code is None:
                self._pending = c[1:]
                return c[0]
            if code is not Ellipsis:
                return code

            pending = c


def wrapper(func: Callable, *args, **kwds):
    """
    Curses wrapper function for CIRCUITPYTHON_TERMINAL output

    :param func: The application function to wrap
    :param args: The arguments to pass the application function
    :param kwds: The keyword arguments to pass the application function
    :return: None
    """
    stdscr = Screen()
    try:
        _nonblocking()
        return func(stdscr, *args, **kwds)
    finally:
        _blocking()
        stdscr.move(LINES - 1, 0)
        print("\n")


def custom_terminal_wrapper(terminal: terminalio.Terminal, func: Callable, *args, **kwds):
    """
    Curses wrapper function for terminalio.Terminal instance output
    :param terminal: The Terminal instance to output to.
    :param func: The application function to wrap
    :param args: The arguments to pass the application function
    :param kwds: The keyword arguments to pass the application function
    :return: None
    """
    stdscr = Screen(terminal)
    try:
        _nonblocking()
        return func(stdscr, *args, **kwds)
    finally:
        _blocking()
        print("\n")
