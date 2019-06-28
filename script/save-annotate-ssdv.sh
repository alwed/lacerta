#!/bin/sh

tmpdir=/dev/shm
tmpimg_save=$tmpdir/save.jpg
tmpimg_scale=$tmpdir/scale.bmp
tmpimg_ssdv=$tmpdir/ssdv.jpg
tmpimg_send=$tmpdir/send.ssdv

quality=6

# w = n * 4 * 16; h = n * 3 * 16
#res_send=1408x1056 # n = 22
# PiCam v1
res_true=2592x1944
res_yuv=2592x1952
# PiCam v2
#res_true=3280x2464
#res_yuv=3296x2464

logo=DARC_Logo.png
logo2=KA_NG50.png

id=0
while [ -e $id.jpg ] ; do
	id=$(($id + 1))
done

cleanup() {
	rm -f "$tmpimg_save" "$tmpimg_scale" "$tmpimg_ssdv" "$tmpimg_send"
}
#trap cleanup EXIT

# Wait for system to be powered from battery
x=0
while [ $x -eq 0 ]; do
	sleep 1
	x=$(pits_monitor "%I > 0.05" | bc -q)
done

while true; do
	# Take images
	cam_double_save.py

	mv "$tmpimg_save" "tx_images/$id.jpg"

	# loc, alt (max), H , V
	gps_str=$(pits_monitor "Grid: %G  Alt: %a (%A)  Speed: H %hkm/h V %vm/s")
	status=$?
	if [ $status -eq 42 ]; then
		gps_str="No GPS"
	elif [ $status -ne 0 ]; then
		gps_str="GPS Failed"
	fi

	date_str=$(date +'%Y-%m-%d %_H:%M')
	info_str="$date_str    $gps_str"


	convert "$tmpimg_scale" -colorspace RGB \
		-font DejaVu-Sans-Mono -pointsize 25 -gravity South -antialias \
		-strokewidth 2 -stroke '#000C' -annotate +0+5 "$info_str" \
		-stroke none -fill white -annotate +0+5 "$info_str" \
		$(if [ -e "$logo" ]; then \
			echo $logo -gravity NorthEast -composite
		fi ) \
                $(if [ -e "$logo2" ]; then \
                        echo $logo2 -gravity NorthWest -composite
                fi ) \
		-colorspace sRGB -quality 100 -sampling-factor "2x2, 1x1, 1x1" \
		"$tmpimg_ssdv"

	ssdv -e -n -q $quality -c $MYCALL -i $id "$tmpimg_ssdv" "${tmpimg_send}~"
	mv "${tmpimg_send}~" "$tmpimg_send"

#	break

	id=$(($id + 1))
	while [ -e $tmpimg_send ]; do
		sleep 1
	done
done
