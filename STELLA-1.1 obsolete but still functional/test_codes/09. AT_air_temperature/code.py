import time
import board
import busio
import adafruit_mcp9808


def main():
    i2c_bus = busio.I2C(board.SCL, board.SDA)
    mcp = adafruit_mcp9808.MCP9808(i2c_bus)

    while True:
        temperature_C = mcp.temperature
        print('Temperature = {} C'.format( temperature_C ))
        time.sleep(1)






main()
