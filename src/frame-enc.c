#define _GNU_SOURCE
#include <stdio.h>
#include <stdint.h>

#include <unistd.h>
#include <fcntl.h>
#include <termios.h>

#include "codec2/H2064_516_sparse.h"

#define K (NUMBERROWSHCOLS / 8)

void ra_enc(const uint8_t *restrict ibits, uint8_t *restrict pbits)
{
	unsigned tmp, par, prev = 0;
	int ind;

	for (unsigned p = 0; p < NUMBERPARITYBITS; p++) {
		par = 0;

		for ( unsigned i = 0; i < MAX_ROW_WEIGHT; i++) {
			ind = H_rows[p + i * NUMBERPARITYBITS];
			par = par + ibits[ind - 1];
		}

		tmp = par + prev;

		tmp &= 1;    // only retain the lsb
		prev = tmp;
		pbits[p] = tmp;
	}
}

int tty_custom_speed(int fd, int speed);

unsigned crc16(unsigned state, int bit) {
	if (state & 0x8000)
		state = ((state << 1) + bit) ^ 0x1021;
	else
		state = (state << 1) + bit;

	return state;
}

int main(int argc, char **argv)
{
	uint8_t bits[CODELENGTH];
	uint8_t *ibits = &bits[0];
	uint8_t *pbits = &bits[NUMBERROWSHCOLS];
	int ret = 0;

	uint8_t uart_buf[12 + CODELENGTH / 8 + 1] =
		"\xAA\xAA\xAA\xAA\xAA\xAA\xAA\xAA\xD2\x7C\xEC\x0A";
	uint8_t *coded_bytes = &uart_buf[12];

	/* Setup UART */
	FILE *uart = fopen("/dev/ttyAMA0", "w");
	if (!uart) {
		perror("fopen");
		return 2;
	}

	int fd = fileno(uart);

	/* POSIX compatible first */
	struct termios tio1;
	if (tcgetattr(fd, &tio1) < 0) {
		perror("tcgetattr");
		return 2;
	}

	cfmakeraw(&tio1);		/* 8bit, no parity, no postprocessing */
	tio1.c_cflag &= ~CSTOPB;	/* 1 stop bit */

	if (tcsetattr(fd, TCSANOW, &tio1) < 0) {
		perror("tcsetattr");
		return 2;
	}

	if (tty_custom_speed(fd, 50000) != 0) {
		perror("custom speed");
		return 2;
	}

	/* Try to set pipe buffer size of input stream. Don't worry about errors,
	 * it will still work. Maybe the input was not a pipe.
	 * The smallest sensible buffer size is the length of one frame. The
	 * actual size can be larger (at least page size).
	 */
	fcntl(fileno(stdin), F_SETPIPE_SZ, 256);

	while (1) {
		uint8_t data;
		unsigned crc = 0xFFFF;

		/* Unpack bytes, calculate crc on the fly */
		for (unsigned k = 0; k < K - 2; k++) {
			if (fread(&data, 1, 1, stdin) != 1) {
				ret = k == 0 ? 0 : 1;
				goto out;
			}

			for (unsigned i = 0; i < 8; i++) {
				int b = (data >> (7-i)) & 1;
				crc = crc16(crc, b);
				ibits[k * 8 + i] = b;
			}
		}

		/* Terminate CRC */
		for (unsigned i = 0; i < 16; i++)
			crc = crc16(crc, 0);

		/* Append CRC (big endian implied by polynomial view) */
		for (unsigned i = 0; i < 16; i++)
			ibits[8 * (K - 2) + i] = (crc >> (15 - i)) & 1;

		//fputs("Packet read\n", stderr);

		/* Append LDPC bits */
		ra_enc(ibits, pbits);

		//fputs("LDPC encoding done\n", stderr);

		/* Write preamble */
		//fputs("\x55\x55\x55\x55\x55\x55\x55\x55\x4B\x3E\x37\x50", stdout);

		/* Pack and write out code bits; reversed for UART*/
		unsigned j = 0;
		for (j = 0; j < CODELENGTH / 8 + 1; j++) {
			uint8_t byte = 0;
			for (unsigned i = 0; i < 8; i++)
				byte |= bits[j * 8 + i] << i;
			//fwrite(&byte, 1, 1, stdout);
			coded_bytes[j] = byte;
		}
		fwrite(&uart_buf, sizeof(uart_buf), 1, uart);

//		for (unsigned i = 0; i < CODELENGTH; i++) {
//			float f = bits[i] ? -1 : 1;
//			fwrite(&f, sizeof(float), 1, stdout);
//		}
	}
out:
	fclose(uart);
	return ret;
}
