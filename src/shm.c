#include <errno.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

static size_t len;

bool shm_openrw(int *fd, void **shm, const char *path)
{
	len = sysconf(_SC_PAGESIZE);

	/* Invalidate output parameters */
	*fd = -1;
	*shm = NULL;

	/* Open file that will back the shared memory. */
	*fd = open(path, O_CREAT | O_RDWR, 0640);
	if (*fd < 0) {
		fprintf(stderr, "Error: Cannot open shared file: %s\n",
                                strerror(errno));
		goto fail;
	}

	/* Enlarge file if necessary */
        if (len > lseek(*fd, len, SEEK_SET)) {
                fprintf(stderr, "Error: Cannot seek shared file: %s\n",
                                strerror(errno));
                goto fail;
        }
        if (1 > write(*fd, "", 1)) {
                fprintf(stderr, "Error: Cannot write to shared file: %s\n",
                                strerror(errno));
                goto fail;
        }

	/* Map the file to memory */
	*shm = mmap(NULL, len, PROT_READ | PROT_WRITE, MAP_SHARED, *fd, 0);
        if (*shm == MAP_FAILED) {
                fprintf(stderr, "Error: Cannot mmap shared file: %s\n",
                                strerror(errno));
                goto fail;
        }
	return true;

 fail:
	munmap(*shm, len);
	close(*fd);
	return false;
}

bool shm_openro(int *fd, const void **shm, const char *path)
{
	len = sysconf(_SC_PAGESIZE);

	/* Invalidate output parameters */
	*fd = -1;
	*shm = NULL;

	/* Open file that will back the shared memory. */
	*fd = open(path, O_RDONLY);
	if (*fd < 0) {
		fprintf(stderr, "Error: Cannot open shared file: %s\n",
                                strerror(errno));
		goto fail;
	}

	/* Check if the file size is large enough to fit an entire page. */
	struct stat statbuf;
	fstat(*fd, &statbuf);
	if (statbuf.st_size < len) {
		fprintf(stderr, "Error: Shared file is not large enough\n");
		goto fail;
	}

	/* Map the file to memory */
	*shm = mmap(NULL, len, PROT_READ, MAP_SHARED, *fd, 0);
        if (*shm == MAP_FAILED) {
                fprintf(stderr, "Error: Cannot mmap shared file: %s\n",
                                strerror(errno));
                goto fail;
        }
	return true;

 fail:
	munmap(*(void **)shm, len);
	close(*fd);
	return false;
}

void shm_close(int fd, void *shm)
{
	munmap(shm, len);
	close(fd);
}
