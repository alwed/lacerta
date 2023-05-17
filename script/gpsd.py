#!/usr/bin/env python3

from ublox import *
from pits_info import pits_shm

from datetime import datetime
import struct
import ntpdshm

def debug_message(msg, **kwargs):
    print(msg)

def setup_ublox():
    global gps, update_rate_ms, dynamic_model
    gps.set_binary()
    gps.configure_poll_port()
    gps.configure_poll(CLASS_CFG, MSG_CFG_USB)
    gps.configure_port(port=PORT_SERIAL1, inMask=1, outMask=0)
    gps.configure_port(port=PORT_USB, inMask=1, outMask=1)
    gps.configure_port(port=PORT_SERIAL2, inMask=1, outMask=0)
    gps.configure_poll_port()
    gps.configure_poll_port(PORT_SERIAL1)
    gps.configure_poll_port(PORT_SERIAL2)
    gps.configure_poll_port(PORT_USB)
    gps.configure_solution_rate(rate_ms=update_rate_ms)

    gps.set_preferred_dynamic_model(dynamic_model)

    gps.configure_message_rate(CLASS_NAV, MSG_NAV_POSLLH, 1)
    gps.configure_message_rate(CLASS_NAV, MSG_NAV_STATUS, 1)
    gps.configure_message_rate(CLASS_NAV, MSG_NAV_SOL, 1)
    gps.configure_message_rate(CLASS_NAV, MSG_NAV_VELNED, 1)
    gps.configure_message_rate(CLASS_CFG, MSG_CFG_NAV5, 1)
    gps.configure_message_rate(CLASS_NAV, MSG_NAV_TIMEGPS, 1)
    gps.configure_message_rate(CLASS_NAV, MSG_NAV_CLOCK, 5)

def gps2unix_ms(gps_week, iTOW, leaps):
    gps_epoch = 315964800  # 1980-01-06T00:00Z
    return (gps_epoch + gps_week * 7 * 24 * 3600 - leaps) * 1000 + iTOW

shm= pits_shm("/dev/shm/pits.shm", read_only = False)
gps = UBlox("/dev/i2c-3", timeout=2)
#gps = UBlox("/dev/ttyACM0", timeout=2)

update_rate_ms = 1000
dynamic_model = DYNAMIC_MODEL_AIRBORNE1G

setup_ublox()

ntpd_shm = ntpdshm.NtpdShm(unit=2)
ntpd_shm.mode = 0
ntpd_shm.precision = -5
ntpd_shm.leap = 0 # leap second notifier implemented

rx_running = True
rx_counter = 0

gps_struct = struct.Struct("@QIIIIIiiH")
alt_max = 0

while rx_running:
    try:
        msg = gps.receive_message()
        msg_name = msg.name()
        #print(msg_name)
    except Exception as e:
        import traceback
        traceback.print_exc()
        debug_message("WARNING: GPS Failure. Attempting to reconnect.")
        numSV = 0
        # Attempt to re-open GPS.
        time.sleep(5)
        try:
            gps.close()
        except:
            pass

        try:
            gps = UBlox(self.port, self.baudrate, self.timeout)
            setup_ublox()
            debug_message("WARNING: GPS Re-connected.")
        except:
            continue

    #debug_message("%2d %s" % (len(msg.name()), msg.name()))

    # If we have received a message we care about, unpack it and update our state dict.
    if msg.name() == "NAV_SOL":
        msg.unpack()
        numSV = msg.numSV
        gpsFix = msg.gpsFix

    elif msg.name() == "NAV_POSLLH":
        msg.unpack()
        latitude = msg.Latitude #*1.0e-7
        longitude = msg.Longitude #*1.0e-7
        altitude = msg.hMSL #msg.height #*1.0e-3
        if altitude > alt_max and gpsFix == 3:
            alt_max = altitude

    elif msg.name() == "NAV_VELNED":
        msg.unpack()
        ground_speed = msg.gSpeed #*0.036 # Convert to kph
        heading = msg.heading #*1.0e-5
        acent_rate = -msg.velD #-1.0*msg.velD/100.0)

    elif msg.name() == "NAV_TIMEGPS":
        msg.unpack()
        week = msg.week
        iTOW = msg.iTOW #*1.0e-3)
        leapS = msg.leapS

        # Update NTP only on whole-second boundary
        if iTOW % 1000 == 0:
            ntpd_shm.update(gps2unix_ms(week, iTOW, leapS) // 1000)

        rx_counter += 1

        # Poll for a CFG_NAV5 message occasionally.
        if rx_counter % 20 == 0:
            # A message with only 0x00 in the payload field is a poll.
            gps.send_message(CLASS_CFG, MSG_CFG_NAV5, b'\x00')

        # Additional checks to be sure we're in the right dynamic model.
        if rx_counter % 40 == 0:
            gps.set_preferred_dynamic_model(dynamic_model)

        timestamp = gps2unix_ms(week, iTOW, leapS)
        gps_status = (numSV << 10) & 0xFC00 | \
                     (gpsFix << 8) & 0x0300 | \
                     dynamic_model & 0x00FF
        if altitude < 0:
            altitude = 42
        if latitude < 0:
            latitude = 0
        if longitude < 0:
            longitude = 0
        if ground_speed < 0:
            ground_speed = 0

        #prettytime = datetime.utcfromtimestamp(timestamp // 1000)
        #print("%d %3d %10.7f %10.7f %8.3f %s %d" % (gpsFix, numSV,
        #        latitude * 1e-7, longitude * 1e-7, altitude * 1e-3, prettytime, iTOW),
        #        end='\r')

        gps_struct.pack_into(shm, 0,
                        timestamp, latitude, longitude, altitude, alt_max,
                        ground_speed, acent_rate, heading, gps_status)
        time.sleep(.7)

    elif msg.name() == "CFG_NAV5":
        msg.unpack()
        if msg.dynModel != dynamic_model:
            debug_message("Dynamic model changed.")
            gps.set_preferred_dynamic_model(dynamic_model)

    else:
        pass
