EXE_AIR := frame-enc pits_monitor power pressure
EXE_GND := fsk_demod frame-dec ssdv_split
EXE := $(EXE_AIR) $(EXE_GND)

MODULES := . codec2

BUILD_DIR ?= ../build

DEBUG ?= 1
ifeq ($(DEBUG), 1)		# general debug
	CFLAGS += -Og -g
else ifeq ($(DEBUG), 2)		# extensive debugging with sanitizer
	CFLAGS += -O0 -ggdb -fsanitize=address -fno-omit-frame-pointer
	CFLAGS += -fsanitize=undefined
	LDFLAGS += -fsanitize=address -fno-omit-frame-pointer
	LDFLAGS += -fsanitize=undefined
else ifeq ($(DEBUG), -1)	# debug the release code
	CFLAGS += -Og -g
else				# release
	CFLAGS	+= -O2 -flto
	LDFLAGS	+= -O2 -flto -s
endif
CFLAGS += -DDEBUG=$(DEBUG)

# Adapted from: Peter Miller "Recursive Make Considered Harmful", 1997
# http://lcgapp.cern.ch/project/architecture/recursive_make.pdf#page=10

DEPEND := ./depend.sh
MKDIR_P ?= mkdir -p

# look for include files in
# each of the modules
CFLAGS += -I. -Icodec2

# extra libraries if required
LIBS_FSK := -lm
LIBS_MON := -lm
LIBS_PWR := -lm
LIBS_PRS := -lm

# each module will add to this
SRC :=
OBJ :=
OBJ_FSK :=
OBJ_FDEC :=
OBJ_FENC :=
OBJ_SPLIT :=
OBJ_MON :=
OBJ_PWR	:=
OBJ_PRS :=

# include the description for each module
include $(patsubst %,%/module.mk,$(MODULES))

# determine the object files
OBJ += $(patsubst %.c,%.o, $(filter %.c,$(SRC)))

EXE := $(addprefix $(BUILD_DIR)/,$(EXE))
EXE_AIR := $(addprefix $(BUILD_DIR)/,$(EXE_AIR))
EXE_GND := $(addprefix $(BUILD_DIR)/,$(EXE_GND))
OBJ := $(addprefix $(BUILD_DIR)/,$(OBJ))

.PHONY: all clean air ground

ground: $(EXE_GND)
all: $(EXE)
air: $(EXE_AIR)

$(BUILD_DIR)/fsk_demod: $(OBJ_FSK)
	@printf "  LD\t$@\n"
	@$(CC) -o $@ $^ $(LIBS_FSK) $(LDFLAGS)

$(BUILD_DIR)/frame-enc: $(OBJ_FENC)
	@printf "  LD\t$@\n"
	@$(CC) -o $@ $^ $(LIBS_FENC) $(LDFLAGS)

$(BUILD_DIR)/frame-dec: $(OBJ_FDEC)
	@printf "  LD\t$@\n"
	@$(CC) -o $@ $^ $(LIBS_FDEC) $(LDFLAGS)

$(BUILD_DIR)/ssdv_split: $(OBJ_SPLIT)
	@printf "  LD\t$@\n"
	@$(CC) -o $@ $^ $(LIBS_SPLIT) $(LDFLAGS)

$(BUILD_DIR)/pits_monitor: $(OBJ_MON)
	@printf "  LD\t$@\n"
	@$(CC) -o $@ $^ $(LIBS_MON) $(LDFLAGS)

$(BUILD_DIR)/power: $(OBJ_PWR)
	@printf "  LD\t$@\n"
	@$(CC) -o $@ $^ $(LIBS_PWR) $(LDFLAGS)

$(BUILD_DIR)/pressure: $(OBJ_PRS)
	@printf "  LD\t$@\n"
	@$(CC) -o $@ $^ $(LIBS_PRS) $(LDFLAGS)

# include the C include dependencies
-include $(OBJ:.o=.d)

# calculate C include dependencies
$(BUILD_DIR)/%.d: %.c
	@printf " DEP\t$<\n"
	@$(MKDIR_P) $(dir $@)
	@$(DEPEND) $(dir $*) $(CFLAGS) $< > $@

# build C sources
$(BUILD_DIR)/%.o: %.c
	@printf "  CC\t$<\n"
	@$(MKDIR_P) $(dir $@)
	@$(CC) $(CPPFLAGS) $(CFLAGS) -c -o $@ $<

clean:
	@printf "CLEAN\n"
	@rm -rf $(BUILD_DIR)
