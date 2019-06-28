#!/bin/bash

# Hack to run from root of repo
mydir="$(realpath $(dirname $0))"
PATH=$PATH:"$mydir":"$mydir/../build"

# Callsign or listener name
export MYCALL=DK0WT

mkdir -p tx_images

save_anotate_ssdv.sh &
gpsd.py &
temperature.py &
power &
pressure &

sleep 1

pkg_source.py | frame-enc

jobs -p | xargs kill
wait
