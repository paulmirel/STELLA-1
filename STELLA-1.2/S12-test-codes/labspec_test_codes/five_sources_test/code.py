import time
import board
import digitalio
import analogio
import adafruit_mcp4728
import adafruit_as7341_nonblocking

MCP4728_DEFAULT_ADDRESS = 0x60
MCP4728A4_DEFAULT_ADDRESS = 0x64

# connect the main battery to power the boost module to make the 5V output

i2c_bus = board.I2C()

#  use for MCP4728 variant
try:
    mcp4728 = adafruit_mcp4728.MCP4728(i2c_bus, adafruit_mcp4728.MCP4728_DEFAULT_ADDRESS)
except Exception as err:
    print( err )
    #  use for MCP4728A4 variant
    mcp4728 = adafruit_mcp4728.MCP4728(i2c_bus, adafruit_mcp4728.MCP4728A4_DEFAULT_ADDRESS)

spectral_sensor = adafruit_as7341_nonblocking.AS7341(i2c_bus)
spectral_sensor.led_current = 50

try:
    enable_5V = digitalio.DigitalInOut( board.D10 )
    enable_5V.direction = digitalio.Direction.OUTPUT
    enable_5V.value = True #active low, True is off
    monitor_5V = analogio.AnalogIn( board.A1)
    print( "initialized" )
except:
    print( "Error: 5V pins init failed" )

def get_voltage(pin):
    return (pin.value * 3.3) / 65536 * 2

output_value = 55000
index = 0

while True:
    try:
        print()
        if index in range (0, 4):
            mcp4728.channel_a.value = output_value
            print("Channel 0" )
        else:
            mcp4728.channel_a.value = 0

        if index in range (4, 8):
            mcp4728.channel_b.value = output_value
            print("Channel 1" )
        else:
            mcp4728.channel_b.value = 0

        if index in range (8, 12):
            mcp4728.channel_c.value = output_value
            print("Channel 2" )
        else:
            mcp4728.channel_c.value = 0

        if index in range (12, 16):
            mcp4728.channel_d.value = output_value
            print("Channel 3" )
        else:
            mcp4728.channel_d.value = 0

        if index in range( 16, 20 ):
            print("Spectral_sensor lamp" )
            headlamp_enabled = True
        else:
            headlamp_enabled = False

        if index > 19:
            index = 0

        enable_5V.value = True
        if headlamp_enabled:
            spectral_sensor.led = True
        time.sleep(0.2)
        print( "5V ON: voltage on the 5V line = ", get_voltage(monitor_5V))
        print( "loop count {}".format(index) )
        index += 1
        time.sleep( 0.75 )
        if headlamp_enabled:
            spectral_sensor.led = False
        enable_5V.value = False
        time.sleep( 1.2 )
        #print( "5V OFF: voltage on the 5V line = ", get_voltage(monitor_5V))
    finally:
        enable_5V.value = False
