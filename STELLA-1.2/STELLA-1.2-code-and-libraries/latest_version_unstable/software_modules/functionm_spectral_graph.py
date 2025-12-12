# spectral graph module
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

import displayio
from adafruit_display_text import label
import vectorio
import terminalio
from .classm_page import Page

class Spectral_Register:
    def __init__( self, instrument ):
        self.instrument = instrument
        self.scale_linear = True
        self.y_axis_irradiance = True
        self.scope = 0
        self.number_of_scope_choices = 6
        self.autoexposure = False
        self.lamps_on = False
        self.five_x_values = [[0,0,0,0,0],[0,0,0,0,0],[0,0,0,0,0],[0,0,0,0,0]]
        self.data_source = 0
        self.number_of_data_source_choices = 3
        self.x_axis_units = 0
        self.number_of_x_axis_units_choices = 4
        self.live = True
        self.number_of_plot_points = 0
        self.show_table = False
        self.wavelength_range = (410, 1000)
        self.wavelengths_to_plot = []
    def calculate_five_x_values( self ):
        c_m_per_s = 299792458
        nm_per_m = 10**9
        Hz_per_THz = 10**12
        h_e_V_per_Hz = 4.135667696/10**15
        self.five_x_values[0][2] = int( (self.five_x_values[0][0] + self.five_x_values[0][4])/2 )
        self.five_x_values[0][1] = int( (self.five_x_values[0][0] + self.five_x_values[0][2])/2 )
        self.five_x_values[0][3] = int( (self.five_x_values[0][2] + self.five_x_values[0][4])/2 )
        for index in range( 0, 5 ):
            self.five_x_values[1][index] = int((c_m_per_s / ((self.five_x_values[0][index])/nm_per_m))/Hz_per_THz) # frequency
            self.five_x_values[2][index] = round((self.five_x_values[1][index]* Hz_per_THz)*h_e_V_per_Hz,1)  # energy
            self.five_x_values[3][index] = int( 10000000/self.five_x_values[0][index] )  # wave number

def create_spectral_register( instrument ):
    spectral_register = Spectral_Register( instrument )
    return spectral_register


