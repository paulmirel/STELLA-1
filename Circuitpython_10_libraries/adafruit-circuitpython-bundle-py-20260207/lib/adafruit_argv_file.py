# SPDX-FileCopyrightText: Copyright (c) 2025 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_argv_file`
================================================================================

Pass arguments to other python code files by writing them to a file before launching.


* Author(s): Tim Cocks

Implementation Notes
--------------------

**Hardware:**

Device must have CPSAVES or other writeable storage in order to use the library.

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads


"""

# imports
import json
import os

from adafruit_pathlib import Path

__version__ = "1.0.1"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_Argv_File.git"

try:
    from typing import Optional
except ImportError:
    pass


def argv_filename(python_code_filepath: str, file_location: str = "/saves/"):
    """
    Format a python code file path into its temporary argv filename.

    :param python_code_filepath: The path to the python code file.
    :param file_location: The location to write the argv file. Location
        must be mounted as writeable.
    :return: The argv filename.
    """
    path = Path(python_code_filepath)
    return f"{file_location}.{path.absolute().replace("/", "_")}.argv"


def read_argv(python_code_filepath: str, file_location: str = "/saves/") -> Optional[list]:
    """
    Read the argv file and return the values from it as a list. Deletes the argv file after
    reading so that the same values won't be re-used multiple times.

    :param python_code_filepath: The path to the python code file to read the argv file for.
    :param file_location: The location to read the argv file from.
    :return: List of values read from the argv file or None if the argv file wasn't read.
    """
    try:
        arg_file = argv_filename(python_code_filepath)
        with open(arg_file) as f:
            args = json.load(f)
        os.remove(arg_file)
        return args
    except OSError:
        # argv file not found
        return None
    except ValueError:
        # JSON syntax error
        os.remove(arg_file)
        return None


def write_argv(
    python_code_filepath: str, argument_list: list, file_location: str = "/saves/"
) -> None:
    """
    Write a list of values into an argv file for a specified python code file.

    :param python_code_filepath: The path to the python code file to write the argv file for.
    :param argument_list: The list of argument values to write.
    :param file_location: The location to write the argv file to. Location must be mounted as
        writeable.
    :return: None
    """
    arg_file = argv_filename(python_code_filepath, file_location=file_location)
    with open(arg_file, "w") as f:
        json.dump(argument_list, f)
