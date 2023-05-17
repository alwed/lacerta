Lacerta
=======

experimental balloon downlink
heavily based on [Wenet](https://github.com/projecthorus/wenet) by Mark Jessop
and [codec2](https://github.com/drowe67/codec2) by David Rowe, et. al.

Key differences from Wenet
--------------------------

- bundled codec2 dependencies for easier development and setup
- sync word (prbs vs. dummy)
- CRC algorithm
- temporal diversity for telemetry packets
- GPU accelerated image scaling

Setup of a receiver station
------------------------

### Dependencies

- Computer, not too slow (eg. Raspberry Pi 3) with GNU/Linux
- SDR receiver and software that dumps raw samples into a pipe (eg. rtl-sdr)
- C toolchain
- python-3
- [csdr](https://github.com/simonyiszk/csdr)
- pyqtgraph (for fskdemodgui)
- [horusdemodlib](https://github.com/projecthorus/horusdemodlib) (for tandem reception)

### Build and run

Build all binaries used by a ground station:

```
$ make -C src/
```

Adapt `scripts/rx[-tandem].sh` if necessary. Adjust the frequency, set your
callsign or listener name and enable image and telemetry upload as desired.

Run the receiver skript from the root:
```
$ script/rx.sh
```
Use `rx_tandem.sh` to decode an additional payload with the same SDR input.

SSDV packets are grouped into images and saved in a `rx_images` directory.
Telemetry and text packets are broadcasted via UDP and can be monitored with
`scripts/pits_client.py`

Protocol specification
----------------------

### Physical Layer

Frequency shift keying:
- Alphabet: `f₁`, `f₂` (1 bit per symbol)
- Symbol rate: 50 kBd 
- Frequency shift `f₁ - f₂`= 50 kHz
- Rectangular pulse-shaping

### Frame Structure

| preamble	| payload	| CRC	| LDPC	|
|-----------|---------|-----|-------|
| 32		| 2048		| 16	| 516	|

- Sizes in bits
- Big endian, MSB first
- Start and stop bits

#### Preamble

The word `0x4B3E3750`, i.e. PRBS-5 with leading 0.

#### Payload

One or more of the packets defined below.

#### CRC

Check bits of the CRC-16 with generator `0x11021` and initial value `0xFFFF`
over the payload. The check value of the nine ASCII characters `"123456789"` is
`0xE5CC`. This is **not** the "false CRC" used by wenet.

#### LDPC

Check bits of the systematic encoded (2580, 2064)₂ - code of wenet / codec2.

#### Start and Stop Bits

Each octet `(D7, D6, …, D0)` of a frame is transmitted as `(0, D7, …, D0, 1)`.
0xAA results in alternating 1s and 0s.

### Packet formats

- Fixed length: 64, 128 or 256 bytes
- 1st byte is packet type
- Packet length is implied by type

#### NULL packet

- Packet Type = 0xFF
- No further packets in this frame

#### SSDV Packet

- Packet Type = 0x55
- see <https://ukhas.org.uk/doku.php?id=guides:ssdv>

#### Telemetry Packet

- Packet Type = 0x80
- Length = 64

| Offset | Length | Description 		|
|--------|--------|-----------------------------|
|  0     | 1      | Packet type = 0x80		|
|  1     | 6      | Call (Base-40) 		|
|  7     | 6      | Time / ms since POSIX epoch |
|        |        |				|
| 13     | 4      | Latitude · 1e7 / °		|
| 17     | 4      | Longitude · 1e7 / °		|
| 21     | 4      | Altitude / mm		|
| 25     | 4      | Maximum altitude / mm	|
| 29     | 4      | Ground speed / cm/s		|
| 33     | 4      | Ascent rate	/ cm/s		|
| 37     | 4      | Heading · 1e5 / °		|
| 41     | 2      | GPS status			|
|        |        | 				|
| 43     | 2      | Temperature SoC / K; U10.6	|
| 45     | 2      | Temperature intern "	|
| 47     | 2      | Temperature extern "	|
| 49     | 4      | Atmospheric pressure / Pa	|
|        |        |				|
| 53     | 2      | Battery voltage / V; U6.10	|
| 55     | 2      | System current / A; U2.14	|
|        |        |				|
| 57     | 7      | reserved			|

#### Text Packet

Packet Type = 0x79
Length = 128 (including header byte)
