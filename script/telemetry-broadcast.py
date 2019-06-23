#!/usr/bin/env python3

import json, sys, socket, struct

WENET_TELEMETRY_UDP_PORT = 7891

last_time = 0

def socket_setup():
    sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    # Set up the telemetry socket so it can be re-used.
    sock.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # We need the following if running on OSX.
    try:
    	sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except:
    	pass
    return sock

def broadcast_packet(sock, data):
    # Deduplicate telemetry
    global last_time
    time = struct.unpack(">Q", b"\0\0" + data[6:12])[0]
    if time <= last_time:
        return
    last_time = time

    # Place data into dictionary.
    data = {'packet': list(bytearray(data))}

    # Send to broadcast if we can.
    try:
    	sock.sendto(json.dumps(data).encode(), ('<broadcast>', WENET_TELEMETRY_UDP_PORT))
    except socket.error:
    	sock.sendto(json.dumps(data).encode(), ('127.0.0.1', WENET_TELEMETRY_UDP_PORT))

def split_frame(data):
    packets = []
    l = -1
    while len(data) > 0:
        if data[0] == 0x80:
            l = 64
        elif data[0] == 0x79:
            l = 128
        else:
            break
        packets.append(data[:l])
        data = data[l:]
    return packets

sock = socket_setup()
try:
    while True:
        frame = sys.stdin.buffer.read(256)
        if len(frame) == 0:
            break
        for pkg in split_frame(frame):
            broadcast_packet(sock, pkg)
finally:
    sock.close()
