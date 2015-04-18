BEEBASM:=~/not-my/beebasm/beebasm
PASMO:=pasmo
VOL:=~/beeb/beeb-files/stuff/zx/0
TVOL:=~/beeb/beeb-files/stuff/zx/7
TSRC:=../tests
VERBOSE:=-v
DEST:=../build

.PHONY:all
all:
	mkdir -p $(DEST)
	$(PASMO) --bin $(TSRC)/test0.s $(DEST)/test0.dat

	$(BEEBASM) -i m128test.6502 -volume $(VOL) # $(VERBOSE)
	$(BEEBASM) -i m128test2.6502 -volume $(VOL) # $(VERBOSE)
	$(BEEBASM) -i zx_main.6502 -volume $(VOL) $(VERBOSE)

	set_bbc_lea --io $(VOL)/CM128TST
	set_bbc_lea --io $(VOL)/CM128TS2
	set_bbc_lea --io $(VOL)/_doZX
