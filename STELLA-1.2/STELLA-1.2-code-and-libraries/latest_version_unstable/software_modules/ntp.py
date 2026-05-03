"""
Do ntp to set the rtc from internet timeservers (wifi/inet_wan).

Obviously we need some internet connection.

We try to load `software_modules.wifi` and then test the module
to see if the resource is available, And use the module's:

    .socket_pool()
    .subscribe()

## Configuration

    software_modules.ntp.NTP_CONFIG = { 'server' :'0.pool.ntp.org', 'tz_offset' : 0, 'cache_seconds' : 3600, 'socket_timeout' : 5 }

# Usage

Usage:
    .initialize(instrument)
    call .update() in your loop

"""

DEBUG=False # verbosity

# Detect required hardware ...

import sys

# need a inet connection
try:
    from software_modules import wifi as inet_lan
except ImportError as e:
    if not str(e).endswith("'software_modules.wifi'"):
        raise e
    inet_lan = None

if not inet_lan:
    print("❌ can't ntp: no wifi|inet_lan module")
    sys.modules[__name__] = None

# Have a module, and presumably hardware
# We may not have a connection though!

else:

    import os,time
    import rtc # fixme: conditional?
    import adafruit_ntp

    try:
        from software_modules import rtc as software_modules_rtc
    except ImportError as e:
        if not str(e).endswith("'software_modules.rtc'"):
            raise e
        print("Won't send time from ntp to rtc hardware, no rtc module")
        software_modules_rtc = None

    from software_modules import every 
    Every = every.Every

    NTP_CONFIG = { 'server' :'0.pool.ntp.org', 'tz_offset' : 0, 'cache_seconds' : 3600, 'socket_timeout' : 5 }
    
    ntp = None
    def initialize(instrument):
        global ntp
        ntp = adafruit_ntp.NTP(inet_lan.wifi_module.socket_pool(), **NTP_CONFIG)
        get_time()
        inet_lan.wifi_module.subscribe( _startup )

    def _startup( p, v ):
        global first_time
        if v:
            print(f"## NTP should try...")
            first_time = True
            retry_time.interval = retry_time.interval # hack to force restart and trigger now
            resync_time.interval = resync_time.interval
    
    def isodate( seconds ):
        ts = time.localtime(seconds)
        return f"{ts.tm_year:04d}-{ts.tm_mon:02d}-{ts.tm_mday:02d}T{ts.tm_hour:02d}:{ts.tm_min:02d}:{ts.tm_sec:02d}"

    resync_time = Every(8 * 60 * 60, True) # every 8 hours, and immediately
    retry_time = Every(1 * 60 * 60) # every 1 hours
    first_time = True
    _got_time = False

    def get_time():
        global _got_time, first_time
        if inet_lan.wifi_module.is_connected():
            if (_got_time and resync_time()) or (not _got_time and retry_time() ):
                print(f"## retrying...")
                try:
                    ntp_tuple = ntp.datetime
                except OSError as e:
                    if 'ETIMEDOUT' in str(e):
                        print(f"ntp timeout, try again later")
                        return
                    else:
                        raise e
                        
                rtc.RTC().datetime = ntp_tuple

                _got_time = True

                resync_time.start() # reset
                if first_time or DEBUG:
                    print(f"✅ ntp time {isodate(time.mktime(ntp_tuple))}")

                if software_modules_rtc:
                    software_modules_rtc.set_rtc( ntp_tuple )
                    if first_time or DEBUG:
                        print("✅ set rtc hardware")

                first_time = False
        else:
            pass
        
    def update():
        # resync periodically
        get_time()
