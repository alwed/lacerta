#!/bin/bash

# Hack to run from root of repo
mydir="$(realpath $(dirname $0))"
PATH=$PATH:"$mydir":"$mydir/../build"

# Callsign or listener name
MYCALL=DL2IK

# Disable as desired
sondehub.py &
ssdv_upload.py &

# Adjust frequency (f_c - 100kHz) to payload
# fskdemodgui can be disabled, eg. on headless systems
rtl_sdr -f 434000000 -s 2400000 -g 5 - \
	| csdr convert_u8_f |  \
	csdr fir_decimate_cc 6 .05 HAMMING | \
	csdr bandpass_fir_fft_cc -0.1 0.45 0.05 | csdr convert_f_s16 | \
	fsk_demod -c -s -t2 2 400000 50000 - - \
	2> >(fskdemodgui.py 2>/dev/null) | frame-dec | ssdv_split | \
	telemetry-broadcast.py

jobs -p | xargs kill
wait
