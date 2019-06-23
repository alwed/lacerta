d := codec2
b := $(BUILD_DIR)/$d

SRC += $d/fsk.c $d/fsk_demod.c  $d/modem_stats.c
SRC += $d/kiss_fft.c $d/kiss_fftr.c $d/octave.c $d/modem_probe.c
SRC += $d/mpdecode_core.c $d/phi0.c

OBJ_FSK += $b/fsk.o $b/fsk_demod.o $b/modem_stats.o $b/kiss_fft.o $b/kiss_fftr.o
OBJ_FSK += $b/octave.o $b/modem_probe.o

OBJ_FDEC += $b/mpdecode_core.o $b/phi0.o
