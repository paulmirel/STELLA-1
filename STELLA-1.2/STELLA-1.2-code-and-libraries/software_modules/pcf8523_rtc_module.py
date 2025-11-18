# pcf8523 rtc module
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

class Device: #parent class
    def __init__(self, name = None, pn = None, address = None, swob = None ):
        self.name = name
        self.swob = swob
        self.pn = pn
        self.address = address
    def report(self):
        found = False
        if self.swob is not None:
            print("report:", hex(self.address), self.pn, "\t", self.name, "found" )
            found = True
        return found
    def found(self):
        if self.swob is not None:
            return True
        else:
            return False

def initialize_hardware_clock( i2c_bus ):
    hardware_clock = Null_Hardware_Clock()
    try:
        hardware_clock = pcf8523_Hardware_Clock( i2c_bus )
        print( "hardware clock initialized" )
    except NameError as err:
        print( "library missing:", err )
    except Exception:
        pass
    return hardware_clock

class pcf8523_Hardware_Clock( Device ):
    def __init__( self, com_bus ):
        super().__init__(name = "hardware_clock", pn = "pcf8523", address = 0x68, swob = pcf8523.PCF8523( com_bus ))
        self.null_time = time.struct_time(( 2020,  01,   01,   00,  00,  00,   0,   -1,    -1 ))
        self.timenow = self.null_time
        self.DAYS = { 0:"Sunday", 1:"Monday", 2:"Tuesday", 3:"Wednesday", 4:"Thursday", 5:"Friday", 6:"Saturday" }
    def battery_ok( self ):
        try:
            self.clock_battery_ok = not self.swob.battery_low
        except:
            self.clock_battery_ok = False
        return self.clock_battery_ok
    def read(self):
        try:
            self.timenow = self.swob.datetime
        except:
            self.timenow = self.null_time
        if self.timenow.tm_wday not in range ( 0, 7 ):
            self.datetime = null_time
        return self.timenow
    def get_iso_time_now( self ):
        self.read()
        iso8601_utc_timestamp = "{:04}{:02}{:02}T{:02}{:02}{:02}Z".format(
            self.timenow.tm_year, self.timenow.tm_mon, self.timenow.tm_mday,
            self.timenow.tm_hour, self.timenow.tm_min, self.timenow.tm_sec )
        return iso8601_utc_timestamp
    def get_decimal_hour_now( self ):
        self.read()
        decimal_hour = self.timenow.tm_hour + self.timenow.tm_min/60.0 + self.timenow.tm_sec/3600.0
        return decimal_hour
    def get_datestamp_now( self ):
        self.read()
        datestamp = "{:04}{:02}{:02}".format( self.timenow.tm_year, self.timenow.tm_mon, self.timenow.tm_mday )
        return datestamp
    def get_day_now( self ):
        return self.DAYS[self.timenow.tm_wday]
    def sync_system_clock(self):
        self.read()
        try:
            system_clock = rtc.RTC()
            system_clock.datetime = self.swob.datetime
            print( "system clock synchronized to hardware clock" )
        except:
            print( "failed to synchronize system clock to hardware clock" )
    def header(self):
        return "TBD"
    def log(self):
        return " "
    def printlog(self):
        print( self.log())
    def set_time(self):
        timenow = self.swob.datetime
        print()
        weekday = timenow.tm_wday
        year = timenow.tm_year
        month = timenow.tm_mon
        day = timenow.tm_mday
        hour = timenow.tm_hour
        minute = timenow.tm_min
        second = timenow.tm_sec
        previous_weekday = weekday
        previous_year = year
        previous_month = month
        previous_day = day
        previous_hour = hour
        previous_minute = minute
        previous_second = second
        try:
            print( "The date is %s %d-%d-%d" % ( self.DAYS[ weekday ], year, month, day ))
            print( "The time is %d:%02d:%02d" % ( hour, minute, second ))
        except IndexError as err:
            print( "The clock has not been set, and the values are out of range." )

        print()
        print( "Current year is {}. Enter a new year and press return, or press return to skip.".format(timenow.tm_year))
        print(">", end = ' ')
        input_string = False
        while input_string == False:
            input_string = input().strip()
        try:
            input_integer = int( input_string )
        except ValueError:
            input_integer = 2000
        if input_integer in range (2010, 2100):
            year = input_integer
            t = time.struct_time(( year,  month,   day,   hour,  minute,  second,   weekday,   -1,    -1 ))
            self.swob.datetime = t

        print()
        print( "Current month is {}. Enter a new month and press return, or press return to skip.".format(timenow.tm_mon))
        print(">", end = ' ')
        input_string = False
        while input_string == False:
            input_string = input().strip()
        try:
            input_integer = int( input_string )
        except ValueError:
            pass
        if input_integer in range (1, 12):
            month = input_integer
            t = time.struct_time(( year,  month,   day,   hour,  minute,  second,   weekday,   -1,    -1 ))
            self.swob.datetime = t
        print()
        print( "Current day is {}. Enter a new day and press return, or press return to skip.".format(timenow.tm_mday))
        print(">", end = ' ')
        input_string = False
        while input_string == False:
            input_string = input().strip()
        try:
            input_integer = int( input_string )
        except ValueError:
            pass
        if input_integer in range (1, 32):
            day = input_integer
            t = time.struct_time(( year,  month,   day,   hour,  minute,  second,   weekday,   -1,    -1 ))
            self.swob.datetime = t

        print()
        print( "Current hour is {} UTC. Enter a new hour and press return, or press return to skip.".format(timenow.tm_hour))
        print(">", end = ' ')
        input_string = False
        while input_string == False:
            input_string = input().strip()
        try:
            input_integer = int( input_string )
        except ValueError:
            pass
        if input_integer in range (0, 23):
            hour = input_integer
            t = time.struct_time(( year,  month,   day,   hour,  minute,  second,   weekday,   -1,    -1 ))
            self.swob.datetime = t

        print()
        print( "Current minute is {}. Enter a new minute and press return, or press return to skip.".format(timenow.tm_min))
        print(">", end = ' ')
        input_string = False
        while input_string == False:
            input_string = input().strip()
        try:
            input_integer = int( input_string )
        except ValueError:
            pass
        if input_integer in range (0, 59):
            minute = input_integer
            t = time.struct_time(( year,  month,   day,   hour,  minute,  second,   weekday,   -1,    -1 ))
            self.swob.datetime = t

        print()
        print( "Current second is {}. Enter a new second and press return, or press return to skip.".format(timenow.tm_sec))
        print(">", end = ' ')
        input_string = False
        while input_string == False:
            input_string = input().strip()
        try:
            input_integer = int( input_string )
        except ValueError:
            pass
        if input_integer in range (0, 59):
            second = input_integer
            t = time.struct_time(( year,  month,   day,   hour,  minute,  second,   weekday,   -1,    -1 ))
            self.swob.datetime = t

        print()
        print( "Current weekday is {}. Enter a new weekday and press return, or press return to skip.".format(self.DAYS[timenow.tm_wday]))
        print( "Enter: sun, mon, tue, wed, thu, fri, sat" )
        print(">", end = ' ')
        input_string = False

        input_string = input().strip()
        print(input_string)
        if input_string == "mon":
            weekday = 1
        elif input_string == "tue":
            weekday = 2
        elif input_string == "wed":
            weekday = 3
        elif input_string == "thu":
            weekday = 4
        elif input_string == "fri":
            weekday = 5
        elif input_string == "sat":
            weekday = 6
        elif input_string == "sun":
            weekday = 0
        else:
            pass
        print("weekday = {}".format(weekday))
        t = time.struct_time(( year,  month,   day,   hour,  minute,  second,   weekday,   -1,    -1 ))
        self.swob.datetime = t
        print( "returning to status page" )

class Null_Hardware_Clock():
    def __init__( self ):
        self.swob = None
        self.null_time = time.struct_time(( 2020,  01,   01,   00,  00,  00,   0,   -1,    -1 ))
        self.timenow = self.null_time
    def read(self):
        pass
    def battery_ok( self ):
        pass
    def get_day_now( self ):
        pass
    def get_time_now_iso_dec( self ):
        self.read()
        iso8601_utc_timestamp = "{:04}{:02}{:02}T{:02}{:02}{:02}Z".format(
            self.timenow.tm_year, self.timenow.tm_mon, self.timenow.tm_mday,
            self.timenow.tm_hour, self.timenow.tm_min, self.timenow.tm_sec )
        decimal_hour = time.monotonic()/ 3600
        return iso8601_utc_timestamp, decimal_hour
    def sync_system_clock(self):
        pass
    def set_time(self):
        pass


