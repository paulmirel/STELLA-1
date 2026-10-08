# welcome page
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

import displayio
from adafruit_display_text import label
import vectorio
import terminalio
from .classm_page import Page

class Welcome_Page( Page ):
    def __init__( self ):
        super().__init__()
        self.page_name = "Welcome"
    def make_group( self, svn ):
        self.group = displayio.Group()
        try:
            bitmap = displayio.OnDiskBitmap("/lib/stella_logo.bmp")
            #print( "Bitmap image file found" )
            # Create a TileGrid to hold the bitmap
            tile_grid = displayio.TileGrid(bitmap, pixel_shader=bitmap.pixel_shader)
            self.group.append(tile_grid)

            version_group = displayio.Group( scale=2, x=40, y=185 )
            text = "STELLA-1.2 ver {}".format( svn )
            version_area = label.Label( terminalio.FONT, text=text, color=0x000000 )
            version_group.append( version_area )
            self.group.append( version_group )

            message_group = displayio.Group( scale=2, x=4, y=220 )
            text = ""
            self.message_area = label.Label( terminalio.FONT, text=text, color=0x000000 )
            message_group.append( self.message_area )
            self.group.append( message_group )

            #battery_group = displayio.Group( scale=2, x=90, y=215 )
            #text = "battery {}%".format( battery_level )
            #battery_area = label.Label( terminalio.FONT, text=text, color=0x000000 )
            #battery_group.append( battery_area )
            #welcome_group.append( battery_group )
            #print( "showing welcome screen with logo")
        except (MemoryError, OSError):
            print( "bitmap image file not found or memory not available" )
            border_color = 0xFF0022 # red
            front_color = 0x0000FF # blue
            if (display == False):
                print("No display")
                return
            border = displayio.Palette(1)
            border[0] = border_color
            front = displayio.Palette(1)
            front[0] = front_color
            outer_rectangle = vectorio.Rectangle(pixel_shader=border, width=320, height=240, x=0, y=0)
            self.group.append( outer_rectangle )
            front_rectangle = vectorio.Rectangle(pixel_shader=front, width=280, height=200, x=20, y=20)
            self.group.append( front_rectangle )
            text_group = displayio.Group( scale=4, x=45, y=110 )
            text = "STELLA-1.2"
            text_area = label.Label( terminalio.FONT, text=text, color=0xFFFFFF )
            text_group.append( text_area )
            self.group.append( text_group )

            version_group = displayio.Group( scale=2, x=27, y=200 )
            text = "software version {}".format( SOFTWARE_VERSION_NUMBER )
            version_area = label.Label( terminalio.FONT, text=text, color=0xFFFFFF )
            version_group.append( version_area )
            self.group.append( version_group )

            message_group = displayio.Group( scale=2, x=8, y=220 )
            text = "message here"
            self.message_area = label.Label( terminalio.FONT, text=text, color=0xFFFFFF )
            message_group.append( self.message_area )
            self.group.append( message_group )

        return self.group
    def announce( self, text ):
        self.message_area.text = text
        print( text )
    def update_values( self ):
        pass

def make_welcome_page( instrument, SOFTWARE_VERSION_NUMBER ):
    welcome_page = Welcome_Page()
    group = welcome_page.make_group(SOFTWARE_VERSION_NUMBER)
    welcome_page.hide()
    instrument.main_display_group.append( group )
    instrument.pages_list.append( welcome_page )
    return welcome_page
