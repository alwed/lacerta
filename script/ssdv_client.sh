#!/bin/sh

cd rx_images

while true; do
	test -f rx.tmp && ssdv -d rx.tmp rx.tmp.jpg
	sleep 10
done &

while [ ! -f rx.tmp.jpg ]; do
	sleep 1
done
feh -. rx.tmp.jpg

jobs -p | xargs kill
wait
