BEEBASM:=~/not-my/beebasm/beebasm
VOL:=~/beeb/beeb-files/stuff/zx/0
VERBOSE:=-v

.PHONY:all
all:
	mkdir -p .build
	$(BEEBASM) -i m128test.6502 -volume $(VOL) # $(VERBOSE)
	$(BEEBASM) -i m128test2.6502 -volume $(VOL) # $(VERBOSE)
	$(BEEBASM) -i zx_main.6502 -volume $(VOL) $(VERBOSE)

	set_bbc_lea --io $(VOL)/CM128TST
	set_bbc_lea --io $(VOL)/CM128TS2
	set_bbc_lea --io $(VOL)/_doZX
