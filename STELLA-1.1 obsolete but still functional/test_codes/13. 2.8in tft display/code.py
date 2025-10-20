"""
This test will initialize the display using displayio, and draw a solid red
background, a smaller purple rectangle, and some white text.

Pinouts are for the 2.4" TFT FeatherWing with a Feather M4 or M0.
"""
import time
import board
import displayio
import terminalio
from adafruit_display_text import label
import adafruit_ili9341

# Release any resources currently in use for the displays
displayio.release_displays()

spi = board.SPI()
tft_cs = board.D9
tft_dc = board.D10

display_bus = displayio.FourWire(spi, command=tft_dc, chip_select=tft_cs, reset=board.D6)
display = adafruit_ili9341.ILI9341(display_bus, width=320, height=240, rotation=180)
print( "Initialized display" )

# Make the display context
splash = displayio.Group()
display.show(splash)

# Draw a green background
color_bitmap = displayio.Bitmap(320, 240, 1)
color_palette = displayio.Palette(1)
color_palette[0] = 0xFF0022 #Reddish

bg_sprite = displayio.TileGrid(color_bitmap,
                               pixel_shader=color_palette,
                               x=0, y=0)

splash.append(bg_sprite)

# Draw a smaller inner rectangle
inner_bitmap = displayio.Bitmap(280, 200, 1)
inner_palette = displayio.Palette(1)
inner_palette[0] = 0x0000FF # blue
inner_sprite = displayio.TileGrid(inner_bitmap,
                                  pixel_shader=inner_palette,
                                  x=20, y=20)
splash.append(inner_sprite)

# Draw a label
text_group = displayio.Group(scale=5, x=70, y=120)
text = "STELLA"
text_area = label.Label(terminalio.FONT, text=text, color=0xFFFFFF)
text_group.append(text_area) # Subgroup for text scaling
splash.append(text_group)
count = 0
while True:
    time.sleep(2)
    count += 1
    text_area.text = ("more {}".format ( count ))

