# instrument configuration file for STELLA-1.2
# set the data_source period = reciprocal of the data_source cadence
#               seconds + ( minutes ) + ( hours )   + ( days )
sample_interval_s = 10.0 + ( 0 * 60 ) + ( 0 * 3600 ) + ( 0 * 3600 * 24 )

burst_count = 3

record_on_startup = True #False

serial_out = True

serial_interval_s = 10.0 + ( 0 * 60 ) + ( 0 * 3600 ) + ( 0 * 3600 * 24 )


