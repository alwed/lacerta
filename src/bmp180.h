#ifndef _BMP180_H_
#define _BMP180_H_

#include <stdbool.h>
#include <stdint.h>

struct bmp180 {
	int fd;
	uint16_t addr;
	struct {
		int16_t AC1;
		int16_t AC2;
		int16_t AC3;
		uint16_t AC4;
		uint16_t AC5;
		uint16_t AC6;
		int16_t B1;
		int16_t B2;
		int16_t MB;
		int16_t MC;
		int16_t MD;
	} calib;
	int32_t B5;
};

size_t bmp180_get_size(void);
bool bmp180_init(struct bmp180 *b, const char *path, uint16_t addr);
void bmp180_close(struct bmp180 *b);

bool bmp180_reset(struct bmp180 *b);
bool bmp180_measT(struct bmp180 *b, int32_t *T);
bool bmp180_measp(struct bmp180 *b, unsigned oss, int32_t *p_out);

#endif
