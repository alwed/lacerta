#ifndef _SHM_H_
#define _SHM_H_

_Bool shm_openrw(int *fd, void *shm, const char *path);
_Bool shm_openro(int *fd, const void *shm, const char *path);
void shm_close(int fd, const void *shm);

#endif
