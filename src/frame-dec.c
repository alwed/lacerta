#include <stdio.h>
#include <stdint.h>

/* From codec2 */
#include "codec2/mpdecode_core.h"
#include "codec2/H2064_516_sparse.h"

#define N	CODELENGTH
#define K	NUMBERROWSHCOLS
#define FLEN	258

/* CRC-16-CIIT shift-register, modified from:
 * http://stackoverflow.com/questions/10564491/function-to-calculate-a-crc16-checksum
 */
uint16_t crc16_new(uint8_t* data, size_t length){
    uint16_t crc = 0xFFFF;

    while (length--) {
        uint8_t x = crc >> 8 ^ *data++;
        x ^= x>>4;
        crc = (crc << 8) ^ ((uint16_t)(x << 12)) ^ ((uint16_t)(x <<5))
		^ ((uint16_t)x);
    }

    return crc;
}

unsigned short crc16(unsigned char* data_p, int length){
    unsigned char x;
    unsigned short crc = 0xFFFF;

    while (length--){
        x = crc >> 8 ^ *data_p++;
        x ^= x>>4;
        crc = (crc << 8) ^ ((unsigned short)(x << 12)) ^ ((unsigned short)(x <<5)) ^ ((unsigned short)x);
    }

    return crc;
}

int main(int argc, char **argv)
{
	float window[40] = {0};
/*	float tag[32] = {
		-1, -1, -1, -1, 1, -1,  1, -1, 1, 1,  1, -1,  1,  1, -1, -1,
		-1,  1,  1,  1, 1,  1, -1, -1, 1, 1, -1,  1, -1, -1,  1, -1
	};*/
	float tag[40] = {
	/*	SP, D0, D1, D2, D3, D4, D5, D6, D7, ST */
		 1, -1, -1, -1, -1,  1, -1,  1, -1, -1,
		 1,  1,  1,  1, -1,  1,  1, -1, -1, -1,
		 1, -1,  1,  1,  1,  1,  1, -1, -1, -1,
		 1,  1,  1, -1,  1, -1, -1,  1, -1, -1,
	};

	double symbols[N];
	float llr[N];
	uint8_t infobits[N], frame[FLEN];
	unsigned frame_count = 0, frame_errors = 0;
	struct LDPC ldpc;

	/* set up LDPC code from include file constants */
	ldpc.max_iter = 100; //MAX_ITER;
	ldpc.dec_type = 0;
	ldpc.q_scale_factor = 1;
	ldpc.r_scale_factor = 1;
	ldpc.CodeLength = CODELENGTH;
	ldpc.NumberParityBits = NUMBERPARITYBITS;
	ldpc.NumberRowsHcols = NUMBERROWSHCOLS;
	ldpc.max_row_weight = MAX_ROW_WEIGHT;
	ldpc.max_col_weight = MAX_COL_WEIGHT;
	ldpc.H_rows = H_rows;
	ldpc.H_cols = H_cols;

	float r;
	while (1) {
		/* Look for preamble */
		while (1) {
			if (fread(&r, sizeof(r), 1, stdin) != 1)
				return 0;

			/* Shift window */
			for (unsigned i = 40 - 1; i > 0; i--)
				window[i] = window[i-1];

			window[0] = r > 0 ? -1 : 1;

			/* Correlate with tag */
			float corr = 0;
			for (unsigned i = 0; i < 40; i++)
				corr += window[i] * tag[i];
			if (corr >= 40 - 5)
				break;
		}

		/* Read codeword */
		for (unsigned i = 0, j = 0; i < N; j++) {
			if (fread(&r, sizeof(r), 1, stdin) != 1)
				return 1; /* incomplete frame is an error */

			if (j % 10 != 0 && j % 10 != 9) {
				/* Convert to double for soft-decision decoder */
				symbols[i++] = r;
			}
		}

		/* Decode LDPC code word */
		int iter, pcheck_count;
		sd_to_llr(llr, symbols, N);
		iter = run_ldpc_decoder(&ldpc, infobits, llr, &pcheck_count);

		/* Pack bits into bytes, MSB first; check CRC on the fly */
		unsigned crc = 0xFFFF;
		for (unsigned i = 0; i < FLEN; i++) {
			int x = 0;
			for (unsigned j = 0; j < 8; j++) {
				unsigned b = infobits[8 * i + j];
				if (crc & 0x8000)
					crc = ((crc << 1) + b) ^ 0x1021;
				else
					crc = (crc << 1) + b;

				x |= b << (7 - j);
			}
			frame[i] = x;
		}

		if ((crc & 0xFFFF) == 0) {
			fwrite(frame, 1, FLEN-2, stdout);
		} else {
			frame_errors++;
		//	fwrite(frame, 1, FLEN-2, stdout);
		}

		frame_count++;
		fprintf(stderr, "frames: %d errors: %d FER: %4.3f iter: %d %d\n",
                           frame_count, frame_errors,
                           (float)frame_errors/frame_count, iter, pcheck_count);

	}

	return 0;
}
