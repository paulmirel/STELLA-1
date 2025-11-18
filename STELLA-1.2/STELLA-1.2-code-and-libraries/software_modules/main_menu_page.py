# main menu page module
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

class Page:
    def __init__( self ):
        pass
    def show(self):
        self.group.hidden = False
    def hide(self):
        self.group.hidden = True
    def update_values(self):
        pass

class Main_Menu_Page( Page ):
    def __init__( self, palette):
        super().__init__()
        self.palette = palette
    def make_group( self ):
        menu_list = "Remote Sense", "Air Analyzer", "Sensors", "Time / Place", "*future use", "*future use", "*future use", "*future use"#, "* Air Analyz", "* Heat", "* Plants"
        menu_color_list = 20, 12, 21, 14, 19, 19, 19, 19
        self.group = displayio.Group()
        start_y = 54
        status_background = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=320, height=240-start_y, x=0, y=start_y )
        self.group.append( status_background )
        title_bar = vectorio.Rectangle(pixel_shader=self.palette, color_index=19, width=320-2*5, height=24, x=0+5, y=start_y)
        self.group.append( title_bar )
        title_group = displayio.Group(scale=2, x=100, y=12+start_y)
        title_text = "Main Menu"
        title_text_area = label.Label(terminalio.FONT, text=title_text, color=self.palette[0])
        title_group.append(title_text_area)
        self.group.append(title_group)
        #selection rectangles
        selection_start_x = 2
        selection_start_y = 78
        selection_offset_x = 158
        selection_offset_y = 31
        self.selection_rectangles = []
        #TBD be more clever about this section
        self.selection_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=158, height=36, x=selection_start_x, y=selection_start_y))
        self.group.append( self.selection_rectangles[0] )
        self.selection_rectangles[0].hidden = True
        self.selection_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=158, height=36, x=selection_start_x+selection_offset_x, y=selection_start_y))
        self.group.append( self.selection_rectangles[1] )
        self.selection_rectangles[1].hidden = True
        self.selection_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=158, height=36, x=selection_start_x, y=selection_start_y+selection_offset_y))
        self.group.append( self.selection_rectangles[2] )
        self.selection_rectangles[2].hidden = True
        self.selection_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=158, height=36, x=selection_start_x+selection_offset_x, y=selection_start_y+selection_offset_y))
        self.group.append( self.selection_rectangles[3] )
        self.selection_rectangles[3].hidden = True
        self.selection_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=158, height=36, x=selection_start_x, y=selection_start_y+selection_offset_y*2))
        self.group.append( self.selection_rectangles[4] )
        self.selection_rectangles[4].hidden = True
        self.selection_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=158, height=36, x=selection_start_x+selection_offset_x, y=selection_start_y+selection_offset_y*2))
        self.group.append( self.selection_rectangles[5] )
        self.selection_rectangles[5].hidden = True
        self.selection_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=158, height=36, x=selection_start_x, y=selection_start_y+selection_offset_y*3))
        self.group.append( self.selection_rectangles[6] )
        self.selection_rectangles[6].hidden = True
        self.selection_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=158, height=36, x=selection_start_x+selection_offset_x, y=selection_start_y+selection_offset_y*3))
        self.group.append( self.selection_rectangles[7] )
        self.selection_rectangles[7].hidden = True
        #choice color rectangles
        selection_border = 5
        choice_rectangles = []
        #TBD be more clever about this section
        choice_width = 158-2*selection_border
        choice_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=menu_color_list[0],
            width=choice_width, height=36-2*selection_border, x=selection_start_x+selection_border, y=selection_start_y+selection_border))
        self.group.append( choice_rectangles[0] )
        choice_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=menu_color_list[1],
            width=choice_width, height=36-2*selection_border, x=selection_start_x+selection_border+selection_offset_x, y=selection_start_y+selection_border))
        self.group.append( choice_rectangles[1] )
        choice_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=menu_color_list[2],
            width=choice_width, height=36-2*selection_border, x=selection_start_x+selection_border, y=selection_start_y+selection_border+selection_offset_y))
        self.group.append( choice_rectangles[2] )
        choice_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=menu_color_list[3],
            width=choice_width, height=36-2*selection_border, x=selection_start_x+selection_border+selection_offset_x, y=selection_start_y+selection_border+selection_offset_y))
        self.group.append( choice_rectangles[3] )
        choice_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=menu_color_list[4],
            width=choice_width, height=36-2*selection_border, x=selection_start_x+selection_border, y=selection_start_y+selection_border+selection_offset_y*2))
        self.group.append( choice_rectangles[4] )
        choice_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=menu_color_list[5],
            width=choice_width, height=36-2*selection_border, x=selection_start_x+selection_border+selection_offset_x, y=selection_start_y+selection_border+selection_offset_y*2))
        self.group.append( choice_rectangles[5] )
        choice_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=menu_color_list[6],
            width=choice_width, height=36-2*selection_border, x=selection_start_x+selection_border, y=selection_start_y+selection_border+selection_offset_y*3))
        self.group.append( choice_rectangles[6] )
        choice_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=menu_color_list[7],
            width=choice_width, height=36-2*selection_border, x=selection_start_x+selection_border+selection_offset_x, y=selection_start_y+selection_border+selection_offset_y*3))
        self.group.append( choice_rectangles[7] )



        #choice text
        menu_spacing_y = selection_offset_y
        menu_start_y = 12+start_y+30
        menu_spacing_x = 158
        menu_start_x = 10
        for index in range ( 0, len(menu_list), 2):
            item_group = displayio.Group(scale=2, x=menu_start_x, y=menu_start_y+menu_spacing_y*int(index/2))
            item_text = menu_list[ index ]
            item_text_area = label.Label(terminalio.FONT, text=item_text, color=self.palette[0])
            item_group.append(item_text_area)
            self.group.append(item_group)
            if index + 1 < len(menu_list):
                item_group = displayio.Group(scale=2, x=menu_start_x+menu_spacing_x, y=menu_start_y+menu_spacing_y*int(index/2))
                item_text = menu_list[ index+1 ]
                item_text_area = label.Label(terminalio.FONT, text=item_text, color=self.palette[0])
                item_group.append(item_text_area)
                self.group.append(item_group)

        footer_start_y = 204
        footer_offset_x = 106
        self.selection_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=104, height=36, x=selection_start_x, y=footer_start_y))
        self.group.append( self.selection_rectangles[8] )
        self.selection_rectangles[8].hidden = True
        self.selection_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=104, height=36, x=selection_start_x+footer_offset_x, y=footer_start_y))
        self.group.append( self.selection_rectangles[9] )
        self.selection_rectangles[9].hidden = True
        self.selection_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=104, height=36, x=selection_start_x+2*footer_offset_x, y=footer_start_y))
        self.group.append( self.selection_rectangles[10] )
        self.selection_rectangles[10].hidden = True
        status_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=16, width=96, height=28, x=selection_start_x+4, y=208)
        self.group.append( status_color )
        self.more_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=19, width=96, height=28, x=selection_start_x+4+footer_offset_x, y=208)
        self.group.append( self.more_color )
        self.return_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=22, width=96, height=28, x=selection_start_x+4+2*footer_offset_x, y=208)
        self.group.append( self.return_color )

        footer_text_start_x = 14
        footer_text_y = 222
        status_text = "Status"
        status_group = displayio.Group(scale=2, x=footer_text_start_x, y=footer_text_y)
        status_text_area = label.Label(terminalio.FONT, text=status_text, color=self.palette[0])
        status_group.append(status_text_area)
        self.group.append(status_group)
        more_text =   "*More.."
        more_group = displayio.Group(scale=2, x=footer_text_start_x+footer_offset_x, y=footer_text_y)
        more_text_area = label.Label(terminalio.FONT, text=more_text, color=self.palette[0])
        more_group.append(more_text_area)
        self.group.append(more_group)
        return_text = "RETURN"
        return_group = displayio.Group(scale=2, x=footer_text_start_x+2*footer_offset_x, y=footer_text_y)
        return_text_area = label.Label(terminalio.FONT, text=return_text, color=self.palette[0])
        return_group.append(return_text_area)
        self.group.append(return_group)
        return self.group

    def update_values( self, instrument ):
        if instrument.main_menu_select in range( 10, 13 ): ### skip future use choices
            instrument.main_menu_select = 14
        if instrument.main_menu_select == 15:  ### skip future use *more option
            instrument.main_menu_select = 16
        if instrument.main_menu_select == 6:
            self.selection_rectangles[0].hidden = False
            if instrument.button_pressed:
                instrument.active_page_number = 9
                instrument.button_pressed = False
        else:
            self.selection_rectangles[0].hidden = True
        if instrument.main_menu_select == 7:
            self.selection_rectangles[1].hidden = False
            if instrument.button_pressed:
                instrument.active_page_number = 8
                instrument.button_pressed = False
        else:
            self.selection_rectangles[1].hidden = True
        if instrument.main_menu_select == 8:
            self.selection_rectangles[2].hidden = False
            if instrument.button_pressed:
                instrument.active_page_number = 5
                instrument.button_pressed = False
        else:
            self.selection_rectangles[2].hidden = True
        if instrument.main_menu_select == 9:
            if instrument.button_pressed:
                instrument.active_page_number = 7
                instrument.button_pressed = False
            self.selection_rectangles[3].hidden = False
        else:
            self.selection_rectangles[3].hidden = True
        if instrument.main_menu_select == 10:
            self.selection_rectangles[4].hidden = False
        else:
            self.selection_rectangles[4].hidden = True
        if instrument.main_menu_select == 11:
            self.selection_rectangles[5].hidden = False
        else:
            self.selection_rectangles[5].hidden = True
        if instrument.main_menu_select == 12:
            self.selection_rectangles[6].hidden = False
        else:
            self.selection_rectangles[6].hidden = True
        if instrument.main_menu_select == 13:
            self.selection_rectangles[7].hidden = False
        else:
            self.selection_rectangles[7].hidden = True
        if instrument.main_menu_select == 14:
            self.selection_rectangles[8].hidden = False
            if instrument.button_pressed:
                instrument.active_page_number = 3
                instrument.button_pressed = False
        else:
            self.selection_rectangles[8].hidden = True
        if instrument.main_menu_select == 15:
            self.selection_rectangles[9].hidden = False
        else:
            self.selection_rectangles[9].hidden = True
        if instrument.main_menu_select == 16:
            self.selection_rectangles[10].hidden = False
            if instrument.button_pressed:
                print("TBD go back to previous page" )
                instrument.button_pressed = False
        else:
            self.selection_rectangles[10].hidden = True


def make_main_menu_page( instrument ):
    instrument.welcome_page.announce( "make_main_menu_page" )
    page = Main_Menu_Page(instrument.palette)
    group = page.make_group()
    page.hide()
    instrument.main_display_group.append( group )
    instrument.pages_list.append( page )
    return page
