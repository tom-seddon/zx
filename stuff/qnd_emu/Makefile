COPTS:=-g -O0 -Wall -D_XOPEN_SOURCE_EXTENDED -DEXECZ80 -DLSB_FIRST
LOPTS:=-g -lncurses

.PHONY:all
all:
	mkdir -p .build
	gcc -o .build/ConDebug.o -c ConDebug.c $(COPTS)
	gcc -o .build/Z80.o -c Z80.c $(COPTS)
	gcc -o .build/Debug.o -c Debug.c $(COPTS)
	gcc -o .build/main.o -c main.cpp $(COPTS)
	gcc -o qnd_emu .build/ConDebug.o .build/Z80.o .build/Debug.o .build/main.o $(LOPTS)

