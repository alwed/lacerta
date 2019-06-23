#!/usr/bin/env python3

import sys, time
import socket
import threading, queue
import json
from datetime import datetime
from base64 import b64encode
from hashlib import sha256
from http.client import HTTPConnection, HTTPException

from pits_info import pits_info

WENET_TELEMETRY_UDP_PORT    = 7891
PITS_INFO_PACKET_ID         = 0x80

upload_queue = queue.Queue()

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

def xor_hex(pkg):
    cs = 0
    for x in pkg:
        cs ^= x

    return b"%02X" % cs

class pits_habitat(pits_info):
    def habitat_sentence(self):
        t = int(round(self.time / 1000))
        self.human_time = datetime.utcfromtimestamp(t).strftime("%H:%M:%S")
        sentence = (("$$%s,%d,%s,"+6*"%.7f,"+"%d,%s,"+5*"%.2f,"+"%d,%s") % (
                self.call,
                t, self.human_time,
                self.lat, self.lon, self.alt, self.speed_g/3.6, self.speed_v,
                self.heading,
                self.numSV, gps_fix_str(self.gpsFix),
                self.Ts - 273.15, self.Ti - 273.15, self.Te - 273.15,
                self.vbat, self.isys,
                self.p,
                self.comment
                )).encode()
        sentence += b"*" + xor_hex(sentence[2:]) + b"\n"
        return sentence

def habitat_queue(pits, user_callsign="N0CALL"):
    sb64 = b64encode(pits.habitat_sentence())
    date = datetime.utcnow().isoformat("T") + "Z"
    data = {
        "type": "payload_telemetry",
        "data": {"_raw" : sb64.decode()},
        "receivers": {
            user_callsign: {
                "time_created": date,
                "time_uploaded": date,
            },
        },
    }
    upload_queue.put(data)

class HabitatUploader(threading.Thread):
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
        c = HTTPConnection("habitat.habhub.org",timeout=10)
        while self.running:
            try:
                data = upload_queue.get(timeout = 2)

                c.request(
                    "PUT",
                    "/habitat/_design/payload_telemetry/_update/add_listener/%s" %                          sha256(data['data']['_raw'].encode()).hexdigest(),
                    json.dumps(data),
                    {"Content-Type": "application/json"}
                )

                res = c.getresponse()
                r = res.read()
                if res.status == 201:
                    print("Uploaded to Habitat successfully")
                else:
                    print("%d: %s\n\t%s" % (res.status, res.reason, r.decode()))
                upload_queue.task_done()

            except queue.Empty:
                continue
            except (HTTPException, OSError) as e:
                upload_queue.put(data)
                c.close()
                print("Failed to upload to Habitat:\n\t%s %s" % (
                    type(e), str(e)))
                time.sleep(10)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        usercall = sys.argv[1]
    else:
        usercall = "anonymous"

    upload_thrd = HabitatUploader()
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

    pits = pits_habitat(False)

    while True:
        try:
            m = s.recv(2048).decode()
            m = json.loads(m)
            m = bytes(m["packet"])
            if m[0] != PITS_INFO_PACKET_ID or len(m) < pits.struct.size:
                continue

            pits.read(m[1:], scale=True)
#            print(pits.habitat_sentence())
            if pits.gpsFix == 3:
                habitat_queue(pits, usercall)

        except socket.timeout:
            continue
        except KeyboardInterrupt:
            break
        except Exception as e:
            print("Error in UDP-Listener:", str(e))
            break

    print("Closing UDP Listener")
    s.close()
    upload_queue.join()
    upload_thrd.join()
