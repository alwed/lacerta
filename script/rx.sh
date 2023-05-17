#!/bin/bash

# Hack to run from root of repo
mydir="$(realpath $(dirname $0))"
PATH=$PATH:"$mydir":"$mydir/../build"

# Callsign or listener name
MYCALL=

# Disable as desired
sondehub.py &
ssdv_upload.py &

# Adjust frequency (f_c - 100kHz) to payload
# fskdemodgui can be disabled, eg. on headless systems
rtl_sdr -f 433900000 -s 2400000 -g 0 - \
	| csdr convert_u8_f |  \
	csdr bandpass_fir_fft_cc 0.02 0.1666 0.02 | \
	csdr fir_decimate_cc 3 .005 HAMMING | \
	csdr realpart_cf | csdr gain_ff 0.5 | \
	csdr convert_f_s16 | \
	fsk_demod -s -t2 2 800000 50000 - - \
	2> >(fskdemodgui.py --wide 2>/dev/null) | frame-dec \
	| ssdv_split | telemetry-broadcast.py


jobs -rp | xargs kill
wait
