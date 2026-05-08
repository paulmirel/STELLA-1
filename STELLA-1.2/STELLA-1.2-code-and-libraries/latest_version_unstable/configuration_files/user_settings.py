# instrument configuration file for STELLA-1.2
# set the data_source period = reciprocal of the data_source cadence
#               seconds + ( minutes ) + ( hours )   + ( days )
sample_interval_s = 3.0 + ( 0 * 60 ) + ( 0 * 3600 ) + ( 0 * 3600 * 24 )

burst_count = 2

record_on_startup = False #True

serial_out_index = 2 #0 text, 1 json, 2 none

serial_interval_s = 10.0 + ( 0 * 60 ) + ( 0 * 3600 ) + ( 0 * 3600 * 24 )

wifi_enabled = True #False

start_on_page = "main" # list choices here


