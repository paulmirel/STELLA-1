#record simple file to sd card
#2022-08-20
#Paul Mirel

import time
import sdcardio
import board
import busio
import digitalio
import storage
import terminalio

# Adalogger Featherwing uses pin D10 for the SDCard chip select line on the SPI bus
# THAT WAS A COLLISION, so I modified the SD card to use pin D11 for chip select
sd_cs = board.D11
spi_bus = board.SPI()
# Connect to the card and mount the filesystem.
sdcard = sdcardio.SDCard( spi_bus, sd_cs )
vfs = storage.VfsFat( sdcard )
storage.mount( vfs, "/sd" )
# Files are under /sd

with open( "/sd/test.txt", "w" ) as f:
    f.write( "year, month, day, batch, checksum\n" )
    f.write( "2022, 10, 25, 5, 11, " )
    f.write( "more information on the same line\n" )


with open("/sd/test.txt", "r") as f:
    print("Printing lines in file:")
    print()
    line = f.readline()
    while line != '':
        print(line)
        line = f.readline()
print()
print( "Program Completed" )
