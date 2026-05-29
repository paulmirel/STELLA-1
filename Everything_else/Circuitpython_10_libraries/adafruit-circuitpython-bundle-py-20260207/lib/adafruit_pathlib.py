# SPDX-FileCopyrightText: Copyright (c) 2013, 2014 micropython-lib contributors
# SPDX-FileCopyrightText: Copyright (c) 2025 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_pathlib`
================================================================================

Subset of the CPython module pathlib


* Author(s): micropython-lib contributors, Tim Cocks

Implementation Notes
--------------------

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

"""

# imports

__version__ = "1.0.3"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_Pathlib.git"

import errno
import os

import storage
from micropython import const

_SEP = const("/")


def _mode_if_exists(path):
    try:
        return os.stat(path)[0]
    except OSError as e:
        if e.errno == errno.ENOENT:
            return 0
        raise e


def _clean_segment(segment):
    segment = str(segment)
    if not segment:
        return "."
    segment = segment.rstrip(_SEP)
    if not segment:
        return _SEP
    while True:
        no_double = segment.replace(_SEP + _SEP, _SEP)
        if no_double == segment:
            break
        segment = no_double
    return segment


class Path:
    def __init__(self, *segments):
        segments_cleaned = []
        for segment in segments:
            segment = _clean_segment(segment)  # noqa: PLW2901, for loop var overwritten
            if segment[0] == _SEP:
                segments_cleaned = [segment]
            elif segment == ".":
                continue
            else:
                segments_cleaned.append(segment)

        self._path = _clean_segment(_SEP.join(segments_cleaned))

    def __truediv__(self, other):
        return Path(self._path, str(other))

    def __rtruediv__(self, other):
        return Path(other, self._path)

    def __repr__(self):
        return f'{type(self).__name__}("{self._path}")'

    def __str__(self):
        return self._path

    def __eq__(self, other):
        return self.absolute() == Path(other).absolute()

    def absolute(self):
        """
        Absolute path
        """
        path = self._path
        cwd = os.getcwd()
        if not path or path == ".":
            return cwd
        if path[0] == _SEP:
            return path
        return _SEP + path if cwd == _SEP else cwd + _SEP + path

    def resolve(self):
        """
        Absolute path
        """
        return self.absolute()

    def open(self, mode="r", encoding=None):
        """
        Open a file from the path.
        :param mode: The mode to open the file in
        :param encoding: The encoding to use
        :return: an opened file handle
        """
        return open(self._path, mode, encoding=encoding)

    def exists(self):
        """
        :return: True if the path exists
        """
        return bool(_mode_if_exists(self._path))

    def mkdir(self, parents=False, exist_ok=False):
        """
        Make a directory
        :param parents:
        :param exist_ok:
        :return:
        """
        try:
            os.mkdir(self._path)
            return
        except OSError as e:
            if e.errno == errno.EEXIST and exist_ok:
                return
            elif e.errno == errno.ENOENT and parents:
                pass  # handled below
            else:
                raise e

        segments = self._path.split(_SEP)
        progressive_path = ""
        if not segments[0]:
            segments = segments[1:]
            progressive_path = _SEP
        for segment in segments:
            progressive_path += _SEP + segment
            try:
                os.mkdir(progressive_path)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise e

    def is_dir(self):
        """
        :return: True if the path is a directory.
        """
        return bool(_mode_if_exists(self._path) & 0x4000)

    def is_file(self):
        """
        :return: True if the path is a file.
        """
        return bool(_mode_if_exists(self._path) & 0x8000)

    @staticmethod
    def _get_mount_for(path):
        if len(path) > 1:
            path = path.rstrip("/")

        if path[0] != "/":
            path = os.getcwd() + "/" + path
        while len(path) > 0:
            try:
                return storage.getmount(path)
            except OSError:
                pos = path.rfind("/") + 1
                path = path[:pos]
        return None

    def _glob(self, path, pattern, recursive):
        # Currently only supports a single "*" pattern.
        n_wildcards = pattern.count("*")
        n_single_wildcards = pattern.count("?")

        if n_single_wildcards:
            raise NotImplementedError("? single wildcards not implemented.")

        if n_wildcards == 0:
            raise ValueError("Must have exactly one wildcard")
        elif n_wildcards > 1:
            raise NotImplementedError("Multiple * wildcards not implemented.")

        prefix, suffix = pattern.split("*")
        path_mount = Path._get_mount_for(path)
        for name, mode, *_ in path_mount.ilistdir(path):
            full_path = path + _SEP + name
            if name.startswith(prefix) and name.endswith(suffix):
                yield full_path
            if recursive and mode & 0x4000:  # is_dir
                yield from self._glob(full_path, pattern, recursive=recursive)

    def glob(self, pattern):
        """Iterate over this subtree and yield all existing files (of any
        kind, including directories) matching the given relative pattern.

        Currently only supports a single "*" pattern.
        """
        return self._glob(self._path, pattern, recursive=False)

    def rglob(self, pattern):
        """
        Recursive glob
        """
        return self._glob(self._path, pattern, recursive=True)

    def stat(self):
        """
        File status
        :return: the file_status object for the path
        """
        return os.stat(self._path)

    def read_bytes(self):
        """
        Read bytes from the file at the path
        :return: the bytes read
        """
        with open(self._path, "rb") as f:
            return f.read()

    def read_text(self, encoding=None):
        """
        Read text from the file at the path
        :param encoding: encoding to use
        :return: the text read
        """
        with open(self._path, encoding=encoding) as f:
            return f.read()

    def rename(self, target):
        """
        Rename the file at the path
        :param target: new name
        :return: None
        """
        os.rename(self._path, target)

    def rmdir(self):
        """
        Remove the directory at the path
        :return: None
        """
        os.rmdir(self._path)

    def touch(self, exist_ok=True):
        """
        Touch the file at the path
        """
        if self.exists():
            if exist_ok:
                return  # TODO: should update timestamp
            else:
                # In lieue of FileExistsError
                raise OSError(errno.EEXIST)
        with open(self._path, "w"):
            pass

    def unlink(self, missing_ok=False):
        """
        Remove (delete) the file at the path. The name unlink was traditionally
        used by Unix.
        """
        try:
            os.unlink(self._path)
        except OSError as e:
            if not (missing_ok and e.errno == errno.ENOENT):
                raise e

    def write_bytes(self, data):
        """
        Write bytes to the file at the path
        :param data: the bytes to write
        :return: None
        """
        with open(self._path, "wb") as f:
            f.write(data)

    def write_text(self, data, encoding=None):
        """
        Write text to the file at the path
        :param data: the text to write
        :param encoding: the encoding to use
        :return: None
        """
        with open(self._path, "w", encoding=encoding) as f:
            f.write(data)

    def with_suffix(self, suffix):
        """
        :param suffix: the new suffix to use
        :return: Return a new path with the suffix changed.
        """
        index = -len(self.suffix) or None
        return Path(self._path[:index] + suffix)

    @property
    def stem(self):
        """

        :return: The stem of the path
        """
        return self.name.rsplit(".", 1)[0]

    @property
    def parent(self):
        """
        The parent of the path
        """
        tokens = self._path.rsplit(_SEP, 1)
        if len(tokens) == 2:
            if not tokens[0]:
                tokens[0] = _SEP
            return Path(tokens[0])
        return Path(".")

    @property
    def name(self):
        """
        :return: The name of the file at the path
        """
        return self._path.rsplit(_SEP, 1)[-1]

    @property
    def suffix(self):
        """
        The suffix of the file at the path
        """
        elems = self._path.rsplit(".", 1)
        return "" if len(elems) == 1 else "." + elems[1]

    def iterdir(self):
        """Iterate over the files in this directory.

        Yields Path objects for the contents of the directory.
        Does not yield entries for '.' and '..'.

        Raises:
            OSError: If self.is_dir() is False.
        """
        if not self.is_dir():
            raise OSError(f"Not a directory: {self._path}")
        for name in os.listdir(self._path):
            yield Path(self._path, name)

    def __hash__(self):
        return hash(self._path)
