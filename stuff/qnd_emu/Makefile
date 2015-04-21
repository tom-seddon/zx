SHAREDOPTS:=-g -O0 -Wall -D_XOPEN_SOURCE_EXTENDED -DEXECZ80 -DLSB_FIRST -DDEBUG
COPTS:=$(SHAREDOPTS)
CPPOPTS:=$(SHAREDOPTS)  -std=c++11
LOPTS:=-g -lncurses -lc++

.PHONY:all
all:
	mkdir -p .build
#	gcc -o .build/ConDebug.o -c ConDebug.c $(COPTS)
	gcc -o .build/Z80.o -c Z80.c $(COPTS)
#	gcc -o .build/Debug.o -c Debug.c $(COPTS)
	gcc -o .build/main.o -c main.cpp $(CPPOPTS)
	gcc -o qnd_emu .build/Z80.o .build/main.o $(LOPTS)

