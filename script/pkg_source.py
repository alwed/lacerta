#!/usr/bin/env python3

import sys, os, time, struct
import threading, queue

from rfm98w import Rfm98wFsk
from pits_info import pits_shm, ssdv_encode_callsign

try:
    call = os.environ["MYCALL"]
except:
    call = "N0CALL"

call = ssdv_encode_callsign(call[:9])
txfo = sys.stdout.buffer
ssdv_path = "/dev/shm/send.ssdv"

chunksize = 14  # 50e3 / ((12*8 + 2580) * 10/8) ≈ 14.95 => 14*ssdv + 1*telemetry

shm = pits_shm("/dev/shm/pits.shm")
struct_format = "QIIIIIiiHHHHiHH"
pits_struct = struct.Struct("@" + struct_format)
telemetry_struct = struct.Struct(">" + struct_format)

def get_telemetry():
    pits = pits_struct.unpack_from(shm)
    return b"\x80" + call[:6] + telemetry_struct.pack(*pits)[2:]


def ceildiv(a, b):
    return -(-a // b)

image_queue = queue.Queue()

text_message = b""
last_telemetry_pkg = get_telemetry()
dummy_frame = b"\xFF" + os.urandom(255)

def format_telemetry_payload():
    global last_telemetry_pkg

    t1 = get_telemetry()
    t2 = last_telemetry_pkg
    last_telemetry_pkg = t1

    frame = bytearray(256)
    frame[:64] = t2
    frame[64:128] = t1

    try:
        lt = len(text_message)
    except:
        lt = 0
    if lt > 0:
        frame[128] = 0x79
        frame[129:129+lt] = text_message[:127]
        if lt < 126:
            frame[129+lt+1] = os.urandom(127 - lt)
    else:
        frame[128:] = dummy_frame[:128]

    return frame

class ImageHandler(threading.Thread):
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
        while self.running:
            if image_queue.empty() and os.path.exists(ssdv_path):
                time.sleep(.5)
                npkgs = os.path.getsize(ssdv_path) // 256
                nchks = ceildiv(npkgs, chunksize)
                #print(npkgs, file=sys.stderr)

                with open(ssdv_path, "rb") as f:
                    for i in range(nchks):
                        chunk = f.read(256 * chunksize)
                        if len(chunk) > 0 and len(chunk) % 256 == 0:
                            image_queue.put(chunk)

                os.unlink(ssdv_path)

image_thrd = ImageHandler()

fsk = Rfm98wFsk()
#fsk.standby()
fsk.set_frequency(434.1e6)

image_thrd.start()
fsk.tx()

try:
    while True:
        txfo.write(format_telemetry_payload())

        try:
            txfo.write(image_queue.get(block = False))
        except queue.Empty:
            for _ in range(chunksize):
                txfo.write(dummy_frame)
except (KeyboardInterrupt, SystemExit):
    pass

finally:
    txfo.write(dummy_frame)
    time.sleep(1)
    fsk.sleep()
    image_thrd.join()
