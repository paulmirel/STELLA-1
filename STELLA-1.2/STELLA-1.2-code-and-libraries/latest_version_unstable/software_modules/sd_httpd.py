"""
Run an http server to serve files from /sd (sd-card if it is mounted).
Insecure (no https).
Will advertise on mdns as http://{name}.local

Usage:
    .initialize(devicename e.g. {uid}-stella, port=default 80)
    call .loop() in your loop
"""
import os
DEBUG = os.getenv("DEBUG_HTTP", None)

MOUNT = '/sd'

# need a inet connection
try:
    from software_modules import wifi as inet_lan
except ImportError as e:
    if not str(e).endswith("'software_modules.wifi'"):
        raise e
    inet_lan = None
    print("Can't start http server, no wifi module")

if inet_lan:
    import time,re
    from software_modules import file_utils

    try:
        import adafruit_httpserver
        from adafruit_httpserver import ChunkedResponse, Request, Response, Server, MIMETypes
    except ImportError as e:
        if not "adafruit_httpserver" in str(e):
            raise e
        inet_lan = None
        print("Can't start http server, no lib/adafruit_httpserver")

if inet_lan:
    print("httpd for sd-card supported")

    # save memory by limiting mime-types to those that we use
    MIMETypes.configure(
        default_to="text/plain",
        # Unregistering unnecessary MIME types can save memory
        keep_for=[".html", ".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".ico"],
        # ones we use
        register={".csv": "text/csv"},
    )

HTTPServer = None
Port = None
def initialize(port=80):
    global HTTPServer,Port
    Port = port

    if not inet_lan:
        return

    if inet_lan.wifi_module.is_connected():
        p = ':' + str(Port) if Port != 80 else ''
        print(f"http://{inet_lan.wifi_module.ipv4_address()}{p}")

    HTTPServer = Server(inet_lan.wifi_module.socket_pool(), MOUNT, debug=not not DEBUG)

    def isodate( seconds ):
        ts = time.localtime(seconds)
        return f"{ts.tm_year:04d}-{ts.tm_mon:02d}-{ts.tm_mday:02d}T{ts.tm_hour:02d}:{ts.tm_min:02d}:{ts.tm_sec:02d}"

    # / would normally be /sd/index.html, but we want to generate that
    @HTTPServer.route("/")
    def file_list(request: Request):
        def body():
            used = 0

            # prelude
            yield "<html><head><title>SDCard Files</title></head>\n<body>\n"

            free,total = free_total(humanize=True)
            yield f"<p>{MOUNT}</p>"
            yield "<p>" + ((20-4)* '&nbsp;') + f"free {free}/{total}</p>"

            for basename in sorted(os.listdir( MOUNT )):
                filename = f"{MOUNT}/{basename}"

                if not file_utils.is_file(filename):
                    continue

                stat = os.stat( filename )
                mtime = stat[8] # .st_mtime
                size = stat[6] # .st_size
                used += size

                size_str = f"{size:8d}"
                size_str = re.sub(' ','&nbsp;',size_str)

                yield f"{isodate(mtime)}Z {size_str} <a href='{basename}'>{basename} </a><br/>\n"

            free,total = free_total(humanize=True)
            yield "<p>" + ((20-4)* '&nbsp;') + f"used {human_size(used)} free {free}/{total}</p>"

            yield "</body></html>"

        return ChunkedResponse(request, body, content_type="text/html")

    @HTTPServer.route("/hello")
    def base(request: Request):
        """
        Serve a default static plain text message.
        """
        return Response(request, "Hello from the CircuitPython HTTP Server!")

    @HTTPServer.route("/favicon.ico")
    def serve_favicon(request):
        return Response(request, "")

    def free_total(humanize=False):
        # the free and total bytes, humanized (K,M,G) if true
        bsize,_,blocks,bfree,*rest = os.statvfs(MOUNT)

        total = blocks*bsize
        free = bfree*bsize
        if humanize:
            return human_size(free), human_size(total)
        else:
            return free, total

    def human_size(byte_count):
        if byte_count <= 10*1024:
            return byte_count
        elif byte_count < 10*1024*1024:
            return f"{byte_count / 1024:0.1f}K"
        elif byte_count < 10*1024*1024*1024:
            return f"{byte_count / 1024/1024:0.1f}M"
        else:
            return f"{byte_count / 1024/1024/1024:0.1f}G"

was_connected = False

def _startup(n, wifi_enabled):
    global was_connected
    if wifi_enabled:
        was_connected = False # force re-start

    else:
        if was_connected:
            HTTPServer.stop()
        was_connected = False
        print("http disconnected (wifi|inet_lan)")

inet_lan.wifi_module.subscribe( _startup )

def update():
    global was_connected

    if not inet_lan:
        return

    # we start/stop as we detect the inet connection

    if inet_lan.wifi_module.is_connected():
        if was_connected:
            try:
                HTTPServer.poll()
            except ValueError as e:
                # crashes on bad connects
                if 'Unparseable' in str(e):
                    # it still prints the error (if debug?)
                    pass
                else:
                    raise e
            except adafruit_httpserver.exceptions.InvalidPathError as e:
                # file-not-exists, backslash, parent-dir
                print(str(e))
                # continue
            except BrokenPipeError:
                # safe to ignore
                pass

        else:
            url = f"http://{inet_lan.wifi_module.ipv4_address()}:{Port}"
            print(f"HTTP for sd-card starting as {url}")
            HTTPServer.start( str(inet_lan.wifi_module.ipv4_address()), port=Port)
            was_connected = True
    else:
        if was_connected:
            HTTPServer.stop()
            was_connected = False
            print("http disconnected (wifi|inet_lan)")

if __name__ == "__main__":
    print("Standalone test")

    if 'initialize' in globals(): # proxy for `if devices.mdns`
        DEBUG=True

        initialize()

        while True:
            update()
    else:
        print("Exit, no inet resource")
