# ili9341 function
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

def initialize_display( spi_bus ):
    try:
        # displayio/dafruit_ili9341 library owns the pins until display release
        displayio.release_displays()
        tft_dc = board.D11
        tft_cs = board.D12
        display_bus = FourWire(spi_bus, command=tft_dc, chip_select=tft_cs )
        display = adafruit_ili9341.ILI9341(display_bus, width=320, height=240, rotation=0)
        print( "display initialized")

    except ValueError as err:
        print("Error: display failed to initialize {:}".format(err))
        display = False
    if display:
        display_group = displayio.Group()
        display.root_group = display_group
    return display_group
