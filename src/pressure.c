#include <signal.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

#include "bmp180.h"
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

        struct bmp180 b;
        const char *i2c_path = "/dev/i2c-3";
	uint16_t addr = 0x77;

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
	if (!bmp180_init(&b, i2c_path, addr)) {
		ret = 2;
		goto out;
	}

        signal(SIGINT, signal_exit);
        signal(SIGTERM, signal_exit);
	running = true;

	while (running) {
		usleep(1000000);

		if (!bmp180_measT(&b, NULL)) {
			fprintf(status_stream, "Error measuring temperature\n");
			continue;
		}
		if (!bmp180_measp(&b, 3, &pits->p)) {
			fprintf(status_stream, "Error measuring preassure\n");
			pits->p = 0;
			continue;
		}
	}
	fprintf(status_stream, "Closing\n");
	ret = 0;

 out:
	bmp180_close(&b);
	shm_close(shm_fd, pits);
	return ret;
}
