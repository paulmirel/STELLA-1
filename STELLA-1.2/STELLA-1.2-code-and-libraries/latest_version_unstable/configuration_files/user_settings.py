# instrument configuration file for STELLA-1.2
# set the data_source period = reciprocal of the data_source cadence
#               seconds + ( minutes ) + ( hours )   + ( days )
sample_interval_s = 3.0 + ( 0 * 60 ) + ( 0 * 3600 ) + ( 0 * 3600 * 24 )

burst_count = 2

record_on_startup = True

serial_out = True

serial_interval_s = 10.0 + ( 0 * 60 ) + ( 0 * 3600 ) + ( 0 * 3600 * 24 )

start_on_page = "main" # list choices here

# some instances of the STELLA-1.2 main board have a mosfet inverter on the 5V enable line,
# so that the 5V doesn't come on at boot (controller outputs are all high at boot)
inverted_5V_enable = False

