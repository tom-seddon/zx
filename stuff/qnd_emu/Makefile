SHAREDOPTS:=-g -O0 -Wall -D_XOPEN_SOURCE_EXTENDED -DEXECZ80 -DLSB_FIRST -DDEBUG -I/opt/local/include/SDL2
COPTS:=$(SHAREDOPTS)
CPPOPTS:=$(SHAREDOPTS)  -std=c++11
LOPTS:=-g -lncurses -lc++ -L/opt/local/lib -lSDL2 -lSDL2main

.PHONY:all
all:
	mkdir -p .build
#	gcc -o .build/ConDebug.o -c ConDebug.c $(COPTS)
	gcc -o .build/Z80.o -c Z80.c $(COPTS)
#	gcc -o .build/Debug.o -c Debug.c $(COPTS)
	gcc -o .build/main.o -c ./main.cpp $(CPPOPTS)
	gcc -o qnd_emu .build/Z80.o .build/main.o $(LOPTS)

