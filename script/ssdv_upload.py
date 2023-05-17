#!/usr/bin/env python3
import glob
import json
import base64
import os, os.path
import datetime
import time
import sys
from http.client import HTTPConnection, HTTPException
import signal

host = "ssdv.habhub.org"
resource = "/api/v0/packets"
glob_string = "./rx_images/*.ssdv"
target_dir = "./rx_images/uploaded/"
headers = {"Host": host, "Content-Type" : "application/json"}

def sigterm_handler(_signo, _stack_frame):
    # Raises SystemExit(0):
    sys.exit(0)

def encode_images(rx_images, usercall):
    data = {"type" : "packets", "packets" : []}

    for path in rx_images:
        date = datetime.datetime.utcfromtimestamp(os.path.getmtime(path)) \
               .strftime("%Y-%m-%dT%H:%M:%SZ")
        with open(path, "rb") as f:
            b = f.read()
        if len(b) > 0 and len(b) % 256 == 0:
            pkgs = (b[i:i+256] for i in range(0, len(b), 256))
            print("Uploading %d packages... " % (len(b) // 256), file=sys.stderr)
            for p in pkgs:
                pkg_data = base64.b64encode(p).decode('ascii')
                pkg = {
                        "type" : "packet",
                        "packet" : pkg_data,
                        "encoding" : "base64",
                        "received" : date,
                        "receiver" : usercall
                }
                data["packets"].append(pkg)

    return json.dumps(data, indent=4).encode("utf-8")

if __name__ == "__main__":
    try:
        usercall = os.environ["MYCALL"]
    except KeyError:
        usercall = "anonymous"
    if len(sys.argv) > 1:
        usercall = sys.argv[1]

    signal.signal(signal.SIGTERM, sigterm_handler)

    try:
        os.mkdir(target_dir)
    except FileExistsError:
        pass

    conn = HTTPConnection(host, timeout=10)
    while True:
        try:
            time.sleep(1)
            rx_images = glob.glob(glob_string)
            if len(rx_images) == 0:
                continue
            rx_images.sort()
            # New image! Wait a little bit in case we're still writing to that file, then upload.
            time.sleep(0.5)
            data = encode_images(rx_images, usercall)

            while True:
                try:
                    conn.request("POST", resource, data, headers)

                    res = conn.getresponse()
                    if res.status == 200:
                        print("SSDV upload successful")
                    else:
                        print("Sondehub: %d: %s\n\t%s" % (res.status, res.reason, res.decode()))
                    break
                except (HTTPException, OSError) as e:
                    conn.close()
                    print("Failed to upload to Sondehub: %s %s" % (
                    type(e), str(e)))
                    time.sleep(10)

            conn.close()
            # Move uploaded images to the archive, so that they are not uploaded again
            for path in rx_images:
                os.replace(path, os.path.join(target_dir, os.path.basename(path)))

        except (KeyboardInterrupt, SystemExit):
            break
