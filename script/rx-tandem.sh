#!/bin/bash

# Hack to run from root of repo
mydir="$(realpath $(dirname $0))"
PATH=$PATH:"$mydir":"$mydir/../build":"$mydir/../../horusdemodlib/build/src"

# Callsign or listener name
export MYCALL=

# Disable as desired
sondehub.py &
ssdv_upload.py &

fifo=rx.fifo
mkfifo $fifo

# Adjust frequency (f_c - 100kHz) to payload
# fskdemodgui can be disabled, eg. on headless systems
rtl_sdr -f 433900000 -s 2400000 -g 0 - | csdr convert_u8_f |  \
	csdr tee rx.fifo 2>/dev/null |
	csdr bandpass_fir_fft_cc 0.02 0.1666 0.02 | \
	csdr fir_decimate_cc 3 .05 HAMMING | \
	csdr realpart_cf | csdr gain_ff 0.5 | \
	csdr convert_f_s16 | \
	fsk_demod -s -t2 2 800000 50000 - - \
	2> >(fskdemodgui.py --wide 2>/dev/null) | frame-dec \
	| ssdv_split | telemetry-broadcast.py &

# Adjust shift (f_c - 1.6kHz) to payload
cat $fifo \
	| csdr shift_addition_cc 0.14833333 | \
	csdr fir_decimate_cc 50 .05 \
	csdr bandpass_fir_fft_cc 0.02 0.45 0.02 |
	csdr realpart_cf | csdr gain_ff 0.5 | \
	csdr convert_f_s16 | \
	horus_demod -m binary -t100 -g - - | ../horusdemodlib/simple_horus_decoder.sh

jobs -rp | xargs kill
wait

rm -f $fifo
