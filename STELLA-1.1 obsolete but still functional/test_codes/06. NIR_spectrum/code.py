import time
import board
import busio
import digitalio
def main():
    #initialize_NIR
    #Calibration information from AS7263 datasheet:
    #Each channel is tested with GAIN = 16x, Integration Time (INT_T) = 166ms and VDD = VDD1 = VDD2 = 3.3V, TAMB=25°C.
    #The accuracy of the channel counts/μW/cm2 is ±12%.
    #610nm, 680nm, 730nm, 760nm, 810nm and 860nm
    try:
        #sensor_NIR = busio.UART(board.TX, board.RX, baudrate=115200, bits=8, parity=1, stop=1)
        sensor_NIR = busio.UART(board.D24, board.D25, baudrate=115200, bits=8, parity=1, stop=1 )
        print( "NIR Spectrometer Sensor detected at UART" )
        sensor_NIR_present = True
    except ValueError:
        print( "Error, no uart device detected" )
        sensor_NIR_present = False


    data = 0
    count = 0
    cycles = 1
    while count < cycles:
        count = count + 1
        if data is not None:
            s = "ATLED0\n"
            b = bytearray()
            b.extend(s)
            sensor_NIR.write(b)
            print( "Bytearray sent: %s" % b )

            data = sensor_NIR.readline()
            print( "Data received: %s" % data)   #first command always returns an error

            s = "ATLED1=100\n" #100 is on, 0 is off
            b = bytearray()
            b.extend(s)
            sensor_NIR.write(b)
            print( "Bytearray sent: %s" % b )

            data = sensor_NIR.readline()
            print( "Data received: %s" % data)
            time.sleep(1.0)

            s = "ATLEDC\n"
            b = bytearray()
            b.extend(s)
            sensor_NIR.write(b)
            print( "Bytearray sent: %s" % b )
            time.sleep(1.0)

            data = sensor_NIR.readline()
            print( "Data received: %s" % data)

            v = int( '100000', 2)
            print(v)

            s = "ATLEDC=32\n" #0, 16, 32, 48 set the driver led to 12.5, 25, 50, 100 mA
            b = bytearray()
            b.extend(s)
            sensor_NIR.write(b)
            print( "Bytearray sent: %s" % b )
            time.sleep(1.0)

            data = sensor_NIR.readline()
            print( "Data received: %s" % data)

            s = "ATLEDC\n"
            b = bytearray()
            b.extend(s)
            sensor_NIR.write(b)
            print( "Bytearray sent: %s" % b )
            time.sleep(1.0)

            data = sensor_NIR.readline()
            print( "Data received: %s" % data)

            time.sleep(0.5)

            s = "ATLED1=0\n" #100 is on, 0 is off
            b = bytearray()
            b.extend(s)
            sensor_NIR.write(b)
            print( "Bytearray sent: %s" % b )





    #query NIR spectral sensor
    data = 0
    count = 0
    cycles = 2
    while count < cycles:
        count = count + 1
        if data is not None:
            s = "ATTCSMD\n"
            b = bytearray()
            b.extend(s)
            sensor_NIR.write(b)
            #print( "Bytearray sent: %s" % b )

            data = sensor_NIR.readline()
            print( "Data received MODE: %s" % data)

    read_data(sensor_NIR)

    data = 0
    count = 0
    cycles = 1
    while count < cycles:
        count = count + 1
        if data is not None:
            s = "ATGAIN\n"
            b = bytearray()
            b.extend(s)
            sensor_NIR.write(b)
            #print( "Bytearray sent: %s" % b )

            data = sensor_NIR.readline()
            print( "Data received default GAIN: %s" % data)


    data = 0
    count = 0
    cycles = 1
    while count < cycles:
        count = count + 1
        if data is not None:
            s = "ATGAIN = 2\n"
            b = bytearray()
            b.extend(s)
            sensor_NIR.write(b)
            #print( "Bytearray sent: %s" % b )

            data = sensor_NIR.readline()
            print( "Data received GAIN SET: %s" % data)

    data = 0
    count = 0
    cycles = 1
    while count < cycles:
        count = count + 1
        if data is not None:
            s = "ATGAIN\n"
            b = bytearray()
            b.extend(s)
            sensor_NIR.write(b)
            #print( "Bytearray sent: %s" % b )

            data = sensor_NIR.readline()
            print( "Data received GAIN: %s" % data)

    #read_data(sensor_NIR)

    data = 0
    count = 0
    cycles = 1
    while count < cycles:
        count = count + 1
        if data is not None:
            #read NIR spectral sensor
            s = "ATINTTIME\n"
            b = bytearray()
            b.extend(s)
            sensor_NIR.write(b)
            #print( "Bytearray sent: %s" % b )

            data = sensor_NIR.readline()
            print( "Data received default INTTIME: %s" % data)

    data = 0
    count = 0
    cycles = 1
    while count < cycles:
        count = count + 1
        if data is not None:
            #read NIR spectral sensor
            s = "ATINTTIME = 59\n"
            b = bytearray()
            b.extend(s)
            sensor_NIR.write(b)
            #print( "Bytearray sent: %s" % b )

            data = sensor_NIR.readline()
            print( "Data received INTTIME SET: %s" % data)

    data = 0
    count = 0
    cycles = 1
    while count < cycles:
        count = count + 1
        if data is not None:
            #read NIR spectral sensor
            s = "ATINTTIME\n"
            b = bytearray()
            b.extend(s)
            sensor_NIR.write(b)
            #print( "Bytearray sent: %s" % b )

            data = sensor_NIR.readline()
            print( "Data received INTTIME: %s" % data)

    read_data(sensor_NIR)

