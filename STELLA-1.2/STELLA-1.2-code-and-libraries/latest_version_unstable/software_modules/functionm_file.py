# file function
# Copyright NASA 2025 under MIT open source license
# Author Paul Mirel

import storage
import sdcardio

def initialize_sd_card( spi_bus, sd_cs_pin ):
    try:
        sdcard = sdcardio.SDCard( spi_bus, sd_cs_pin )
        vfs = storage.VfsFat(sdcard)
        storage.mount(vfs, "/sd")
        print( "SD card initialized" )
    except Exception as err:
        print("SD card fail: missing or full: {}".format(err))
        print( "*** The card may be missing, or you may need to create a folder named sd in the root directory of CIRCUITPY ***" )
        vfs = False
    return vfs

def write_line( instrument, system_log, line ):
    try:
        with open( "/sd/{}".format( instrument.filename ), "a" ) as f:
            f.write( "{}, ".format(system_log))
            f.write( "{}".format(line) )
            f.write( "\n" )
        return True
    except Exception as err:
        print( "failed to write to file: ", err )
        instrument.vfs = False
        return False

def evaluate_sdcard_storage( vfs, bytes_per_hour, verbose ):
    try:
        sdcard_status = os.statvfs("/sd")
        sdf_block_size = sdcard_status[0]
        sdf_blocks_avail = sdcard_status[4]
        storage_free_percent = sdf_blocks_avail/sdf_block_size *100
        #print( sdcard_status )
        #print( "bytes per block = {}".format(sdf_block_size))
        #print( "free blocks = {}".format(sdf_blocks_avail))
        sd_bytes_avail_B = sdf_blocks_avail * sdf_block_size
        sd_bytes_avail_MB = sd_bytes_avail_B/ 1000000
        #print( "MB available = {}".format(sd_bytes_avail_MB))
        sdfssize = sdcard_status[2]
        sdbytessize_MB = int (round(( sdfssize * sdf_block_size/ 1000000 ), 0))
        #print( "MB drive size = {}".format(sdbytessize_MB))
        sdbytessize_GB = int( round( sdbytessize_MB /1000, 0 ))
        sdavail_percent = int( sd_bytes_avail_MB/ sdbytessize_MB * 100)
        if verbose:
            if sdbytessize_GB < 1:
                print( "SD card space available = {} % of {} MB".format(sdavail_percent, sdbytessize_MB))
            else:
                print( "SD card space available = {} % of {} GB".format(sdavail_percent, sdbytessize_GB))
        if False:
            line_bytes_size = 200 #bytes_per_line
            line_capacity_remaining = int(sd_bytes_avail_MB * 1000000/ line_bytes_size)
            data_source_interval_s = 1.0
            lines_per_s= 1/sample_interval_s
            time_remaining_h = int( line_capacity_remaining * lines_per_s /3600 )
        time_remaining_h = sd_bytes_avail_B/ bytes_per_hour
        time_remaining_days = round(time_remaining_h/24, 1)
        if verbose:
            print( "data collection time remaining until this SD card is full: {} h = {} days".format(time_remaining_h, time_remaining_days))
    except Exception as err:
        print( err )
        time_remaining_h = False
    return time_remaining_h


def update_batch( datestamp ):
    try:
        with open( "/sd/batch.txt", "r" ) as b:
            try:
                previous_batchfile_string = b.readline()
                previous_datestamp = previous_batchfile_string[ 0:8 ]
                previous_batch_number = int( previous_batchfile_string[ 8: ])
            except ValueError:
                previous_batch_number = 0
            if datestamp == previous_datestamp:
                # this is the same day, so increment the batch number
                batch_number = previous_batch_number + 1
            else:
                # this is a different day, so start the batch number at 0
                batch_number = 0
    except OSError:
            print( "batch.txt file not found" )
            batch_number = 0
    batch_string = ( "{:03}".format( batch_number ))
    batch_file_string = datestamp + batch_string
    try:
        with open( "/sd/batch.txt", "w" ) as b:
            b.write( batch_file_string )
            b.write("\n")
    except OSError as err:
        print("Error: writing batch.txt {:}".format(err) )
    return batch_number

def update_filename( instrument ):
    # device_type, hardware_clock, new_header, batch_number
    timenow = instrument.hardware_clock.read()
    if timenow is not None:
        create_new_file = False
        filename_of_the_day = ("{}_data_{}{:02}{:02}-{}.csv".format(instrument.device_type, timenow.tm_year,timenow.tm_mon,timenow.tm_mday,instrument.batch_number))
        # create a dummy filename
        last_filename_in_use = ("{}_data_{}{:02}{:02}-{}.csv".format(instrument.device_type, 2000,01,01,0))
        # look up today's date
        current_datestamp = "{:04}{:02}{:02}".format( timenow.tm_year, timenow.tm_mon, timenow.tm_mday)
        # look up the last filename
        try:
            with open( "/sd/last_filename.txt", "r" ) as lfn:
                try:
                    last_filename_in_use = lfn.readline().rstrip()
                except ValueError as err:
                    print(err)
        except OSError:
            print( "last_filename.txt file not found, creating new last_filename.txt file" )
            try:
                with open ( "/sd/last_filename.txt", "w" ) as lfn:
                    lfn.write(filename_of_the_day)
            except:
                print( "unable to create last_filename.txt file")

        substrings = last_filename_in_use.split("_")
        date_batch = substrings[-1]
        substrings = date_batch.split("-")
        last_datestamp = substrings[0]
        if last_datestamp != current_datestamp:
            print( "new day, start a new file" )
            create_new_file = True
        else:
            try:
                with open( "/sd/{}".format(last_filename_in_use), "r" ) as lfn:
                    previous_header = lfn.readline().rstrip()
                    previous_header += "\n"
            except OSError as err:
                create_new_file = True
                print( "unable to open last filename: ", err )
                print( "creating new file" )
        filename_to_use = last_filename_in_use
        if create_new_file:
            filename_to_use = filename_of_the_day
            try:
                with open( "/sd/{}".format(filename_to_use), "w" ) as fn:
                    fn.write( instrument.header )
                    fn.write("\n")
            except OSError as err:
                print( err )
            try:
                with open ( "/sd/last_filename.txt", "w" ) as lfn:
                    lfn.write(filename_to_use)
            except:
                print( "unable to write to last_filename.txt file")

    else:
        filename_to_use = "{}_data_no_timestamp.csv".format(DEVICE_TYPE)
        try:
            with open( "/sd/{}".format(filename_to_use), "w" ) as fn:
                fn.write( new_header )
        except OSError as err:
            print( err )

    instrument.filename = filename_to_use
