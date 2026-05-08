"""
Connect to wifi.
Exports socket_pool(), connected()

You must setup the file CIRCUITPY/settings.toml:
    CIRCUITPY_WIFI_SSID="Your WiFi SSID Here"
    CIRCUITPY_WIFI_PASSWORD="Your WiFi Password Here"

# Usage

## Test as standalone:

    copy this to CIRCUITPY/code.py

NB: the wifi connection seems to be cached across at least reloads,
so, you may get a wifi connection with previous settings.toml at boot,
before code.py can run.
But, this code will re-connect with the new settings.toml, so you can change
the wifi ssid.

"""

DEBUG=False # verbosity

# Detect required hardware (and other resources)

# can't do wifi if no ssid/password
import os,sys
ssid = os.getenv("CIRCUITPY_WIFI_SSID", None)
password = os.getenv("CIRCUITPY_WIFI_PASSWORD", None)
wifi = None # the module when we import it

class NullWifi:
    """minimal api for null operation
    """
    def __init__(self, instrument):
        self.instrument = instrument
    def update(self):
        pass

# Password can be None for some ssid's (distinct from the empty string ""!)
if ssid==None:
    print("No wifi: no settings.toml `CIRCUITPY_WIFI_SSID` (and maybe CIRCUITPY_WIFI_PASSWORD)")
    # GC us
    def initialize(instrument):
        return NullWifi(instrument)
else:

    # need wifi library
    try:
        import wifi
    except ImportError as e:
        if not str(e).endswith("'wifi'"):
            raise e
        # The module isn't there
        # this module usually means "built-in" wifi
        # fixme: another `devices` module for external wifi

if wifi==None:
    print("No wifi: no `wifi` (built-in) python module")
    # GC us
    def initialize(instrument):
        return NullWifi(instrument)

# (actual connection is a dynamic issue)
else:
    # Hardware (and "resources") detected!
    print("wifi supported")

    import socketpool
    from software_modules import every
    Every = every.Every
    from software_modules import micro_observable
    Observable = micro_observable.Observable

    class WifiModule(NullWifi, Observable):
        """for the main loop
        """
        # try not to be too intrusive when we retry the wifi connection
        # FIXME: check if async can help avoid blocking here?
        connect_retry = Every(30) # and immediately

        _subscribable = 'wifi_enabled'

        def __init__(self, *args, **kwargs):
            NullWifi.__init__(self, *args, **kwargs)
            Observable.__init__(self)
            self.inet = wifi.radio # for non-socket services, e.g. mdns
            self.first_time = True
            # this is nice: immediately react to saved-setting (if any)
            # and if !enabled, ensures radio etc is off
            self.last_wifi_enabled = None


        def socket_pool(self):
            return socketpool.SocketPool(wifi.radio)

        def is_connected(self):
            return wifi.radio.connected if wifi else False

        def ipv4_address(self):
            return wifi.radio.ipv4_address

        def connected(self):
            # NB: the wifi connection seems to be cached across at least reloads
            # so, before code.py, the device will try to connect to wifi
            # we force a re-connection with the current settings.toml (first_time==True)
            # fixme: does that cause anything if the ssid/pass is the same?

            if self.first_time or (not self.is_connected() and self.connect_retry()):
                try:
                    try:
                        # Connect to the Wi-Fi network
                        wifi.radio.connect(ssid, password)
                        print(f"Wifi {ssid} : {wifi.radio.ipv4_address}")
                        self.publish( 'wifi_enabled', True )
                        return True

                    except OSError as e:
                        if 'No network with that ssid' in str(e):
                            if self.first_time or DEBUG:
                                print(f"no wifi w/ssid {ssid}")
                        else:
                            raise e
                finally:
                    self.first_time = False
            else:
                return wifi.radio.connected

        def update(self):
            if self.last_wifi_enabled != self.instrument.wifi_enabled:
                self.last_wifi_enabled = self.instrument.wifi_enabled
                if self.instrument.wifi_enabled:
                    print(f"wifi START")
                    wifi.radio.enabled = True
                    first_time = True
                else:
                    print(f"wifi STOP")
                    self.publish( 'wifi_enabled', False ) # disconnecting
                    wifi.radio.enabled = False

            if self.instrument.wifi_enabled:
                self.connected() # side-effect is to connect/re-connect

    # The Object
    wifi_module = WifiModule(None)

    def initialize(instrument):
        wifi_module.instrument = instrument
        return wifi_module

if __name__ == "__main__":
    print("Standalone test")
    DEBUG=True
    # no initialize()
    if 'socket_pool': # proxy for "if devices.wifi"
        initialize(None)
        while True:
            wifi_module.update()
    else:
        print("Exit, no wifi")