def read_data(sensor_NIR):
    data = 0
    count = 0
    cycles = 10
    while count < cycles:
        count = count + 1
        if data is not None:
            #read NIR spectral sensor
            s = "ATCDATA\n"
            b = bytearray()
            b.extend(s)
            sensor_NIR.write(b)
            #print( "Bytearray sent: %s" % b )

            data = sensor_NIR.readline()
            #print( "Data received: %s" % data)

            if data is None:                    #if returned data is of type NoneType
                print( "Alert: Sensor miswired at main instrument board, or not properly modified for uart usage" )
                print( "Enable serial communication via UART by removing solder from the jumpers labeled JP1," )
                print( "and add solder to the jumper labeled JP2 (on the back of the board)" )
            else:
                datastr = ''.join([chr(b) for b in data]) # convert bytearray to string
                #print( "Data converted to string: %s" % datastr )

                datastr = datastr.rstrip(" OK\n")
                #print( "Datastring stripped: %s" % datastr )
                if datastr == "ERROR":
                    datastr = "0.0, 0.0, 0.0, 0.0, 0.0, 0.0"

                datalist_NIR = datastr.split( ", " )
                n = 0
                while n < 6:
                    a = type( datalist_NIR[n] )
                    #print( "Element %d of the list is: %s and is type" % ( n, datalist_NIR[n] ) )
                    #print ( a )

                    try:
                        datalist_NIR[n] = float( datalist_NIR[n] )
                    except ValueError:
                        datalist_NIR[n] = 0
                    #print( "After converting to float, element %d of the list is: %0.1f and is type" % ( n, datalist_NIR[n] ) )
                    a = type( datalist_NIR[n] )
                    #print ( a )
                    n += 1

                Rstr = "610nm: %0.1f" % datalist_NIR[0]
                Sstr = "680nm: %0.1f" % datalist_NIR[1]
                Tstr = "730nm: %0.1f" % datalist_NIR[2]
                Ustr = "760nm: %0.1f" % datalist_NIR[3]
                Vstr = "810nm: %0.1f" % datalist_NIR[4]
                Wstr = "860nm: %0.1f" % datalist_NIR[5]
                print()
                print( "uW/cm^2" )
                print( Rstr )
                print( Sstr )
                print( Tstr )
                print( Ustr )
                print( Vstr )
                print( Wstr )

                time.sleep(0.5)

main()
