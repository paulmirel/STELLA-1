# aqi function
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

def calculate_aqi_p( p25_reading, p100_reading ):
    gc.collect()
    p25_break_points = (0, 12, 12.1, 35.4, 35.5, 55.4, 55.5, 150.4, 150.5, 250.4, 250.5, 350.4, 350.5, 500.4)
    #print( p25_break_points )
    p100_break_points = (0, 54, 55, 154, 155, 254, 255, 354, 355, 424, 425, 504, 505, 604)
    #print( p100_break_points )
    AQI_levels = (0, 50, 51, 100, 101, 150, 151, 200, 201, 300, 301, 400, 401, 500)
    #print( AQI_levels )
    p25_index = 0
    p100_index = 0
    for i in range (len(AQI_levels)-1):
        if (p25_reading > p25_break_points[i] and p25_reading < p25_break_points[i+1]):
            p25_index = i
    #aqi = int((((ihi-ilo)/(bhi-blo))*(reading-blo))+ilo)
    aqi25 = int((((AQI_levels[p25_index+1] - AQI_levels[p25_index])/(p25_break_points[p25_index+1] - p25_break_points[p25_index]))*(p25_reading-p25_break_points[p25_index]))+AQI_levels[p25_index])
    #print(aqi25)
    for n in range (len(AQI_levels)-1):
        if (p100_reading > p100_break_points[i] and p100_reading < p100_break_points[i+1]):
            p100_index = i
    aqi100 = int((((AQI_levels[p100_index+1] - AQI_levels[p100_index])/(p100_break_points[p100_index+1] - p100_break_points[p100_index]))*(p100_reading-p25_break_points[p100_index]))+AQI_levels[p100_index])
    #print(aqi100)
    #print( p25_break_points[p25_index], p25_break_points[p25_index+1], AQI_levels[p25_index], AQI_levels[p25_index+1], p100_break_points[p100_index], p100_break_points[p100_index+1], AQI_levels[p100_index], AQI_levels[p100_index+1])
    if aqi100 > aqi25:
        return aqi100
    else:
        return aqi25
