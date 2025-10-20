import time
import board
import displayio
import terminalio
from adafruit_display_text import label
import adafruit_ili9341
from fourwire import FourWire

displayio.release_displays()

spi = board.SPI()
tft_cs = board.D12
tft_dc = board.D11

display_bus = FourWire(spi, command=tft_dc, chip_select=tft_cs )
display = adafruit_ili9341.ILI9341(display_bus, width=320, height=240, rotation=0)
print( "Initialized display" )

display_group = displayio.Group()
display.root_group = display_group

color_bitmap = displayio.Bitmap(320, 240, 1)
color_palette = displayio.Palette(1)
color_palette[0] = 0xFF0022 #

background = displayio.TileGrid(color_bitmap, pixel_shader=color_palette, x=0, y=0)

display_group.append(background)

inner_bitmap = displayio.Bitmap(280, 200, 1)
inner_palette = displayio.Palette(1)
inner_palette[0] = 0x0000FF # blue
inner_sprite = displayio.TileGrid(inner_bitmap, pixel_shader=inner_palette, x=20, y=20)
display_group.append(inner_sprite)

text_group = displayio.Group(scale=5, x=70, y=120)
text = "STELLA"
text_area = label.Label(terminalio.FONT, text=text, color=0xFFFFFF)
text_group.append(text_area) # Subgroup for text scaling
display_group.append(text_group)
count = 0
while True:
    time.sleep(2)
    count += 1
    text_area.text = ("more {}".format ( count ))

