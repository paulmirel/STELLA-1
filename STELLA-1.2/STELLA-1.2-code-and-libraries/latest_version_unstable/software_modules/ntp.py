"""
Do ntp to get the time from internet timeservers (wifi/inet_wan).

Obviously we need some internet connection.

We try to load `software_modules.wifi` and then test the module
to see if the resource is available, And use the module's:

    .socket_pool()
    .subscribe()

## Configuration

    software_modules.NTPTime.NTP_CONFIG = { 'server' :'0.pool.ntp.org', 'tz_offset' : 0, 'cache_seconds' : 3600, 'socket_timeout' : 5 }

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
    import adafruit_ntp
    from software_modules import micro_observable
    Observable = micro_observable.Observable

    from software_modules import every 
    Every = every.Every

    class NTPTime(Observable):
        _subscribable = 'timestruct'
        
        NTP_CONFIG = { 'server' :'0.pool.ntp.org', 'tz_offset' : 0, 'cache_seconds' : 3600, 'socket_timeout' : 5 }

        def __init__(self):
            Observable.__init__(self)
            self.ntp = adafruit_ntp.NTP(inet_lan.wifi_module.socket_pool(), **self.NTP_CONFIG)
            self.first_time = True
            self.resync_time = Every(8 * 60 * 60, True) # every 8 hours, and immediately
            self.retry_time = Every(1 * 60 * 60) # every 1 hours
            self._got_time = False

            inet_lan.wifi_module.subscribe( self._startup )
    
        def _startup(self, p, wifi_enabled ):
            if wifi_enabled:
                self.first_time = True
                self.retry_time.interval = self.retry_time.interval # hack to force restart and trigger now
                self.resync_time.interval = self.resync_time.interval
    
        def isodate(self, seconds ):
            ts = time.localtime(seconds)
            return f"{ts.tm_year:04d}-{ts.tm_mon:02d}-{ts.tm_mday:02d}T{ts.tm_hour:02d}:{ts.tm_min:02d}:{ts.tm_sec:02d}"

        def get_time(self):
            if inet_lan.wifi_module.is_connected():
                if (self._got_time and self.resync_time()) or (not self._got_time and self.retry_time() ):
                    print(f"NTP retrying...")
                    try:
                        ntp_tuple = self.ntp.datetime
                    except OSError as e:
                        if 'ETIMEDOUT' in str(e):
                            print(f"ntp timeout, try again later")
                            return
                        else:
                            raise e
                            
                    self.publish( 'timestruct', ntp_tuple )

                    self._got_time = True

                    self.resync_time.start() # reset
                    if self.first_time or DEBUG:
                        print(f"✅ ntp time {self.isodate(time.mktime(ntp_tuple))}")

                    self.first_time = False
            else:
                pass
            
        def update(self):
            # resync periodically
            self.get_time()

    def initialize():
        return NTPTime()
