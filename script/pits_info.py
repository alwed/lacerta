#! /usr/bin/env python3

import os, mmap, sys
import struct
import time
from collections import namedtuple
from datetime import datetime

ssdv_callsign_alphabet = '-0123456789---ABCDEFGHIJKLMNOPQRSTUVWXYZ'
def ssdv_encode_callsign(call):
    code = 0
    call = call[:9]
    y = 1
    for c in call:
        x = ssdv_callsign_alphabet.find(c)
        if x < 0:
            x = 0
        code += x * y
        y *= 40
    return struct.pack(">Q", code)[2:]

def ssdv_decode_callsign(code):
    code = bytearray(code)
    if len(code) == 4:
        code = struct.unpack('>I', code)[0]
    else:
        code = struct.unpack('>Q', b"\0\0" + code)[0]

    callsign = ''
    while code:
        callsign += ssdv_callsign_alphabet[code % 40]
        code //= 40

    return callsign

def pits_shm(shm_path, read_only = True):
    if read_only:
        open_flags = os.O_RDONLY
        mmap_flags = mmap.PROT_READ
    else:
        open_flags = os.O_RDWR | os.O_CREAT
        mmap_flags = mmap.PROT_READ | mmap.PROT_WRITE

    fd = os.open(shm_path, open_flags, 0o640)

    if not read_only and os.fstat(fd).st_size < mmap.PAGESIZE:
        os.lseek(fd, mmap.PAGESIZE, os.SEEK_SET)
        os.write(fd, b"\0")

    return mmap.mmap(fd, mmap.PAGESIZE, mmap.MAP_SHARED, mmap_flags)

class pits_info(object):
    ntup = namedtuple(  "pits_info",
                        "time, "
                        "lat, lon, alt, alt_max, speed_g, speed_v, "
                        "heading, gps_status, "
                        "Ts, Ti, Te, "
                        "p, "
                        "vbat, isys")

    def __init__(self, native_order = True):
        if native_order == True:
            struct_format = "@QIIIIIiiHHHHiHH"
        else:
            struct_format = ">6x6sIIIIIiiHHHHiHH"
        self.native_order = native_order
        self.struct = struct.Struct(struct_format)

        self.call = ""
        self.time = 0
        self.lat = 0
        self.lon = 0
        self.alt = 0
        self.alt_max = 42
        self.speed_g = 0
        self.speed_v = 0
        self.heading = 0
        self.gps_status = 0
        self.numSV = 0
        self.gpsFix = 0
        self.dynamic_model = 0
        self.Ts = 0
        self.Ti = 0
        self.Te = 0
        self.p = 0
        self.vbat = 0
        self.isys = 0
        self.comment = ""

    def read(self, packet, scale = True):
        t = self.struct.unpack(packet[:self.struct.size])
        self.__dict__.update(dict(self.ntup._make(t)._asdict()))

        if self.native_order == False:
            self.call = ssdv_decode_callsign(packet[:6])
            self.time = struct.unpack(">Q", b"\0\0" + packet[6:12])[0]

        self.numSV = (self.gps_status >> 10) & 0x3F
        self.gpsFix = (self.gps_status >> 8) & 0x03
        self.dynamic_model = self.gps_status & 0xFF

        if scale == True:
            self.lat *= 1e-7
            self.lon *= 1e-7
            self.alt *= 1e-3
            self.alt_max *= 1e-3
            self.speed_g *= 1e-2
            self.speed_v *= 1e-2
            self.heading *= 1e-5
            self.Ts *= 2**-6
            self.Ti *= 2**-6
            self.Te *= 2**-6
            self.vbat *= 2**-10
            self.isys *= 2**-14

if __name__ == "__main__":
    shm = pits_shm("/dev/shm/pits.shm")
    pits = pits_info()

    while True:
        pits.read(shm)
        timestamp = datetime.fromtimestamp(pits.time // 1000)

        print("%d %3d %10.7f %10.7f %8.3f %s" % (pits.gpsFix, pits.numSV,
                pits.lat, pits.lon, pits.alt, timestamp),
                end='\r')

        time.sleep(.1)
