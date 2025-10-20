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
        sensor_NIR = busio.UART(board.TX, board.RX, baudrate=115200, bits=8, parity=1, stop=1)
        print( "NIR Spectrometer Sensor detected at UART" )
        sensor_NIR_present = True
    except ValueError:
        print( "Error, no uart device detected" )
        sensor_NIR_present = False

    read_data(sensor_NIR)

def read_data(sensor_NIR):
    data = 0
    count = 0
    cycles = 2
    while count < cycles:
        count = count + 1
        if data is not None:
            #read NIR spectral sensor
            s = "ATTEMP\n"
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
                print( "Data converted to string: %s" % datastr )

                datastr = datastr.rstrip(" OK\n")
                print( "Supposed to be degrees C but seems high: %s" % datastr )
                print( "Joule heating of sensor? Accuracy +/- 8.5C per datasheet" )



main()
