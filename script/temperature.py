#! /usr/bin/env python3

import os, sys
import time
import struct
from pits_info import pits_shm

# TODO: Read from environment or command line parameter
sens_intern_dev = "/sys/bus/w1/devices/28-0000081470eb"
sens_extern_dev = "/sys/bus/w1/devices/10-00080201b43e"
sens_system_dev = "/sys/class/thermal/thermal_zone0/temp"
shm_path = "/dev/shm/pits.shm"

class sens_temp(object):
    def __init__(self, device=None):
        if device is not None:
            self.open(device)

    def open(self, device):
        self.f = open(device, "rb")
    def close(self):
        self.f.close()
    def temp(self):
        pass

class w1_temp(sens_temp):
    def open(self, device):
        sens_temp.open(self, os.path.join(device, "w1_slave"))

    def temp(self):
        self.f.seek(0)
        l = self.f.readlines()
        T = float("NaN")
        try:
            if l[0].split()[-1] == b"YES":
               T = float(l[1].split()[-1][2:]) / 1000
        except Exception as e:
            print("Error reading 1w temperature:", e, file=sys.stderr)
        return T

class sys_temp(sens_temp):
    def temp(self):
        self.f.seek(0)
        try:
            thita = float(self.f.read()) / 1000
        except Exception as e:
            print("Error reading system temperature:", e, file=sys.stderr)
            thita = float("NaN")
        return thita

def C2pitsK(thita):
    try:
        T = int((thita + 273.15) * 2**6)
    except:
        T = 0
    return T

if __name__ == "__main__":
    shm = pits_shm(shm_path, False)
    sens_system = sys_temp(sens_system_dev)
    sens_intern = w1_temp(sens_intern_dev)
    sens_extern = w1_temp(sens_extern_dev)

    while True:
        try:
            Ts = C2pitsK(sens_system.temp())
            Ti = C2pitsK(sens_intern.temp())
            Te = C2pitsK(sens_extern.temp())

            shm[38:38+6] = struct.pack("@3H", Ts, Ti, Te)

#            print(Ts / 2**6, Ti / 2**6, Te / 2**6)

            time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            break
        except Exception as e:
            #pass
            print(e, file=sys.stderr)
