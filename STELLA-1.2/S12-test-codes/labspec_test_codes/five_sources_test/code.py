import time
import board
import digitalio
import analogio
import adafruit_mcp4728

MCP4728_DEFAULT_ADDRESS = 0x60
MCP4728A4_DEFAULT_ADDRESS = 0x64

# connect the main battery to power the boost module to make the 5V output

i2c_bus = board.I2C()

#  use for MCP4728 variant
#mcp4728 = adafruit_mcp4728.MCP4728(i2c_bus, adafruit_mcp4728.MCP4728_DEFAULT_ADDRESS)
#  use for MCP4728A4 variant
mcp4728 = adafruit_mcp4728.MCP4728(i2c_bus, adafruit_mcp4728.MCP4728A4_DEFAULT_ADDRESS)
output_value = 55000
mcp4728.channel_a.value = 0#output_value
mcp4728.channel_b.value = output_value
mcp4728.channel_c.value = output_value
mcp4728.channel_d.value = output_value


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

index = 0
while True:
    enable_5V.value = True
    time.sleep(0.2)
    print( "5V ON: voltage on the 5V line = ", get_voltage(monitor_5V))
    print( "loop count {}".format(index) )
    index += 1
    time.sleep( 1 )
    enable_5V.value = False
    time.sleep( 2 )
    print( "5V OFF: voltage on the 5V line = ", get_voltage(monitor_5V))
