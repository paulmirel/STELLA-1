# Annoying functions to not have
import os

def file_exists(name):
    try:
        os.stat(name)
        return True
    except OSError as e:
        # this is what happens if the path doesn't exist
        # str comparisons are not stable across implementations of python
        if e.args[0] == 2 or "No such file/directory" in str(e):
            return False
        else:
            raise e

def is_dir(path):
    try:
        _isdir = os.stat(path)[0] & 0x4000
    except OSError as e:
        _isdir = False
    return _isdir

def is_file(path):
    try:
        _isfile = os.stat(path)[0] & 0x8000
    except OSError as e:
        _isfile = False
    return _isfile

