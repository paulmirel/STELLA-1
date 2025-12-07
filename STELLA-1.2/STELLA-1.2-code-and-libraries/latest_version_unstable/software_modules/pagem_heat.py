# heat page module
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

import displayio
from adafruit_display_text import label
import vectorio
import terminalio
from .classm_page import Page

class Heat_Page( Page ):
    def __init__( self, instrument ):
        super().__init__()
        self.page_name = "Heat"
        self.instrument = instrument
        self.palette = instrument.palette
        self.selection = 0
        self.last_selection = 0
        self.selection_count = 1
        self.field_selected = False
    def make_group( self ):
        self.group = displayio.Group()
        start_y = 54
        status_background = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=320, height=240-start_y, x=0, y=start_y )
        self.group.append( status_background )


        label_x_start = 12
        value_x_start = label_x_start
        value_y_start = 64
        column_spacing = 106
        label_y_start = value_y_start  + 30

        label_group = displayio.Group(scale=1, x=label_x_start, y=label_y_start)
        label_text = "Tsurface"
        label_text_area = label.Label(terminalio.FONT, text=label_text, color=self.palette[0])
        label_group.append(label_text_area)
        self.group.append(label_group)

        value_group = displayio.Group(scale=2, x=value_x_start, y=value_y_start)
        value_text = "100.0C"
        self.tsurface_text_area = label.Label(terminalio.FONT, text=value_text, color=self.palette[0])
        value_group.append(self.tsurface_text_area)
        self.group.append(value_group)

        label_group = displayio.Group(scale=1, x=label_x_start+int(2*column_spacing/3), y=label_y_start)
        label_text = "-"
        label_text_area = label.Label(terminalio.FONT, text=label_text, color=self.palette[0])
        label_group.append(label_text_area)
        self.group.append(label_group)

        label_group = displayio.Group(scale=1, x=label_x_start+column_spacing, y=label_y_start)
        label_text = "Tair"
        label_text_area = label.Label(terminalio.FONT, text=label_text, color=self.palette[0])
        label_group.append(label_text_area)
        self.group.append(label_group)

        value_group = displayio.Group(scale=2, x=value_x_start+column_spacing, y=value_y_start)
        value_text = "100.0C"
        self.tair_text_area = label.Label(terminalio.FONT, text=value_text, color=self.palette[0])
        value_group.append(self.tair_text_area)
        self.group.append(value_group)

        label_group = displayio.Group(scale=1, x=label_x_start+int(3*column_spacing/2), y=label_y_start)
        label_text = "="
        label_text_area = label.Label(terminalio.FONT, text=label_text, color=self.palette[0])
        label_group.append(label_text_area)
        self.group.append(label_group)

        label_group = displayio.Group(scale=1, x=label_x_start+2*column_spacing, y=label_y_start)
        label_text = "Tdiff"
        label_text_area = label.Label(terminalio.FONT, text=label_text, color=self.palette[0])
        label_group.append(label_text_area)
        self.group.append(label_group)

        value_group = displayio.Group(scale=2, x=value_x_start+2*column_spacing, y=value_y_start)
        value_text = "100.0C"
        self.tdiff_text_area = label.Label(terminalio.FONT, text=value_text, color=self.palette[0])
        value_group.append(self.tdiff_text_area)
        self.group.append(value_group)


        self.selection_rectangles = []
        select_width = 4
        offset = 4

        # lower controls
        separator_bar_height = 2
        lower_control_height = 14
        lower_select_y = 240 - offset - separator_bar_height - lower_control_height - select_width
        lower_select_height = lower_control_height + 2*select_width
        lower_control_y = lower_select_y + select_width
        lower_text_y = lower_control_y + 6
        # data_source
        data_source_select_x = offset
        data_source_color_x = data_source_select_x + select_width
        data_source_select_width = 50
        self.data_source_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=data_source_select_width, height=lower_select_height, x=data_source_select_x, y=lower_select_y)
        self.group.append( self.data_source_select )
        self.selection_rectangles.append(self.data_source_select)

        self.data_source_select.hidden = True
        data_source_control_width = data_source_select_width - 2 * select_width
        self.data_source_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=data_source_control_width, height=lower_control_height, x=data_source_color_x, y=lower_control_y)
        self.group.append( self.data_source_color )
        data_source_text_x = data_source_color_x + 3
        data_source_group = displayio.Group(scale=1, x=data_source_text_x, y=lower_text_y)
        data_source_text = "s/ref"
        self.data_source_text_area = label.Label(terminalio.FONT, text=data_source_text, color=self.palette[0])
        data_source_group.append(self.data_source_text_area)
        self.group.append(data_source_group)


        #graph_settings
        graph_settings_select_x = offset + data_source_select_width
        graph_settings_color_x = graph_settings_select_x + select_width
        graph_settings_select_width = 36
        self.graph_settings_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=graph_settings_select_width, height=lower_select_height, x=graph_settings_select_x, y=lower_select_y)
        self.group.append( self.graph_settings_select )
        self.selection_rectangles.append(self.graph_settings_select)

        self.graph_settings_select.hidden = True
        graph_settings_control_width = graph_settings_select_width - 2 * select_width
        self.graph_settings_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=graph_settings_control_width, height=lower_control_height, x=graph_settings_color_x, y=lower_control_y)
        self.group.append( self.graph_settings_color )
        graph_settings_text_x = graph_settings_color_x + 3
        graph_settings_group = displayio.Group(scale=1, x=graph_settings_text_x, y=lower_text_y)
        graph_settings_text = "set"
        self.graph_settings_text_area = label.Label(terminalio.FONT, text=graph_settings_text, color=self.palette[0])
        graph_settings_group.append(self.graph_settings_text_area)
        self.group.append(graph_settings_group)

        # units_x
        units_x_select_x = offset + data_source_control_width +graph_settings_select_width
        units_x_color_x = units_x_select_x + select_width
        units_x_select_width = 96
        self.units_x_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=units_x_select_width, height=lower_select_height, x=units_x_select_x, y=lower_select_y)
        self.group.append( self.units_x_select )
        self.selection_rectangles.append(self.units_x_select)

        self.units_x_select.hidden = True
        units_x_control_width = units_x_select_width - 2 * select_width
        self.units_x_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=units_x_control_width, height=lower_control_height, x=units_x_color_x, y=lower_control_y)
        self.group.append( self.units_x_color )
        units_x_text_x = units_x_color_x + 4
        units_x_group = displayio.Group(scale=1, x=units_x_text_x, y=lower_text_y)
        units_x_text = "wavelength nm"
        self.units_x_text_area = label.Label(terminalio.FONT, text=units_x_text, color=self.palette[0])
        units_x_group.append(self.units_x_text_area)
        self.group.append(units_x_group)

        # table / graph
        table_graph_select_width = 46
        table_graph_select_x = offset + data_source_control_width + graph_settings_control_width + units_x_control_width
        table_graph_color_x = table_graph_select_x + select_width
        self.table_graph_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=table_graph_select_width, height=lower_select_height, x=table_graph_select_x, y=lower_select_y)
        self.group.append( self.table_graph_select )
        self.selection_rectangles.append(self.table_graph_select)

        self.table_graph_select.hidden = True
        table_graph_control_width = table_graph_select_width - 2 * select_width
        self.table_graph_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=table_graph_control_width, height=lower_control_height, x=table_graph_color_x, y=lower_control_y)
        self.group.append( self.table_graph_color )
        table_graph_text_x = table_graph_color_x + 3
        table_graph_group = displayio.Group(scale=1, x=table_graph_text_x, y=lower_text_y)
        table_graph_text = "table"
        self.table_graph_text_area = label.Label(terminalio.FONT, text=table_graph_text, color=self.palette[0])
        table_graph_group.append(self.table_graph_text_area)
        self.group.append(table_graph_group)


        # live
        live_select_width = 36
        live_select_x = offset + data_source_control_width + graph_settings_control_width + units_x_control_width + table_graph_select_width
        live_color_x = live_select_x + select_width
        self.live_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=live_select_width, height=lower_select_height, x=live_select_x, y=lower_select_y)
        self.group.append( self.live_select )
        self.selection_rectangles.append(self.live_select)

        self.live_select.hidden = True
        live_control_width = live_select_width - 2 * select_width
        self.live_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=live_control_width, height=lower_control_height, x=live_color_x, y=lower_control_y)
        self.group.append( self.live_color )
        live_text_x = live_color_x + 3
        live_group = displayio.Group(scale=1, x=live_text_x, y=lower_text_y)
        live_text = "LIVE"
        self.live_text_area = label.Label(terminalio.FONT, text=live_text, color=self.palette[0])
        live_group.append(self.live_text_area)
        self.group.append(live_group)


        return_select_width = 50
        return_select_x = 320 - offset - return_select_width
        return_color_x = return_select_x + select_width
        self.return_select = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=return_select_width, height=lower_select_height, x=return_select_x, y=lower_select_y)
        self.group.append( self.return_select )
        self.selection_rectangles.append(self.return_select)
        self.selection_count = len( self.selection_rectangles )
        self.return_select.hidden = True
        return_control_width = return_select_width - 2 * select_width
        self.return_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=19, width=return_control_width, height=lower_control_height, x=return_color_x, y=lower_control_y)
        self.group.append( self.return_color )
        return_text_x = return_color_x + 3
        return_group = displayio.Group(scale=1, x=return_text_x, y=lower_text_y)
        return_text = "RETURN"
        self.return_text_area = label.Label(terminalio.FONT, text=return_text, color=self.palette[0])
        return_group.append(self.return_text_area)
        self.group.append(return_group)

        '''
        title_bar = vectorio.Rectangle(pixel_shader=self.palette, color_index=19, width=320-2*5, height=24, x=0+5, y=start_y)
        self.group.append( title_bar )
        title_group = displayio.Group(scale=2, x=100, y=12+start_y)
        title_text = "Heat"
        title_text_area = label.Label(terminalio.FONT, text=title_text, color=self.palette[0])
        title_group.append(title_text_area)
        self.group.append(title_group)
        '''
        '''
        #selection rectangles
        selection_start_x = 2
        selection_start_y = 78
        selection_offset_x = 158
        selection_offset_y = 31

        '''
        '''
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
        self.selection_count += 1

        choice_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=menu_color_list[1],
            width=choice_width, height=36-2*selection_border, x=selection_start_x+selection_border+selection_offset_x, y=selection_start_y+selection_border))
        self.group.append( choice_rectangles[1] )
        self.selection_count += 1

        choice_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=menu_color_list[2],
            width=choice_width, height=36-2*selection_border, x=selection_start_x+selection_border, y=selection_start_y+selection_border+selection_offset_y))
        self.group.append( choice_rectangles[2] )
        self.selection_count += 1

        choice_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=menu_color_list[3],
            width=choice_width, height=36-2*selection_border, x=selection_start_x+selection_border+selection_offset_x, y=selection_start_y+selection_border+selection_offset_y))
        self.group.append( choice_rectangles[3] )
        self.selection_count += 1

        choice_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=menu_color_list[4],
            width=choice_width, height=36-2*selection_border, x=selection_start_x+selection_border, y=selection_start_y+selection_border+selection_offset_y*2))
        self.group.append( choice_rectangles[4] )
        self.selection_count += 1

        choice_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=menu_color_list[5],
            width=choice_width, height=36-2*selection_border, x=selection_start_x+selection_border+selection_offset_x, y=selection_start_y+selection_border+selection_offset_y*2))
        self.group.append( choice_rectangles[5] )
        self.selection_count += 1

        choice_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=menu_color_list[6],
            width=choice_width, height=36-2*selection_border, x=selection_start_x+selection_border, y=selection_start_y+selection_border+selection_offset_y*3))
        self.group.append( choice_rectangles[6] )
        self.selection_count += 1

        choice_rectangles.append( vectorio.Rectangle(pixel_shader=self.palette, color_index=menu_color_list[7],
            width=choice_width, height=36-2*selection_border, x=selection_start_x+selection_border+selection_offset_x, y=selection_start_y+selection_border+selection_offset_y*3))
        self.group.append( choice_rectangles[7] )
        self.selection_count += 1



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
        self.selection_count += 1

        more_text =   "*more.."
        more_group = displayio.Group(scale=2, x=footer_text_start_x+footer_offset_x, y=footer_text_y)
        more_text_area = label.Label(terminalio.FONT, text=more_text, color=self.palette[0])
        more_group.append(more_text_area)
        self.group.append(more_group)
        return_text = "RETURN"
        return_group = displayio.Group(scale=2, x=footer_text_start_x+2*footer_offset_x, y=footer_text_y)
        return_text_area = label.Label(terminalio.FONT, text=return_text, color=self.palette[0])
        return_group.append(return_text_area)
        self.group.append(return_group)
        self.selection_count += 1
        '''
        return self.group

    def update_selection( self ):
        self.selection_rectangles[self.last_selection].hidden = True
        self.selection_rectangles[self.selection].hidden = False

    def hide_all_selections( self ):
        for item in self.selection_rectangles:
            if item.hidden == False:
                item.hidden = True

    def action( self ):
        pass
        '''
        if self.selection == 0:
            self.instrument.active_page_number = self.instrument.pages_dict["Remote"]
        if self.selection == 1:
            self.instrument.active_page_number = self.instrument.pages_dict["Exposure"]
        if self.selection == 2:
            self.instrument.active_page_number = self.instrument.pages_dict["Air"]
        if self.selection == 3:
            self.instrument.active_page_number = self.instrument.pages_dict["Time"]
        if self.selection == 4:
            self.instrument.active_page_number = self.instrument.pages_dict["Sensors"]
        if self.selection == 8:
            self.instrument.active_page_number = self.instrument.pages_dict["Status"]
        if self.selection == 10:
            print( "return whence")
            self.instrument.active_page_number = self.instrument.previous_page_number

        '''



def make_heat_page( instrument ):
    instrument.welcome_page.announce( "make_heat_page" )
    page = Heat_Page(instrument)
    group = page.make_group()
    page.hide()
    instrument.main_display_group.append( group )
    instrument.pages_list.append( page )
    return page
