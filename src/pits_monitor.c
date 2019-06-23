#include <errno.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "pits_info.h"
#include "shm.h"

static const char *shm_path = "/dev/shm/pits.shm";

int maidenhead(float lon, float lat, char *out, size_t length);

int main(int argc, char **argv)
{
	if (argc < 2) {
		fprintf(stderr, "No format string given\n");
		return 2;
	}

	int ret = 1;

	int shm_fd = -1;
	const struct pits_info *pits;
	if (!shm_openro(&shm_fd, &pits, shm_path)) {
		ret = 1;
		goto out;
	}

	size_t len = 32;
	size_t k = 0;
	char *buf = malloc(len); // small buffer, enlarge it later if needed
	char s[20];
	for (int i = 1; i < argc; i++) {
		for (size_t j = 0; argv[i][j]; j++) {
			s[0] = 0;
			int l = 0;
			if (argv[i][j] == '%') {
				j++;
				switch(argv[i][j]) {
				case 'T':	/* Latitude, "θ" */
					l = snprintf(s, 20, "% 9.7f",
							pits->lat * 1e-7);
					break;
				case 'F':	/* Longitude, "φ" */
					l = snprintf(s, 20, "% 10.7f",
							pits->lon * 1e-7);
					break;
				case 'G':	/* Grid */
					maidenhead(pits->lon * 1e-7,
							pits->lat * 1e-7, s, 7);
					l = 6;
					break;
				case 'a':	/* Altitude */
					l = snprintf(s, 20, "%6.1f",
							pits->alt * 1e-3);
					break;
				case 'A':	/* Maximum altitude */
					l = snprintf(s, 20, "%6.1f",
							pits->alt_max * 1e-3);
					break;
				case 'h':	/* ground speed */
					l = snprintf(s, 20, "%.1f",
							pits->speed_g * 1e-2);
					break;
				case 'v':	/* ascent rate */
					l = snprintf(s, 20, "%+.1f",
							pits->speed_v * 1e-2);
					break;
				case 'S':
					l = snprintf(s, 20, "0x%hX",
						pits->gps_status);
					break;
				case 'U':
					l = snprintf(s, 20, "%.2f",
						 (double) pits->vbat / 0x400);
					break;
				case 'I':
					l = snprintf(s, 20, "%.3f",
						 (double) pits->isys / 0x4000);
					break;
				case '%':
					s[0] = '%'; s[1] = 0;
					l = 1;
					break;
				default:
					fprintf(stderr, "Invalid format "
							"specifier\n");
					break;
				}
				if (l >= 20) {
					fprintf(stderr, "Formatted string "
						"longer than expected\n");
					l = 19;
				} else if (l < 0) {
					fprintf(stderr, "Format error\n");
					l = 0;
				}
			} else {
				s[0] = argv[i][j]; s[1] = 0;
				l = 1;
			}
			if (l == 0)
				continue;

			if (k + l > len) {
				len += 64;
				buf = realloc(buf, len);
				if (!buf) {
					fprintf(stderr, "%s\n",
							strerror(errno));
					goto out;
				}
			}
			strncpy(buf + k, s, l+1);
			k += l;
		}
	}

	puts(buf);
	if ((pits->gps_status & 0x0300) >> 8 == 3) {
		ret = 0;
	} else {
		ret = 42;
	}
 out:
	shm_close(shm_fd, pits);
	return ret;
}

static uint8_t quantize_component(float *coord, float divisor)
{
	float quant = floorf(*coord / divisor);
	*coord -= quant * divisor;
	return quant;
}

static size_t encode_level(float *lon, float *lat, char *out,
		size_t length, float lon_div, float lat_div, char ref)
{
	if (length >= 2) {
		out[0] = ref + quantize_component(lon, lon_div);
		out[1] = ref + quantize_component(lat, lat_div);
		return 2;
	} else {
		return 0;
	}
}

int maidenhead(float lon, float lat, char *out, size_t length)
{
	size_t written = 0;

	/* Measure latitude from the South Pole and longitude
	 * eastward from the antimeridian of Greenwich */
	lon += 180;
	lat += 90;

	/* Field: base18, letters A to R */
	written += encode_level(&lon, &lat, out + written, length - written,
			360./18, 180./18, 'A');

	/* Square: base10, digits 0 to 9 */
	written += encode_level(&lon, &lat, out + written, length - written,
			360./18/10, 180./18/10, '0');

	/* Subsquare: base24, letters a to x */
	written += encode_level(&lon, &lat, out + written, length - written,
			360./18/10/24, 180./18/10/24, 'a');

	/* Extended square: base10, digits 0 to 9 */
	written += encode_level(&lon, &lat, out + written, length - written,
			360./18/10/24/10, 180./18/10/24/10, '0');

	for (int i = written; i < length; i++) {
		out[i] = 0;
	}
	return written;
}
