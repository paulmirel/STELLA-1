# gps module
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel


import time
import adafruit_gps
from .classm_device import Device

            
def initialize_gps( instrument ):
    gps = Null_GPS()
    try:
        gps = pa1616d_GPS( instrument.uart_bus )
        instrument.welcome_page.announce( "initialize_gps" )
        instrument.sensors_present.append( gps )
        time.sleep(0.1)
        gps.request_firmware_report()
        gps.send_start_commands()
    except Exception as err:
        print("gps failed init: {}".format(err))
        pass
    return gps

class pa1616d_GPS( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "gps", pn = "pa1616d", address = 0x00, swob = adafruit_gps.GPS( com_bus, debug=False))
        self.last_read = 0
    def send_start_commands(self):
        self.swob.send_command(b"PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0") #set data output configuration
        self.swob.send_command(b"PMTK220,1000") #set update interval to 1000 ms

    def request_firmware_report( self ):
        self.swob.send_command(b"PMTK605")  # request firmware version
        data = self.swob.read(32)  # read up to 32 bytes
            # print(data)  # this is a bytearray type
        if data is not None:
            # convert bytearray to string
            data_string = "".join([chr(b) for b in data])
            print( "gps firmware report = ", end='')
            report = data_string[:4]
            print( report )
        else:
            report = ["False"]
            print( "no data on firmware" )
        if report[0] == '$':
            print("good gps firmware report")
        else:
            print("gps status not determined")
        return report
    # TBD can we get warm start battery health information?
    def fix(self):
        return self.swob.has_fix
    def read(self):
        self.swob.update()
        self.latitude = self.swob.latitude
        self.longitude = self.swob.longitude
        self.altitude = self.swob.altitude_m
        self.timestruct = self.swob.timestamp_utc
    def header(self):
        return( "gps_fix-!-boolean, gps_latitude-!-degrees, gps_longitude-!-degrees, gps_altitude-!-m, gps_timestamp-!-iso8601utc" )
    def log(self):
        if self.timestruct is not None:
            self.gps_timestamp = "{}{:02}{:02}T{:02}{:02}{:02}Z".format(
                        self.timestruct.tm_year,# Note you might not get all data like year month day
                        self.timestruct.tm_mon,
                        self.timestruct.tm_mday,
                        self.timestruct.tm_hour,
                        self.timestruct.tm_min,
                        self.timestruct.tm_sec
                        )
        else: self.gps_timestamp = None #"20000101T000000Z"
        return "{}, {}, {}, {}, {}".format( self.swob.has_fix, self.latitude, self.longitude, self.altitude, self.gps_timestamp )
    def printlog(self):
        print( self.log())

class Null_GPS(Device):
    def __init__( self ):
        super().__init__(name = None, swob = None)
    def read(self):
        pass
    def log(self):
        pass
    def fix(self):
        return False
    def report(self):
        pass
    def send_start_commands(self):
        pass
    def printlog(self):
        pass
    def header(self):
        pass
