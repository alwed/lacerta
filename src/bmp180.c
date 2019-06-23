#include <endian.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/i2c.h>
#include <linux/i2c-dev.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

#include "bmp180.h"

#define REG_CALIB0	0xAA /* 11x16bit be	*/
#define REG_ID		0xD0 /* reads 0x55	*/
#define REG_SOFT_RESET	0xE0 /* write 0xB6	*/
#define REG_CTRL_MEAS	0xF4
#define REG_OUT		0xF6 /* 24bit be	*/

static bool readregs(struct bmp180 *b, uint8_t addr, void *buf, uint16_t len);
static bool writereg(struct bmp180 *b, uint8_t addr, uint8_t val);
static void calib_betoh(struct bmp180 *b);

/*int main(int argc, char **argv)
{
	struct bmp180 b;
	char *path;

	if (argc > 1) {
		path = argv[1];
	} else {
		path = "/dev/i2c-3";
	}

	if (!bmp180_init(&b, path, BMP180_ADDR))
		return 1;

	int32_t T, p;
	bool succ = true;
	succ = succ && bmp180_measT(&b, &T);
	succ = succ && bmp180_measp(&b, 3, &p);

	if (succ) {
		printf("%.2f °C\t%.2f hPa\n", T / 10., p / 100.);
	}

	bmp180_close(&b);
	return succ ? 0 : 1;
}*/

bool bmp180_measT(struct bmp180 *b, int32_t *T)
{
	uint16_t UT;
	int32_t X1, X2;

	/* Start temperature measurement */
	if (!writereg(b, REG_CTRL_MEAS, 0x2E))
		return false;
	usleep(4500); /* Wait 4.5ms for conversion */

	/* Read UT */
	if (!readregs(b, REG_OUT, &UT, 2))
		return false;
	UT = be16toh(UT); /* Ensure correct endianess */

	/* Linearize temperature */
	X1 = (UT - b->calib.AC6) * b->calib.AC5 / 0x8000;
	X2 = (b->calib.MC * 0x800) / (X1 + b->calib.MD);
	b->B5 = X1 + X2;

	/* Convert to 0.1°C only if the user needs it */
	if (T)
		*T = (b->B5 + 8) / 0xF;

	return true;
}

bool bmp180_measp(struct bmp180 *b, unsigned oss, int32_t *p_out)
{
	unsigned wait;
	uint32_t UP, B4, B7;
	int32_t B3, B6, X1, X2, X3, p;

	if (!p_out) {
		fprintf(stderr, "Invalid address for result.\n");
		return false;
	}

	switch (oss) {
	case 0:	/* ultra low power */
		wait = 4500;
		break;
	case 1:	/* standard */
		wait = 7500;
		break;
	case 2: /* high resolution */
		wait = 13500;
		break;
	case 3: /* ultra high resolution */
	default:
		wait = 25500;
		break;
	}

	/* Start pressure measurement */
	if (!writereg(b, REG_CTRL_MEAS, 0x34 + ((oss & 0x3) << 6)))
		return false;
	usleep(wait); /* Wait for converion */

	/* Read UP */
	UP = 0;
	readregs(b, REG_OUT, &UP, 3);
	UP = be32toh(UP);
	UP >>= 8 + 8 - oss;

	/* Calculate pressure in physical units */
	B6 = b->B5 - 4000;
	X1 = (b->calib.B2 * (B6 * B6 / 0x1000)) / 0x800;
	X2 = b->calib.AC2 * B6 / 0x800;
	X3 = X1 + X2;
	B3 = (((b->calib.AC1 * 4 + X3) << oss) + 2) / 4;
	X1 = b->calib.AC3 * B6 / 0x2000;
	X2 = (b->calib.B1 * (B6 * B6 / 0x1000)) / 0x10000;
	X3 = ((X1 + X2) + 2) / 4;
	B4 = b->calib.AC4 * (uint32_t)(X3 + 0x8000) / 0x8000;
	B7 = ((uint32_t) UP - B3) * (50000 >> oss);
	if (B7 < 0x80000000) {
		p = (B7 * 2) / B4;
	} else {
		p = (B7 / B4) * 2;
	}
	X1 = (p / 0x100) * (p / 0x100);
	X1 = (X1 * 3038) / 0x10000;
	X2 = (-7357 * p) / 0x10000;
	p = p + (X1 + X2 + 3791) / 0xF;

	*p_out = p;

	return true;
}

bool bmp180_init(struct bmp180 *b, const char *path, uint16_t addr)
{
	b->addr = addr;
	b->fd = open(path, O_RDWR);
	if (b->fd < 0) {
		fprintf(stderr, "Error opening device \"%s\": %s\n",
				path, strerror(errno));
		goto fail;
	}

	if (ioctl(b->fd, I2C_SLAVE, b->addr) < 0) {
		fprintf(stderr, "Failed to acquire bus access for slave " \
				"0x%X: %s\n", b->addr, strerror(errno));
		goto fail;
	}

	if (!readregs(b, 0xAA, &b->calib, sizeof(b->calib))) {
		goto fail;
	}
	calib_betoh(b);

	return true;
 fail:
	bmp180_close(b);
	return false;
}

void bmp180_close(struct bmp180 *b)
{
	close(b->fd);
}

bool bmp180_reset(struct bmp180 *b)
{
	return writereg(b, REG_SOFT_RESET, 0xB6);
}

static bool readregs(struct bmp180 *b, uint8_t addr, void *buf, uint16_t len)
{
	struct i2c_msg msgs[] = {
		{
			.addr = b->addr,
			.flags = 0,
			.len = 1,
			.buf = &addr,
		}, {
			.addr = b->addr,
			.flags = I2C_M_RD,
			.len = len,
			.buf = buf,
		},
	};
	struct i2c_rdwr_ioctl_data msgset = {
		.msgs = msgs,
		.nmsgs = sizeof(msgs) / sizeof(struct i2c_msg),
	};

	if (ioctl(b->fd, I2C_RDWR, &msgset) < 0) {
		fprintf(stderr, "Failed to read registers: %s\n", strerror(errno));
		return false;
	}
	return true;
}

static bool writereg(struct bmp180 *b, uint8_t addr, uint8_t val)
{
	uint8_t buf[2] = {addr, val};
	ssize_t n = write(b->fd, buf, sizeof(buf));
	if (n < 0) {
		fprintf(stderr, "Failed to write to device: %s\n", strerror(errno));
		return false;
	} else if (n < sizeof(buf)) {
		fprintf(stderr, "Too few bytes written: %d of %d", n, sizeof(buf));
		return false;
	}
	return true;
}

static void calib_betoh(struct bmp180 *b)
{
	uint16_t *p = (uint16_t *) &b->calib;
	for (unsigned i = 0; i < sizeof(b->calib) / 2; i++)
		p[i] = be16toh(p[i]);
}