class Spectral_Graph_Page( Page ):
    def __init__( self, instrument, spectral_register ):
        super().__init__()
        self.instrument = instrument
        self.page_name = "Spectral_Graph"
        self.spectral_register = spectral_register
        self.palette = instrument.palette
        self.points = []

    def make_group( self ):
        self.group = displayio.Group()
        graph_x = 14 #4
        graph_width = 320 - graph_x *2
        graph_height = 240-124
        message_height = int( graph_height/4 )
        message_offset = 10
        graph_y = 80
        self.graph_pix_y0 = graph_y + graph_height
        self.graph_pix_x0 = graph_x
        self.graph_pix_xn = self.graph_pix_x0 + graph_width
        self.graph_pix_yn = self.graph_pix_y0 - graph_height
        graph_background = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9, width=graph_width, height=graph_height-4, x=graph_x, y=graph_y+4 )
        self.group.append( graph_background )
        ## make all the plot points, store them on the x-axis
        self.pixels_per_point = 2 #4
        self.point_height = 2
        self.number_of_points = int(graph_width / self.pixels_per_point)
        #print( "number_of_points", self.number_of_points )
        for index in range (0, self.number_of_points):
            #color_index = index % 10 or color_index = 0
            point = vectorio.Rectangle( pixel_shader=self.palette, color_index = 0 , width=self.pixels_per_point, height=self.point_height,
                        x=self.graph_pix_x0 + index*self.pixels_per_point, y=self.graph_pix_y0 - self.point_height )
            self.points.append(point)
            self.group.append(point)

        self.message_bar = vectorio.Rectangle( pixel_shader=self.palette, color_index = 9,
                        width=graph_width-2*message_offset, height=message_height,
                        x=self.graph_pix_x0+message_offset, y=self.graph_pix_y0 - message_offset - message_height )
        self.group.append( self.message_bar )
        self.message_bar.hidden = True
        message_group = displayio.Group(scale=2, x=self.graph_pix_x0+3*message_offset, y=self.graph_pix_y0 - message_height+4)
        message_text = "updating graph"
        self.message_text_area = label.Label(terminalio.FONT, text=message_text, color=self.palette[19])
        message_group.append(self.message_text_area)
        self.message_text_area.hidden = True
        self.group.append(message_group)

        # future function banner
        self.banner_group = displayio.Group()
        select_width = 2
        banner_width = 250
        banner_height = 60
        banner_x = 30
        banner_y = 110
        banner_color_x = banner_x + select_width
        banner_color_y = banner_y + select_width
        banner_border = vectorio.Rectangle(pixel_shader=self.palette, color_index=0, width=banner_width, height=banner_height, x=banner_x, y=banner_y)
        self.banner_group.append( banner_border )
        banner_color_width = banner_width - 2 * select_width
        banner_color_height = banner_height - 2 * select_width
        banner_color = vectorio.Rectangle(pixel_shader=self.palette, color_index=9, width=banner_color_width, height=banner_color_height, x=banner_color_x, y=banner_color_y)
        self.banner_group.append( banner_color )
        banner_text_x = banner_color_x + 3
        banner_text_y = banner_color_y + 12
        banner_text_group = displayio.Group(scale=2, x=banner_text_x, y=banner_text_y)
        banner_text = "*future function: "
        banner_text_area = label.Label(terminalio.FONT, text=banner_text, color=self.palette[0])
        banner_text_group.append(banner_text_area)
        self.banner_group.append(banner_text_group)
        self.banner_message_group = displayio.Group(scale=2, x=banner_text_x, y=banner_text_y+26)
        banner_message = "message goes here"
        self.banner_message_area = label.Label(terminalio.FONT, text=banner_message, color=self.palette[0])
        self.banner_message_group.append( self.banner_message_area )
        self.banner_group.append(self.banner_message_group)
        self.group.append( self.banner_group )
        self.banner_group.hidden = True

        return self.group

    def update_plot_data( self ):
        if self.spectral_register.live:
            data_dict_to_plot = {}
            if self.spectral_register.y_axis_irradiance:
                for spectral_sensor in self.instrument.spectral_sensors_present:
                    if spectral_sensor.pn == "as7256x":
                        spectral_sensor.read_fcal()
                        data_dict_to_plot.update( spectral_sensor.dict_fcal )
                    if spectral_sensor.pn == "as7331":
                        spectral_sensor.read_fcal()
                        data_dict_to_plot.update( spectral_sensor.dict_fcal )
                    if spectral_sensor.pn == "as7341":
                        spectral_sensor.read()
                        data_dict_to_plot.update( as7341_spectrometer.dict_stenocal )
            else:
                for spectral_sensor in self.instrument.spectral_sensors_present:
                    if spectral_sensor.pn == "as7256x":
                        spectral_sensor.read_counts()
                        data_dict_to_plot.update( spectral_sensor.dict_counts )
                    if spectral_sensor.pn == "as7331":
                        spectral_sensor.read_counts()
                        data_dict_to_plot.update( spectral_sensor.dict_counts )
                    if spectral_sensor.pn == "as7341":
                        spectral_sensor.read()
                        data_dict_to_plot.update( as7341_spectrometer.dict_counts )
            if self.spectral_register.scope == 0: # vis +nir
                wavelength_range = (410, 1000)
            if self.spectral_register.scope == 1: # vis
                wavelength_range = (410, 700)
            if self.spectral_register.scope == 2: # nir
                wavelength_range = (700, 1000)
            if self.spectral_register.scope == 3: # uv + vis + nir
                wavelength_range = (200, 1000)
            if self.spectral_register.scope == 4: # uv + vis
                wavelength_range = (200, 700)
            if self.spectral_register.scope == 5: # uv
                wavelength_range = (200, 400)
            wavelengths_to_plot = []
            for item in self.instrument.wavelength_bands_list_sorted:
                if item in range (wavelength_range[0], wavelength_range[1]):
                    wavelengths_to_plot.append(item)
            if wavelengths_to_plot != []:
                self.spectral_register.five_x_values[0][0] = wavelengths_to_plot[0]
                self.spectral_register.five_x_values[0][4] = wavelengths_to_plot[-1]
                self.spectral_register.calculate_five_x_values()
            else:
                self.spectral_register.scope = (self.spectral_register.scope +1) % self.spectral_register.number_of_scope_choices
            spectral_graph_x_values_nm = []
            spectral_bandwidths_nm = []
            spectral_graph_y_values = []
            for item in self.instrument.wavelength_bands_list_sorted:
                if item in range ( wavelength_range[0], wavelength_range[1]):
                    if data_dict_to_plot.get(item) is not None:
                        spectral_graph_x_values_nm.append( item )
                        for spectral_sensor in self.instrument.spectral_sensors_present:
                            bw = spectral_sensor.get_bandwidth(item)
                            if bw is not None:
                                spectral_bandwidths_nm.append(bw)
                        if self.spectral_register.scale_linear:
                            spectral_graph_y_values.append( data_dict_to_plot.get(item) )
                        else:
                            if data_dict_to_plot.get(item) < 1:
                                spectral_graph_y_values.append( 0 )
                            else:
                                spectral_graph_y_values.append( math.log(data_dict_to_plot.get(item),10))
            #print(spectral_bandwidths_nm)

            # TBD look up the bandwidth for each
            # TBD plot all the points. set their color, width, height, offset. Interpolate the inactive points.
            if spectral_graph_y_values:
                #print( spectral_graph_x_values_nm[0], spectral_graph_x_values_nm[-1])
                wavelength_nm_per_point = (spectral_graph_x_values_nm[-1] - spectral_graph_x_values_nm[0])/(self.number_of_points - 1 )
                #print( wavelength_nm_per_point )

                inactive_point_color = 19
                indicies_of_active_points = []
                point_wavelengths_nm = []  # wavelength for each point
                point_active = []       # boolean list, true if there's real data for that point
                point_colors = []       # color index for each point
                point_bandwidths = []   # bandwidth for each point ( 0 for inactive points )
                point_y_values = []     # y value in counts or irradiance for each point
                point_y_location = []   # display position in y pixels for each point: plot this value

                for value in spectral_graph_x_values_nm:
                    indicies_of_active_points.append(int( round((value - spectral_graph_x_values_nm[0]) / wavelength_nm_per_point,0)))

                slopes_delta_y_per_point = []
                for index in range ( 0, len(indicies_of_active_points)-1):
                    slopes_delta_y_per_point.append( (spectral_graph_y_values[index+1]-spectral_graph_y_values[index])/(indicies_of_active_points[index+1]-indicies_of_active_points[index]) )

                y_value_index = -1
                last_index = 0
                for index in range (0, self.number_of_points):
                    point_wavelengths_nm.append( spectral_graph_x_values_nm[0] + index * wavelength_nm_per_point)
                    if index in indicies_of_active_points:
                        y_value_index += 1
                        point_active.append( True )
                        bandwidth = spectral_bandwidths_nm[y_value_index]
                        wavelength = spectral_graph_x_values_nm[y_value_index]
                        if wavelength in range(390,420):
                            self.points[index].color_index = 25
                        if wavelength in range(420,450):
                            self.points[index].color_index = 26
                        if wavelength in range(450,470):
                            self.points[index].color_index = 27
                        if wavelength in range(470,500):
                            self.points[index].color_index = 28
                        if wavelength in range(500,520):
                            self.points[index].color_index = 29
                        if wavelength in range(520,550):
                            self.points[index].color_index = 30
                        if wavelength in range(550,570):
                            self.points[index].color_index = 31
                        if wavelength in range(570,600):
                            self.points[index].color_index = 32
                        if wavelength in range(600,630):
                            self.points[index].color_index = 33
                        if wavelength in range(630,660):
                            self.points[index].color_index = 34
                        if wavelength in range(660,690):
                            self.points[index].color_index = 35
                        if wavelength in range(690,720):
                            self.points[index].color_index = 36
                        if wavelength in range(720,745):
                            self.points[index].color_index = 37
                        if wavelength in range(745,785):
                            self.points[index].color_index = 38
                        if wavelength > 785 or wavelength < 390:
                            self.points[index].color_index = 0
                        bw_in_points = int( bandwidth/wavelength_nm_per_point )*self.pixels_per_point
                        self.points[index].width = bw_in_points
                        self.points[index].x = self.graph_pix_x0 + index*self.pixels_per_point - int(bw_in_points/2)
                        self.points[index].height = self.point_height *3
                        point_y_values.append( spectral_graph_y_values[ y_value_index ] )
                        last_index = index
                    else:
                        point_active.append( False )
                        self.points[index].color_index = 19
                        self.points[index].width = self.pixels_per_point
                        self.points[index].height = self.point_height
                        self.points[index].x=self.graph_pix_x0 + index*self.pixels_per_point
                        point_y_values.append( (index-last_index)*slopes_delta_y_per_point[y_value_index] + spectral_graph_y_values[ y_value_index ] )

                y_pixel_span = self.graph_pix_y0 - self.graph_pix_yn
                y_value_span = max( point_y_values ) -  min( point_y_values )
                if y_value_span > 0:
                    y_pix_per_value = y_pixel_span / y_value_span
                else:
                    y_pix_per_value = 1

                y_pix_coords = []
                for item in point_y_values:
                    y_pix_coords.append( self.graph_pix_y0 - self.point_height - int( y_pix_per_value *(item - min(point_y_values))) )

                for index in range (0, self.number_of_points):
                    #print( index, y_pix_coords[index] )
                    self.points[index].y = y_pix_coords[index]


def make_spectral_graph_page( instrument, spectral_register ):
    instrument.welcome_page.announce( "make_spectral_graph_page" )
    page = Spectral_Graph_Page( instrument, spectral_register )
    group = page.make_group()
    page.hide()
    instrument.main_display_group.append( group )
    instrument.pages_list.append( page )
    return page
