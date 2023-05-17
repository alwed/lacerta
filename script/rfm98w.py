#!/usr/bin/env python3

import time
import spidev
import struct

def bytes_to_hex(Bytes):
    return ''.join(["0x%02X " % x for x in Bytes]).strip()

class Rfm98wFsk(object):
    FXOSC = 32000000    # Hz
    FSTEP = 61.03515625 # Hz

    config_common = [
    	0x09,			# FSK, low frequency, Standby
    	0x02, 0x80,		# 50 kBd
    	0x01, 0x9A,		# 50048.828125/2 Hz (976.5 ppm)
    	0x6C, 0x8C, 0xCD	# Carrier: 434.2 MHz
    ]

    config_tx = [
    	0x8f,			# 17dBm
    	0x09,			# no shaping, 40µs PA ramp
    	0x1B			# 100mA OCP
    ]

    config_packet = [0x00] * 17	# Continuous mode

    def __init__(self):
        self.spi = spidev.SpiDev()
        self.spi.open(0, 1) # TODO: make generic
        self.spi.bits_per_word = 8
        self.spi.mode = 0
        self.spi.max_speed_hz = 8000000 # 8 MHz

        self.register_write(0x01, self.config_common)
        self.register_write(0x09, self.config_tx)
        #self.register_write(0x0C, self.config_rx)
        self.register_write(0x25, self.config_packet)
        self.register_write(0x24, [0x07])	# RC osc off
        self.register_write(0x3B, [0x02])	# no automatic receiver calibration
        #self.register_write(0x5D, [0x06])	# BitrateFrac


    def __del__(self):
        self.sleep()
        self.spi.close()

    def register_read(self, addr, count=1):
        return self.spi.xfer([addr & 0x7F] + count * [0])[1:]

    def register_write(self, addr, data):
        self.spi.writebytes([addr | 0x80] + data)

    def sleep(self):
        x = (self.register_read(0x01)[0] & 0xF8) + 0
        self.register_write(0x01, [x])

#    def standby(self):
#        x = (self.register_read(0x01)[0] & 0xF8) + 3
#        self.register_write(0x01, [x])

    def tx(self):
        x = (self.register_read(0x01)[0] & 0xF8) + 3
        self.register_write(0x01, [x])

    def set_frequency(self, f):
        Frf = int(round(f / self.FSTEP))
        data = list(struct.pack(">I", Frf))[1:]
        self.register_write(0x06, data)
