BEEBASM:=~/not-my/beebasm/beebasm
PASMO:=pasmo
VOL:=~/beeb/beeb-files/stuff/zx/0
TVOL:=~/beeb/beeb-files/stuff/zx/7
TSRC:=../tests
VERBOSE:= #-v
DEST:=../build
ZXBAOPTS:=

.PHONY:all
all:
	mkdir -p $(DEST)
	$(PASMO) --bin $(TSRC)/test0.s $(DEST)/test0.dat

	python ../tools/throwaway/make_zop_routines_skeleton.py > $(DEST)/z80ops.generated.6502

	$(BEEBASM) -i daa_test.6502 -volume $(VOL)
	$(BEEBASM) -i m128test.6502 -volume $(VOL) # $(VERBOSE)
	$(BEEBASM) -i m128test2.6502 -volume $(VOL) # $(VERBOSE)
	$(BEEBASM) -i zx_main.6502 -volume $(VOL) -l $(DEST)/zx_main.lst $(VERBOSE) $(ZXBAOPTS)
	$(BEEBASM) -i zx_load.6502 -volume $(VOL) -l $(DEST)/zx_load.lst $(VERBOSE) $(ZXBAOPTS)
#	$(BEEBASM) -i zx_writers.6502 -volume $(VOL) -l $(DEST)/zx_writers.lst $(VERBOSE) $(ZXBAOPTS)

	set_bbc_lea --io $(VOL)/CM128TST
	set_bbc_lea --io $(VOL)/CM128TS2
	set_bbc_lea --io $(VOL)/_doZX
	set_bbc_lea --io $(VOL)/_doZX2
	set_bbc_lea --io $(VOL)/_doZXW
