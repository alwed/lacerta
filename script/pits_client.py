#!/usr/bin/env python3

import curses
import socket
from threading import Thread
import datetime
import struct
import json
from collections import namedtuple
from pits_info import pits_info, ssdv_decode_callsign

WENET_TELEMETRY_UDP_PORT    = 7891
PITS_INFO_PACKET_ID         = 0x80

pits = pits_info(False)

def decode_pits_info(packet):
    global pits
    if packet[0] != PITS_INFO_PACKET_ID or len(packet) < pits.struct.size:
        return
    try:
        pits.read(packet[1:])
    except Exception as e:
        print("Packet decode error:", str(e), len(packet))

def decT(c):
    return c - 273.15

def decode_text(packet):
    return packet[4:4+packet[1]].decode()

from textwrap import wrap
import time

def logtext(s):
    global logwin
    s = "[" + time.strftime("%H:%M:%S")  + "] " + str(s)
    _, w = logwin.getmaxyx()
    ss = wrap(s, w)

    for s in ss:
        logwin.addstr("\n" + s)

    logwin.refresh()

def main(stdscr):
    global logwin

    curses.use_default_colors()
    try:
        curses.curs_set(0)
    except:
        pass
    curses.halfdelay(10)

    pitswin = stdscr.derwin(20,45, 2,0)
    pitswin.box()

    _, w = stdscr.getmaxyx(); w -= 46
    logwin_outer = stdscr.derwin(20,w, 2,46)
    logwin_outer.box()
    logwin = logwin_outer.derwin(18,w-2, 1,1)
    logwin.idlok(True)
    logwin.scrollok(True)

    while True:
        pitswin.addstr(1,5, "PITS Info: %s" % pits.call)
        timestamp = pits.time // 1000
        pitswin.addstr(3,1, "Timestamp:\t%s" % \
                    datetime.datetime.fromtimestamp(timestamp).isoformat(' '))
        pitswin.addstr(4,1, ("Position:\t% 9.7f° N, % 10.7f° E" % (
            pits.lat, pits.lon)))
        pitswin.addstr(5,1, ("Heading:\t% 5.2f°" % pits.heading))
        pitswin.addstr(6,1, ("Altitude:\t%.0f m (%.0f)" % (
            pits.alt, pits.alt_max)).ljust(30))
        pitswin.addstr(7,1, ("Speed:\t\tH %.0f km/h  V %+.0f m/s" % (
            pits.speed_g * 3.6, pits.speed_v)).ljust(30))
        pitswin.addstr(8,1, "GPS Fix:\t%s\t%d" % (
            pits.gpsFix, pits.dynamic_model))

        pitswin.addstr(10,1, "Temperatures:")
        pitswin.addstr(11,1, ("  System:\t% 5.2f °C" % decT(pits.Ts)).ljust(30))
        pitswin.addstr(12,1, ("  Intern:\t% 5.2f °C" % decT(pits.Ti)).ljust(30))
        pitswin.addstr(13,1, ("  Extern:\t% 5.2f °C" % decT(pits.Te)).ljust(30))

        pitswin.addstr(15,1, ("Voltage (Bat):\t%.2f V" % (
            pits.vbat)).ljust(30))
        pitswin.addstr(16,1, ("Current (Sys):\t%.2f A" % (
            pits.isys)).ljust(30))

        pitswin.addstr(18,1, ("Pressure:\t%d Pa" % pits.p).ljust(30))

        pitswin.refresh()

        try:
            c = stdscr.getch()
        except:
            continue

        if c == ord('q'):
            break

udp_listener_running = False
def udp_listener():
    """ Listen on a port for UDP broadcast packets,
        and pass them onto process_udp() """
    global udp_listener_running
    s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    s.settimeout(1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except:
        pass
    s.bind(('', WENET_TELEMETRY_UDP_PORT))
    print("Started UDP Listener Thread.")

    udp_listener_running = True
    while udp_listener_running:
        m = ""
        try:
            m = s.recv(2048).decode()
            m = json.loads(m)
            m = bytes(m["packet"])
            #if m[0] == 0x00:
            #    logtext(decode_text(m))
            if m[0] == 0x80:
                decode_pits_info(m)
                #logtext(str(pits.time))
            else:
                #logtext("%02X %d" % (m[0], len(m)))
                continue
        except socket.timeout:
            continue
        except Exception as e:
            logtext("Error in UDP-Listener: " + str(e))

    print("Closing UDP Listener")
    s.close()


if __name__ == "__main__":
    t = Thread(target=udp_listener)
    t.start()
    curses.wrapper(main)
    udp_listener_running = False
    t.join()
