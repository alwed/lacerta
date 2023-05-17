#!/bin/bash

# Hack to run from root of repo
mydir="$(realpath $(dirname $0))"
PATH=$PATH:"$mydir":"$mydir/../build:$mydir/../../horusbinary"

# Callsign or listener name
MYCALL=DL2IK

# Disable as desired
sondehub.py &
ssdv_upload.py &

fifo=rx.fifo
mkfifo $fifo

# Adjust frequency (f_c - 100kHz) to payload
# fskdemodgui can be disabled, eg. on headless systems
rtl_sdr -f 434000000 -s 2400000 -g 5 - \
	| csdr convert_u8_f |  \
	csdr fir_decimate_cc 2 .083 HAMMING | csdr tee rx.fifo 2>/dev/null | \
	csdr fir_decimate_cc 3 .05 HAMMING | \
	csdr bandpass_fir_fft_cc 0 0.5 0.05 | csdr convert_f_s16 | \
	fsk_demod -c -s -t2 2 400000 50000 - - \
	2> >(fskdemodgui.py 2>/dev/null) | frame-dec | ssdv_split | \
	telemetry-broadcast.py &

# Adjust shift (f_c - 1.6kHz) to payload
cat $fifo \
	| csdr shift_addition_cc 0.37633333333333333333 | \
	csdr fir_decimate_cc 25 .01 HAMMING | \
	csdr convert_f_s16 | \
	horus_demod -q -m binary - - | \
	horusbinary.py --stdin

jobs -p | xargs kill
wait

rm -f $fifo
