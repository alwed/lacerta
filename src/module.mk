b := $(BUILD_DIR)

SRC += frame-enc.c tty_custom_baud.c
SRC += frame-dec.c
SRC += ssdv_split.c
SRC += shm.c pits_monitor.c
SRC += power.c mcp3426.c
SRC += pressure.c bmp180.c

OBJ_FENC += $b/frame-enc.o $b/tty_custom_baud.o
OBJ_FDEC += $b/frame-dec.o
OBJ_SPLIT += $b/ssdv_split.o
OBJ_MON += $b/pits_monitor.o $b/shm.o
OBJ_PWR += $b/power.o $b/mcp3426.o $b/shm.o
OBJ_PRS	+= $b/pressure.o $b/bmp180.o $b/shm.o
