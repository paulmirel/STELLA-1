import gc
import board
import time
import digitalio
import displayio
import terminalio
import adafruit_gps
import busio



def main():
    try:
        indicator_LED = digitalio.DigitalInOut( board.LED )
        indicator_LED.direction = digitalio.Direction.OUTPUT
        indicator_LED.value = 1
        print( "initialized indicator" )
    except Exception as err:
        print( "Error: led pin init failed {:}".format(err) )

    indicator_LED.value = 1
    time.sleep(1)
    indicator_LED.value = 0

    spi = board.SPI()
    tft_cs = board.D9
    tft_dc = board.D10

    uart = busio.UART(board.TX, board.RX, baudrate=9600, timeout=10)
    gps_sensor = initialize_gps( uart )
    gps_sensor.send_command(b"PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0")
    gps_sensor.send_command(b"PMTK220,1000")

    request_firmware_report( gps_sensor )

    GPS_fix = True
    loop_count = 0
    last_print = time.monotonic()
    while True:
        print( "loop count = {}".format( loop_count ), end = " -- " )
        loop_count += 1
        gps_sensor.update()  # read up to 32 bytes
        print("Fix quality: {}".format(gps_sensor.fix_quality))

        if gps_sensor.has_fix:
            indicator_LED.value = 1
            print("FIX")
            print("# satellites: {}".format(gps_sensor.satellites))
            print("Latitude: {0:.6f} degrees".format(gps_sensor.latitude))
            print("Longitude: {0:.6f} degrees".format(gps_sensor.longitude))
            print(
                "Fix timestamp: {}/{}/{} {:02}:{:02}:{:02}".format(
                    gps_sensor.timestamp_utc.tm_mon,  # Grab parts of the time from the
                    gps_sensor.timestamp_utc.tm_mday,  # struct_time object that holds
                    gps_sensor.timestamp_utc.tm_year,  # the fix time.  Note you might
                    gps_sensor.timestamp_utc.tm_hour,  # not get all data like year, day,
                    gps_sensor.timestamp_utc.tm_min,  # month!
                    gps_sensor.timestamp_utc.tm_sec,
                    )
                )
            time.sleep( 0.25 )
        else:
            indicator_LED.value = 0

        time.sleep( 1 )

def request_firmware_report( gps_sensor ):
    gps_sensor.send_command(b"PMTK605")  # request firmware version
    data = gps_sensor.read(32)  # read up to 32 bytes
        # print(data)  # this is a bytearray type
    if data is not None:
        # convert bytearray to string
        data_string = "".join([chr(b) for b in data])
        print( "gps firmware report = ", end='')
        print(data_string[:4], end="")
    else:
        print( "no data on firmware" )
    print("\n")
    time.sleep(2)

def initialize_gps( uart ):
    try:
        gps = adafruit_gps.GPS( uart, debug=False)
        print("gps init success")
    except ValueError:
        gps = False
    return gps

main()
