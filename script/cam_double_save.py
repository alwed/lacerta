#!/usr/bin/env python3

import time
import picamera

res_true = (2592, 1944)	# PiCam V1
n = 21 # 1080p Monitor
res_send = (n * 4 * 16, n * 3 * 16)

with picamera.PiCamera(resolution = res_true) as camera:
    camera.awb_mode = "sunlight"
    camera.meter_mode = "matrix"
    time.sleep(2)
    camera.capture("/dev/shm/save.jpg", quality = 90)
    camera.capture("/dev/shm/scale.bmp", resize = res_send)
