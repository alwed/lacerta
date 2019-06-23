#!/usr/bin/env python3

import base64
import time
import datetime
import sys, os, glob
import traceback
import json
import threading, queue
from http.client import HTTPConnection, HTTPException

#ssdv_url = "http://ssdv.habhub.org/api/v0/packets"
ssdv_host = "ssdv.habhub.org"
ssdv_url = "/api/v0/packets"

upload_queue = queue.Queue(4096) # Limit memory consumption, as images are on disk, too

def ssdv_queue(packets, mycall="N0CALL"):
    encoded_pkgs = []
    for p in packets:
        encoded_pkgs.append({
                "type":     "packet",
                "packet":   base64.b64encode(p).decode('ascii'),
                "encoding": "base64",
                "received": datetime.datetime.utcnow()
                                    .strftime("%Y-%m-%dT%H:%M:%SZ"),
                "receiver": mycall
            })

    post_data = {
            "type":     "packets",
            "packets":  encoded_pkgs
    }

    upload_queue.put(post_data)

class ssdvUploader(threading.Thread):
    def __init__(self):
        self.running = False
        return super().__init__()

    def start(self):
        self.running = True
        return super().start()

    def join(self):
        self.running = False
        super().join()

    def run(self):
        data = None
        c = HTTPConnection(ssdv_host, timeout=10)
        while self.running:
            try:
                if data is None:
                    data = upload_queue.get(timeout = 2)

                c.request(
                    "POST",
                    ssdv_url,
                    json.dumps(data),
                    {"Content-Type": "application/json"}
                )

                res = c.getresponse()
                r = res.read()
                if res.status == 200:
                    print("Uploaded to habhub successfully")
                else:
                    print("%d: %s\n\t%s" % (res.status, res.reason, r.decode()))
                upload_queue.task_done()
                data = None

            except queue.Empty:
                continue
            except (HTTPException, OSError) as e:
                c.close()
                print("Failed to upload to habhub:\n\t%s %s" % (
                    type(e), str(e)))
                time.sleep(10)

def ssdv_upload_file(filename, callsign="N0CALL"):
    with open(filename, "rb") as f:
        b = f.read()
        if len(b) > 0 and len(b) % 256 == 0:
            pkgs = (b[i:i+256] for i in range(0, len(b), 256))
            print("Uploading %d packages... " % (len(b) // 256), file=sys.stderr)
            ssdv_queue(pkgs, callsign)

def ssdv_dir_watcher(glob_string="./rx_images/*.ssdv", check_time = 0.5, callsign="N0CALL"):
    # Check what's there now..
    rx_images = glob.glob(glob_string)
    print("Starting directory watch...")

    while True:
        try:
            time.sleep(check_time)

            # Check directory again.
            rx_images_temp = glob.glob(glob_string)
            if len(rx_images_temp) == 0:
                continue
            # Sort list. Image filenames are timestamps, so the last element in the array will be the latest image.
            rx_images_temp.sort()
            # Is there an new image?
            #if rx_images_temp[-1] not in rx_images:
            new_images = set(rx_images_temp) - set(rx_images)
            if len(new_images) > 0:
                # New image! Wait a little bit in case we're still writing to that file, then upload.
                time.sleep(0.5)
            for filename in new_images:
                #filename = rx_images_temp[-1]
                print("Found new image! Uploading: %s " % filename)
                ssdv_upload_file(filename,callsign=callsign)

            rx_images = rx_images_temp
        except KeyboardInterrupt:
            return
        except:
            traceback.print_exc()
            continue

if __name__ == "__main__":
    try:
        callsign = sys.argv[1]
        if len(callsign) > 9:
            callsign = callsign[:9]
    except:
        print("Usage: python ssdv_upload.py CALLSIGN &")
        sys.exit(1)

    print("Using callsign: %s" % callsign)

    upload_thrd = ssdvUploader()
    upload_thrd.start()

    ssdv_dir_watcher(callsign=callsign)

    ssdv_upload_file("rx_images/rx.tmp", callsign)
    upload_queue.join()
    upload_thrd.join()
