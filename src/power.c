#include <math.h>
#include <signal.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

#include "mcp3426.h"
#include "pits_info.h"
#include "shm.h"

static bool running;
void signal_exit(int s)
{
        if (s != SIGINT && s != SIGTERM)
                return;

        running = false;
}

int main(int argc, char **argv)
{
	int ret = 1;

        int adc = -1;
        const char *i2c_path = "/dev/i2c-3";
	uint16_t addr = 0x68;

	const char *shm_path = "/dev/shm/pits.shm";
	int shm_fd;
        struct pits_info *pits;

	FILE *status_stream = stdout;

        if (argc > 1)
		i2c_path = argv[1];
	if (argc > 2)
		addr = strtol(argv[2], NULL, 0);

	if (!shm_openrw(&shm_fd, &pits, shm_path)) {
		ret = 1;
		goto out;
	}
	adc = mcp3426_init(i2c_path, addr);
	if (adc < 0) {
		ret = 2;
		goto out;
	}

	signal(SIGINT, signal_exit);
	signal(SIGTERM, signal_exit);
	running = true;

	while (running) {
		usleep(1000000);

		pits->vbat = round(0x400 * mcp3426_get(adc, 0, 0)
				* 2.048 * 7.8 / INT16_MAX);
		pits->isys = round(0x4000 * mcp3426_get(adc, 1, 2)
				* 2.048 / .24 / 4 / INT16_MAX);

	}
	fprintf(status_stream, "Closing\n");
	ret = 0;

 out:
	mcp3426_close(adc);
	shm_close(shm_fd, pits);
	return ret;
}
