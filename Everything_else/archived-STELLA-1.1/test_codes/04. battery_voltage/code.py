import board
from analogio import AnalogIn

vbat_voltage_pin = AnalogIn(board.A1)


def get_voltage(pin):
    return (pin.value * 3.3) / 65536 * 2

battery_voltage = get_voltage(vbat_voltage_pin)
print("Main battery voltage: {:.2f} V".format(battery_voltage))
