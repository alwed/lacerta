#!/usr/bin/env python3

import sys, time, os
import socket
import threading
import json
from datetime import datetime
import signal
import gzip
from http.client import HTTPSConnection, HTTPException

from pits_info import pits_info

WENET_TELEMETRY_UDP_PORT    = 7891
PITS_INFO_PACKET_ID         = 0x80

host = "api.v2.sondehub.org"
resource = "/amateur/telemetry"

headers = {
        "Host": host,
        "User-Agent": "lacerta/0.1",
        "Content-Encoding": "gzip",
        "Content-Type" : "application/json",
}


class SyncAccu(object):
    """Accumulate objects to be fetched together"""
    def __init__(self):
        self.lock = threading.Lock()
        self.items = []

    def put(self, item):
        with self.lock:
            self.items.append(item)

    def getAll(self):
        with self.lock:
            items, self.items = self.items, []
        return items

upload_queue = SyncAccu()

def sigterm_handler(_signo, _stack_frame):
    # Raises SystemExit(0):
    sys.exit(0)

def gps_fix_str(fix):
    if fix == 0:
        return "none"
    elif fix == 2:
        return "2D"
    elif fix == 3:
        return "3D"
    elif fix == 5:
        return "time"
    else:
        return "error"

def queue_upload(pits, user_callsign="N0CALL"):
    mytime = datetime.utcnow().isoformat("T") + "Z"
    t = int(round(pits.time / 1000))
    sondetime = datetime.utcfromtimestamp(t).isoformat("T") + "Z"
    data = {
        "software_name" : "lacerta",
        "software_version" : "0.1",
        "uploader_callsign" : user_callsign,
        "time_received" : mytime,
        "payload_callsign" : pits.call,
        "datetime" : sondetime,
        "lat" : pits.lat,
        "lon" : pits.lon,
        "alt" : pits.alt,
        "ext_pressure" : pits.p / 100,
        "speed" : pits.speed_g,
        "ascent_rate" : pits.speed_v,
        "heading" : pits.heading,
        "sats" : pits.numSV,
        "batt" : pits.vbat,
        "i_sys" : pits.isys,
    }

    if pits.Ti > 0:
        data["temp"] = round(pits.Ti - 273.15, 2)
    if pits.Te > 0:
        data["ext_temperature"] = round(pits.Te - 273.15, 2)
    if pits.Ti > 0:
        data["soc_temperature"] = round(pits.Ts - 273.15, 2)

    upload_queue.put(data)

class SondehubUploader(threading.Thread):
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
        conn = HTTPSConnection(host, timeout=10)
        while self.running:
            time.sleep(1)

            data = upload_queue.getAll()
            if len(data) == 0:
                continue
            dataz = gzip.compress(json.dumps(data).encode("utf-8"))

            retrys = 0
            while self.running and retrys < 5:
                headers["Date"] = datetime.utcnow().isoformat("T") + "Z"
                try:
                    conn.request("PUT", resource, dataz, headers)
                    res = conn.getresponse()
                    if res.status == 200:
                        print("Telemetry upload successful", len(data))
                        break
                    elif res.status == 500:
                        retrys += 1
                    else:
                        print("Sondehub: %d: %s\n\t%s" % (res.status, res.reason, r.decode()))
                        break
                except (HTTPException, OSError) as e:
                    conn.close()
                    print("Failed to upload to Sondehub: %s %s" % (
                    type(e), str(e)))
                    time.sleep(10)
            conn.close()
            time.sleep(9)

if __name__ == "__main__":
    try:
        usercall = os.environ["MYCALL"]
    except KeyError:
        usercall = "anonymous"
    if len(sys.argv) > 1:
        usercall = sys.argv[1]

    signal.signal(signal.SIGTERM, sigterm_handler)

    upload_thrd = SondehubUploader()
    upload_thrd.start()

    s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    s.settimeout(1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except:
        pass
    s.bind(('',WENET_TELEMETRY_UDP_PORT))
    print("Started UDP Listener")

    pits = pits_info(False)

    while True:
        try:
            m = s.recv(2048).decode()
            m = json.loads(m)
            m = bytes(m["packet"])
            if m[0] != PITS_INFO_PACKET_ID or len(m) < pits.struct.size:
                continue

            pits.read(m[1:], scale=True)
            if pits.gpsFix == 3:
                queue_upload(pits, usercall)

        except socket.timeout:
            continue
        except (KeyboardInterrupt, SystemExit):
            break
        except Exception as e:
            print("Error in UDP-Listener:", str(e))
            break

    print("Closing UDP Listener")
    s.close()
    upload_thrd.join()
