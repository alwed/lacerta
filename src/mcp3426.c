#include <endian.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/i2c-dev.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

/*#define MCP3426_ADDR 0x68

int main(int argc, char **argv)
{
	int adc;
	char *path;

	if (argc > 1) {
		path = argv[1];
	} else {
		path = "/dev/i2c-3";
	}

	adc = adc_init(path, MCP3426_ADDR);
	if (adc < 0)
		return 1;

	printf("%f V\t%f A\n", adc_get(adc, 0, 0) * 2.048 * 7.8 / INT16_MAX,
			 adc_get(adc, 1, 2) * 2.048 / .24 / 4 / INT16_MAX);
	close(adc);
	return 0;
}*/

int mcp3426_init(const char *path, unsigned addr)
{
	int adc = open(path, O_RDWR);
	if (adc < 0) {
		fprintf(stderr, "Error opening device \"%s\": %s\n",
				path, strerror(errno));
		return -1;
	}

	if (ioctl(adc, I2C_SLAVE, addr) < 0) {
		fprintf(stderr, "Failed to acquire bus access for slave " \
				"0x%X: %s\n", addr, strerror(errno));
		close(adc);
		return -1;
	}

	return adc;
}

void mcp3426_close(int adc)
{
	close(adc);
}

short mcp3426_get(int adc, unsigned channel, unsigned gain)
{
	uint8_t config = 0b10001000; /* !RDY, Channel 0, One-Shot, 16bit, Gain 1 */
	config |= (channel & 0x3) << 5; /* Channel bits: 6, 5 */
	config |= (gain & 0x3); /* Gain bits: 1, 0 */
	if (write(adc, &config, 1) < 1) {
		fprintf(stderr, "Error writing to slave: %s\n",
				strerror(errno));
		return 0;
	}

	union {
		char bytes[3];
		int16_t val;
	} resp;

	resp.bytes[2] = 0x80;
	while (resp.bytes[2] & 0x80) {
		usleep(20000); /* Wait for conversion */
		ssize_t n = read(adc, &resp, 3);
		if (n < 0) {
			fprintf(stderr, "Error reading from slave: %s\n",
					strerror(errno));
			return 0;
		} else if (n < 3) {
			fprintf(stderr, "Short slave response: %d of 3\n", n);
			for (int i = n; i < 3; i++) resp.bytes[i] = 0x80;
		}
//		char *buf = resp.bytes;
//		fprintf(stderr, "%02X %02X %02X\n", buf[0], buf[1], buf[2]);
	}
	return be16toh(resp.val);
}
