import struct
from adafruit_bus_device.i2c_device import I2CDevice

class Device:
    """Class for communicating with an I2C device.

    Allows reading and writing 8-bit, 16-bit, and byte array values to
    registers on the device."""

    def __init__(self, address, i2c):
        """Create an instance of the I2C device at the specified address using
        the specified I2C interface object."""
        self._address = address
        self._i2c = i2c
        self.i2c_device = I2CDevice(i2c, address)
        self.buf2 = bytearray(2)

    def write8(self, register, value):
        """Write an 8-bit value to the specified register."""
        value = value & 0xFF
        buf = self.buf2
        buf[0] = register
        buf[1] = value
        with self.i2c_device as i2c:
            i2c.write(buf)

    def readU8(self, register):
        """Read an unsigned byte from the specified register."""
        buf = self.buf2
        buf[0] = register
        with self.i2c_device as i2c:
            i2c.write(buf, end=1)
            i2c.readinto(buf, end=1)
        return buf[0]
