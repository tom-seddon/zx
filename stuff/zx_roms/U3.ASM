
#define DEFB .BYTE
#define DEFW .WORD
#define EQU  .EQU
#define ORG  .ORG

; ========================
; UTILITY3 v1.3
; ========================
;
; UTILITY3 a disassembler for the ZX Spectrum which
; incorporates routine DIS-Z80 by John Kerr. 
; It also uses adaptations of scrolling routines
; and keyboard-reading routines from the Spectrum ROM.
; The pocket calculator style font looks a little familiar too.
; 
; ========================

; ========================
; 
; U3 is a self-contained, screen-resident disassembler written in
; 2K of memory. It is designed to load at address $4000 and re-locate 
; itself to $5000. The main subroutine, DIS-Z80 was written by John Kerr 
; and published in SUBSET 1987.
; The program will work on any Spectrum and doesn't make OS calls.
;
;========================


ORG $5000


; Note this section is
; normally executed at $4000


	LD 	HL,$4000  	; begin by relocating the entire 2K
	LD 	DE,$5000  	; block of instructions from the top 
	LD 	BC,$0800  	; third of the screen to the lower
	LDIR         		; third creating a print area in the 
                                ; top two thirds - 16 lines numbered
                                ; line 0 - line 15.

; Ensure that the attributes at end of line 15 are black ink on cyan paper.

	LD 	HL,$59FC

ATTLP	LD  	(HL),$28
	INC 	L
	JR 	NZ,ATTLP
	DEC 	L

; copy the colour attributes on line 15 to preceding lines 0-14.
; Note a cyan column helps highlight the ASCII text.

	LD 	DE,$59DF  	; end of line 14 attributes.
	LD 	BC,$01E0  	; number of bytes to fill.
	LDDR

; Now check if Interface 1 is present and initialized
; If so allow ROM 4 to be paged. (Not relevant to +3).
; This cautious approach prevents a BASIC error code being generated
; should Interface 1 not be present. 


	LD 	A,(IY+$7C)	; shadow system variable FLAGS3 
				; or first byte of CHANS area.
	AND 	A       	; test - will be zero if shadow ROM initialized.
	JR 	NZ,NOSHDW  	; skip to NOSHDW if not  

	LD 	HL,MAXROM	; enable paging of Shadow ROM
	INC 	(HL)    	; increase from 4 to 5.

NOSHDW 	JP 	MAIN		; jump to main entry point now in lower screen 

; --------------------------------------------------------------------
; The above code although copied to lower screen is no longer required
; If space were at a premium it could be executed on another screen line.
; --------------------------------------------------------------------

; --------------
; The next routine pages in a ROM in the range 0-4
; --------------

ROM  	DI			; disable interrupts until end.
     	LD 	A,'?'      	; prompt
     	LD 	($50FF),A 	; "ROM?"
     	CALL 	ROMTXT  	; large

ROML 	CALL 	KEY		; wait for a valid keypress.

	LD 	HL,MAXROM	; holds 4 or 5
     	CP 	(HL)     	; compare against upper limit 4/5 
     	JR 	NC,ROML   	; loop back if too high.

     	LD 	E,A       	; select ROM
     	CALL 	ROMSEL  	; and continue into disassembly loop.

; Note. the call to ROMSEL puts the address of MAIN on the stack.

;========================
;
; Initial Entry Point.
;
;========================

MAIN   	LD 	HL,0 		; start address is initially zero 
				; and reset to zero after a ROM switch.

MAINLP 	LD 	(DISADD),HL	; update disassembly address.

      	CALL 	ROMTXT		; large print in lower screen shows
				; the current ROM.


; The start of the main disassembly loop.

DLOOP  	LD 	B,8 		; disassemble 8 lines at a time.

BLOOP  	PUSH 	BC		; save line count. 

      	CALL 	SCROLL		; scroll top 16 lines upwards

      	LD 	DE,(DISADD)	; pick up address in DE
      	PUSH 	DE		; save it

;------------------------
      	CALL 	DISZ80		; disassemble one instruction.
;------------------------

      	LD 	(DISADD),DE	; save new disassembly address.

      	LD 	B,3     	; print

GAP   	CALL 	CHROP 		; a three
      	DJNZ 	GAP    		; space gap.

      	POP 	HL     		; pop the old disassembly address

TEXTLP	LD 	A,(HL)   	; print
      	INC 	HL     		; ASCII
      	CALL 	CHROP 		; TEXT to help distinguish 
      	AND 	A		; instructions
      	SBC 	HL,DE		; from data.
       	JR 	NC,TXTEND	; finished when addresses match. 

      	ADD 	HL,DE		; loop back until HL matches DE
      	JR 	TEXTLP		; could be 1 to 4 characters

TXTEND	POP 	BC     		; restore the counter
      	DJNZ 	BLOOP   	; and loop back for 8 lines

      	CALL 	KEY   		; get a keypress.

      	CP 	16      	; is it Enter ?
      	JR 	Z,DLOOP 	; back if so for another 8 lines.

      	CP 	17      	; is it 'R' ?
      	JR  	Z,ROM		; back to ROM routine if so.

      	CP 	18      	; is it 'Q' ?
      	JR  	Z,QUIT		; forward if so to quit

; By elimination a  numeric key (0-F) has been pressed so continue to build
; up  a hex number. The HL pair will initially hold 0 from the KEY routine. 
; First time through the loop, the value will be $00 - $0F. Any key higher,
; usually ENTER, causes the hex input to be accepted. 


HEX_LP 	CP 	$10     	; is key higher than hex digit ?

      	JR 	NC,MAINLP 	; back to main loop with ENTER, etc.
				; and a new disassembly address.

      	ADD 	HL,HL 		; rotate the
      	ADD 	HL,HL 		; nibble to the left
      	ADD 	HL,HL 		; losing the
      	ADD 	HL,HL 		; 5'th character.

      	OR 	L
      	LD 	L,A    		; insert new hex digit.

      	EX 	DE,HL           ; transfer address to DE

      	CALL 	CLINE		; clear line 15
      	CALL 	ADRSP		; print DE as HEX then a space
      	PUSH 	DE		; save the address.

      	CALL  	BIGPR           ; scan text to produce large text
				; in lower third.
      	POP 	HL		; restore address to HL.

	LD 	D,$A0		; outer adjustable delay counter.

DELAY	PUSH 	HL		; 21-cycle
	POP	HL		; delay.
	PUSH	HL		; and again.
	POP	HL		;
	DJNZ	DELAY		; decrement inner counter and loop

	DEC	D		; decrement outer counter.

      	JR 	NZ,DELAY	; back to DELAY1 while D not zero.

      	CALL 	KEY 		; get a keypress.

      	JR 	HEX_LP		; and back to hex input loop

; ------------------
;
; Select ROM.
;
; ------------------ 

ROM3   	LD 	E,3		; Amstrad named the original ROM ROM3.

ROMSEL 	LD 	A,($700) 	; fetch the byte at location $700.
       	CP 	201      	; is it the RET instruction ?
       	CALL 	Z,$700 		; if it is then call it.

; Note. Interface 1 is un-paged by an instruction fetch on 0x700. The above 
; code would have no ill effects if another ROM had a RET at same address.

       	LD 	A,E		; fetch desired ROM $00-$04
       	OR 	'0'        	; add to ascii base character.
       	LD 	($50FF),A 	; place after letters "ROM"

       	CP 	'4'       	; is Interface 1 ROM required.
       	JR 	NZ,PLUS3	; forward to consider 128K ROMS

       	DEC 	E      		; change 4 to 3.
       	CALL 	PLUS3 		; ensure main Basic ROM is active.

       	LD 	HL,0     	; a dummy address
       	PUSH 	HL     		; is pushed on the stack.

       	JP 	$0008       	; jump to location $0008.

; Note. An instruction fetch on address $0008 pages in Interface 1.
; A routine in the Interface 1 ROM will drop the zero off the stack.
; It will then return to the Main Entry Point leaving the shadow ROM paged in.
; This method which tricks Interface 1 into thinking that the CALBAS routine 
; has been used, avoids writing to RAM areas outside the screen area.
; Use this program with an Interface 1 supporting emulator to see what happens
; on the other side. Or use with the real hardware.

; The various 128K Spectrums page in the various ROMS using OUT instructions.
; These have no adverse affects on Spectrums that have only a single ROM.

PLUS3   LD 	A,(23399)
        AND 	248
        BIT 	1,E
        JR 	Z,SW1

        OR  	4

SW1     LD 	BC,$1FFD
        OUT 	(C),A

        LD 	A,(23388)
        BIT 	0,E
        JR 	NZ,SW2

        RES 	4,A

SW2     LD 	BC,$7FFD
        OUT 	(C),A
        RET

;====================
;
; Before returning to BASIC select the main ROM, discourage re-entry
; with an all-white display and enable interrupts.
;
;====================

QUIT    CALL ROM3

        LD 	HL,$57FF
        LD 	DE,$5800
        LD 	BC,$0300
        LDIR

        EI

LABEND  RET   			; Finish  >>>

; ---
; Note. there is a gap of approx 16 unused bytes here.
; ---

ORG $50F8

; Three Program Variables.

DISADD 	DEFW 	0		; two byte disassembly address.
PRIPOS  DEFB 	0     		; low byte of print position.
MAXROM  DEFB 	4               ; one more than maximum ROM allowed.



; ---

ORG $50FC

; This message terminates at a page boundary and requires no end marker.

	DEFB "ROM3"

; ====================
; DIS-Z80 was published in the SUBSET column of Personal Computer World 1987.
; The routine disassembles a single Z80 instruction at address DE. 
; It is required to be followed by a routine called CHROP that outputs a 
; single ASCII character.
; It was originally developed for CP/M on an Amstrad CPC128.
; The original ORG was $0100. I have added $5000 to all addresses.
; The stated aim was to write a Z80 disassembly routine in as short a space
; as possible and, at just over 1K (1090 bytes), it is a rather incredible 
; program. 
; The SUBSET editor David Barrow was able to trim only one byte from John 
; Kerr's compact code. I've forgotten where so there's a challenge.
; ====================

ORG $5100


DISZ80 	CALL 	ADRSP
       	LD 	BC,$0900
       	LD 	HL,$2020

BUFFER 	PUSH 	HL
       	DJNZ 	BUFFER
       	LD 	H,B
       	LD 	L,C
       	ADD 	HL,SP

       	PUSH 	BC
       	EX 	(SP),IX
       	PUSH 	BC
       	PUSH 	BC
       	ADD 	IX,SP

       	PUSH 	HL
       	LD 	HL,GROUP3

TRYNDX 	CALL 	FETCH

       	LD 	B,C
       	CP 	$ED
       	JR 	Z,CONFLG

       	INC 	B
       	CP 	$DD
       	JR 	Z,CONFLG

       	INC 	B
       	CP 	$FD
       	JR 	NZ,NOTNDX

CONFLG 	LD 	(IX+1),B
       	INC 	B
       	DJNZ 	TRYNDX

       	JR 	NXBYTE

NOTNDX 	LD 	C,A
       	LD 	A,(IX+1)
       	OR 	A
       	JR 	Z,NODISP

       	LD 	A,C
       	CP 	$CB
       	JR 	Z,GETDIS

       	AND 	$44
       	CP 	4
       	JR 	Z,GETDIS

       	LD 	A,C
       	AND 	$C0
       	CP 	$40
       	JR 	NZ,NODISP

GETDIS 	CALL 	FETCH
       	LD 	(IX+2),A

NODISP 	LD 	HL,GROUP1
       	LD 	A,C
       	CP 	$CB
       	JR 	NZ,NEWMSK

       	LD 	HL,GROUP2

NXBYTE 	CALL 	FETCH
       	LD 	C,A

NEWMSK 	LD 	A,(HL)
       	OR 	A
       	JR 	Z,TABEND

       	AND 	C
       	INC 	HL

NEWMOD 	LD 	B,(HL)
       	INC 	HL
       	INC 	B
       	JR 	Z,NEWMSK

TRYMAT 	CP 	(HL)
       	INC 	HL
       	JR 	Z,GETNDX

       	BIT 	7,(HL)
       	INC 	HL
       	JR 	Z,TRYMAT

       	JR 	NEWMOD

GETNDX 	LD 	A,(HL)
       	AND 	$7F
       	DEC 	B

TABEND 	POP 	HL
       	PUSH 	DE
       	PUSH 	HL

       	EX 	DE,HL
       	LD 	HL,MONICS
       	CALL 	XTRACT

       	POP 	HL
       	LD 	DE,5
       	ADD 	HL,DE
       	POP 	DE

       	LD 	A,B
       	AND 	$F0
       	JR 	Z,SECOND

       	RRA
       	RRA
       	RRA
       	RRA
       	PUSH 	BC

       	LD 	B,A
       	LD 	A,C
       	CALL 	OPRND1

       	POP 	BC
       	LD 	A,B
       	AND 	$0F
       	JR 	Z,OPDONE

       	LD 	(HL),44  		;,
       	INC 	HL

SECOND 	LD 	A,B
       	AND 	$0F

       	LD 	B,A
       	LD 	A,C
       	CALL 	NZ,OPRND2

OPDONE 	LD 	A,3
       	SUB 	(IX)

       	POP 	HL
       	POP 	HL
       	POP 	IX

       	JR 	C,OUTEXT

       	INC 	A
       	LD 	B,A
       	ADD 	A,B
       	ADD 	A,B
       	LD 	B,A

SPACES 	LD 	A,$20
       	CALL 	CHROP
       	DJNZ 	SPACES

OUTEXT 	LD 	B,18

PUTOUT 	DEC 	SP
       	POP 	HL
       	LD 	A,H
       	CALL 	CHROP
       	DJNZ 	PUTOUT

       	RET

;***********************

GROUP2 	DEFB 	$C0,$36,$40
	DEFB 	$04,$80,$2D,$C0,$BE
	DEFB 	$FF,$F8,$06,$00,$33
	DEFB 	$08,$38,$10,$35,$18
	DEFB 	$3A,$20,$3F,$28,$40
	DEFB 	$30,$00,$38,$C1


GROUP1 	DEFB 	$FF,$00,$00
	DEFB 	$24,$07,$32,$0F,$37
	DEFB 	$17,$31,$1F,$36,$27
	DEFB 	$0D,$2F,$0B,$37,$3D
	DEFB 	$3F,$06,$76,$14,$C9
	DEFB 	$30,$D9,$12,$F3,$0F
	DEFB 	$FB,$91,$72,$C6,$02
	DEFB 	$CE,$01,$DE,$BC,$02
	DEFB 	$D6,$42,$E6,$03,$EE
	DEFB 	$43,$F6,$25,$FE,$8C
	DEFB 	$04,$08,$93,$01,$10
	DEFB 	$10,$18,$9D,$AF,$22
	DEFB 	$A2,$FA,$2A,$A2,$A7
	DEFB 	$32,$A2,$7A,$3A,$A2
	DEFB 	$03,$C3,$1C,$CD,$85
	DEFB 	$97,$D3,$AA,$79,$DB
	DEFB 	$9B,$5F,$E3,$93,$0E
	DEFB 	$E9,$9C,$05,$EB,$93
	DEFB 	$DF,$F9,$A2,$FF,$C0
	DEFB 	$B6,$40,$A2,$FF,$F8
	DEFB 	$76,$80,$02,$88,$01
	DEFB 	$98,$BC,$06,$90,$42
	DEFB 	$A0,$03,$A8,$43,$B0
	DEFB 	$25,$B8,$8C,$FF,$C7
	DEFB 	$0B,$04,$16,$05,$8E
	DEFB 	$B2,$06,$A2,$20,$C0
	DEFB 	$B0,$23,$C2,$1C,$C4
	DEFB 	$85,$10,$C7,$BB,$FF
	DEFB 	$CF,$D3,$01,$A2,$0D
	DEFB 	$03,$16,$0B,$8E,$FD
	DEFB 	$09,$82,$60,$C1,$2B
	DEFB 	$C5,$AC,$FF,$E7,$21
	DEFB 	$20,$9D,$FF,$EF,$E7
	DEFB 	$02,$A2,$7E,$0A,$A2


GROUP3 	DEFB 	$FF,$00,$44
	DEFB 	$23,$45,$2F,$4D,$2E
	DEFB 	$4E,$00,$67,$39,$6F
	DEFB 	$34,$70,$00,$71,$00
	DEFB 	$A0,$21,$A1,$0A,$A2
	DEFB 	$1A,$A3,$29,$A8,$1F
	DEFB 	$A9,$08,$AA,$18,$AB
	DEFB 	$28,$B0,$20,$B1,$09
	DEFB 	$B2,$19,$B3,$27,$B8
	DEFB 	$1E,$B9,$07,$BA,$17
	DEFB 	$BB,$A6,$FF,$C7,$B8
	DEFB 	$40,$9B,$8B,$41,$AA
	DEFB 	$FF,$CF,$FD,$42,$3C
	DEFB 	$4A,$81,$AD,$43,$A2
	DEFB 	$DA,$4B,$A2,$FF,$E7
	DEFB 	$40,$46,$95,$FF,$F7
	DEFB 	$C7,$47,$A2,$7C,$57
	DEFB 	$A2,$FF,$00

;_______________

MONICS 	DEFB 	$BF
	DEFB 	'A','D','C'+$80   	; ADC 
	DEFB 	'A','D','D'+$80   	; ADD 
	DEFB 	'A','N','D'+$80   	; AND 
	DEFB 	'B','I','T'+$80   	; BIT 
	DEFB 	'C','A','L','L'+$80	; CALL 
	DEFB 	'C','C','F'+$80   	; CCF
	DEFB 	'C','P','D','R'+$80	; CPDR
	DEFB 	'C','P','D'+$80   	; CPD
	DEFB 	'C','P','I','R'+$80	; CPIR
	DEFB 	'C','P','I'+$80   	; CPI
	DEFB 	'C','P','L'+$80   	; CPL
	DEFB 	'C','P'+$80      	; CP 
	DEFB 	'D','A','A'+$80   	; DAA
	DEFB 	'D','E','C'+$80   	; DEC 
	DEFB 	'D','I'+$80      	; DI
	DEFB 	'D','J','N','Z'+$80	; DJNZ 
	DEFB 	'E','I'+$80      	; EI
	DEFB 	'E','X','X'+$80   	; EXX
	DEFB 	'E','X'+$80      	; EX 
	DEFB 	'H','A','L','T'+$80	; HALT
	DEFB 	'I','M'+$80      	; IM 
	DEFB 	'I','N','C'+$80   	; INC 
	DEFB 	'I','N','D','R'+$80	; INDR
	DEFB 	'I','N','D'+$80   	; IND
	DEFB 	'I','N','I','R'+$80	; INIR
	DEFB 	'I','N','I'+$80   	; INI
	DEFB 	'I','N'+$80      	; IN 
	DEFB 	'J','P'+$80      	; JP 
	DEFB 	'J','R'+$80      	; JR 
	DEFB 	'L','D','D','R'+$80	; LDDR
	DEFB 	'L','D','D'+$80   	; LDD
	DEFB 	'L','D','I','R'+$80	; LDIR
	DEFB 	'L','D','I'+$80   	; LDI
	DEFB 	'L','D'+$80      	; LD 
	DEFB 	'N','E','G'+$80   	; NEG
	DEFB 	'N','O','P'+$80   	; NOP
	DEFB 	'O','R'+$80      	; OR 
	DEFB 	'O','T','D','R'+$80	; OTDR
	DEFB 	'O','T','I','R'+$80	; OTIR
	DEFB 	'O','U','T','D'+$80	; OUTD
	DEFB 	'O','U','T','I'+$80	; OUTI
	DEFB 	'O','U','T'+$80   	; OUT 
	DEFB 	'P','O','P'+$80   	; POP 
	DEFB 	'P','U','S','H'+$80	; PUSH 
	DEFB 	'R','E','S'+$80   	; RES 
	DEFB 	'R','E','T','I'+$80	; RETI
	DEFB 	'R','E','T','N'+$80	; RETN
	DEFB 	'R','E','T'+$80   	; RET
	DEFB 	'R','L','A'+$80   	; RLA
	DEFB 	'R','L','C','A'+$80	; RLCA
	DEFB 	'R','L','C'+$80   	; RLC 
	DEFB 	'R','L','D'+$80   	; RLD
	DEFB 	'R','L'+$80      	; RL 
	DEFB 	'R','R','A'+$80   	; RRA
	DEFB 	'R','R','C','A'+$80	; RA
	DEFB 	'R','R','C'+$80   	; RRC 
	DEFB 	'R','R','D'+$80   	; RRD
	DEFB 	'R','R'+$80      	; RR 
	DEFB 	'R','S','T'+$80   	; RST 
	DEFB 	'S','B','C'+$80   	; SBC 
	DEFB 	'S','C','F'+$80   	; SCF
	DEFB 	'S','E','T'+$80   	; SET 
	DEFB 	'S','L','A'+$80   	; SLA 
	DEFB 	'S','R','A'+$80   	; SRA 
	DEFB 	'S','R','L'+$80   	; SRL 
	DEFB 	'S','U','B'+$80   	; SUB 
	DEFB 	'X','O','R'+$80   	; XOR 



;*****************

OPRND1 	DJNZ 	CONDIT

RSTADR 	AND 	$38
       	JR 	DA

OPRND2 	DJNZ 	DAT8

RELADR 	CALL 	FETCH
       	LD 	C,A
       	RLA
       	SBC 	A,A
       	LD 	B,A
       	EX 	DE,HL
       	PUSH 	HL
       	ADD 	HL,BC
       	JR 	DHL

CONDIT 	RRA
       	RRA
       	RRA
       	DJNZ 	BITNUM

       	BIT 	4,A
       	JR 	NZ,ABS

       	AND 	3
	
ABS    	AND 	7
       	ADD 	A,$14
       	JR 	PS1

DAT8   	DJNZ 	DAT16

D8     	CALL 	FETCH
       	JR 	DA

BITNUM 	DJNZ 	INTMOD
       	AND 	7

DA     	LD 	C,A
       	SUB 	A
       	JR 	DAC

DAT16  	DJNZ 	EXAF
	
D16    	CALL 	FETCH
       	LD 	C,A
       	CALL 	FETCH

DAC    	EX 	DE,HL
       	PUSH 	HL
       	LD 	H,A
       	LD 	L,C

DHL    	LD 	C,$F8
       	PUSH 	HL
       	CALL 	CONVHL
       	POP 	HL
       	LD 	BC,$000A
       	OR 	A
       	SBC 	HL,BC
       	POP 	HL
       	EX 	DE,HL
       	RET 	C

       	LD 	(HL),'H'
       	INC 	HL
       	RET


INTMOD 	DJNZ 	STKTOP
       	AND 	3
       	ADD 	A,$1C
	
PS1    	JR 	PS3

STKTOP 	LD 	C,$13
       	DEC 	B
       	JR 	Z,PS2

REG16P 	DJNZ 	COMMON
       	RRA
       	AND 	3
       	CP 	3
       	JR 	NZ,RX

       	DEC 	A
       	JR 	RNX

EXAF   	LD 	C,$0A
       	DEC 	B
       	JR 	Z,PS2

EXDE   	INC 	C
       	DEC 	B
       	JR 	Z,PS2

REG8S  	DJNZ 	ACCUM

R8     	AND 	7
       	CP 	6
       	JR 	NZ,PS3

       	LD 	(HL),'('
       	INC 	HL
       	CALL 	REGX
       	LD 	A,(IX+2)
       	OR 	A
       	JR 	Z,RP

       	LD 	(HL),43 		;+
       	RLCA
       	RRCA
       	JR 	NC,POS

       	LD 	(HL),45			;-
       	NEG

POS    	INC 	HL
       	EX 	DE,HL
       	PUSH 	HL
       	LD 	H,B
       	LD 	L,A
       	LD 	C,$FB
       	CALL 	CONVHL
       	POP 	HL
       	EX 	DE,HL
       	JR 	RP

ACCUM  	RRA
       	RRA
       	RRA

COMMON 	LD 	C,7
       	DEC 	B
       	JR 	Z,PS2

PORTC  	DEC 	C
       	DJNZ 	IDAT8

PS2    	LD 	A,C
PS3    	JR 	PS4

IDAT8  	DJNZ 	IDAT16
       	LD 	(HL),'('
       	INC 	HL
       	CALL 	D8
       	JR 	RP

IDAT16 	DJNZ 	REG8
       	LD 	(HL),'('
       	INC 	HL
       	CALL 	D16
       	JR 	RP

REG8   	DEC 	B
       	JR 	Z,R8

IPAREF 	DJNZ 	REG16
       	AND 	9
       	JR 	PS4

REG16  	RRA
       	DJNZ 	IREG16

R16    	AND 	3
RX     	CP  	2
       	JR 	Z,REGX

RNX    	ADD 	A,$0C
       	JR 	PS4

IREG16 	DJNZ 	REGX
       	LD 	(HL),'('
       	INC 	HL
       	CALL 	R16

RP     	LD 	(HL),')'
       	INC 	HL
       	RET

REGX   	LD 	A,(IX+1)
       	ADD 	A,$10

PS4    	EX 	DE,HL
       	PUSH 	HL
       	LD 	HL,RGSTRS
       	CALL 	XTRACT
       	POP 	HL
       	EX 	DE,HL
       	RET

;*************

RGSTRS 	DEFB 	'B'				+$80
	DEFB 	'C'       			+$80
	DEFB 	'D'       			+$80
	DEFB 	'E'       			+$80
	DEFB 	'H'       			+$80
	DEFB 	'L'       			+$80
	DEFB 	"(","C",')' 			+$80
	DEFB 	'A'       			+$80
	DEFB 	'I'       			+$80
	DEFB 	'R'       			+$80
	DEFB 	"A","F",",","A","F",'''		+$80
	DEFB 	"D","E",",","H",'L'    		+$80
	DEFB 	"B",'C'             		+$80
	DEFB 	"D",'E'             		+$80
	DEFB 	"A",'F'             		+$80
	DEFB 	"S",'P'             		+$80
	DEFB 	"H",'L'             		+$80
	DEFB 	"I",'X'             		+$80
	DEFB 	"I",'Y'             		+$80
	DEFB 	"(","S","P",')'       		+$80
	DEFB 	"N",'Z'             		+$80
	DEFB 	'Z'                		+$80
	DEFB 	"N",'C'             		+$80
	DEFB 	'C'                		+$80
	DEFB 	"P",'O'             		+$80
	DEFB 	"P",'E'             		+$80
	DEFB 	'P'                		+$80
	DEFB 	'M'                		+$80
	DEFB 	'0'    				+$80
	DEFB 	'?'    				+$80
	DEFB 	'1'    				+$80
	DEFB 	'2'    				+$80

;********************

CONVHL 	SUB 	A

CVHL1  	PUSH 	AF
       	SUB 	A
       	LD 	B,16

CVHL2  	ADD 	A,C
       	JR 	C,CVHL3
       	SUB 	C

CVHL3  	ADC 	HL,HL
       	RLA
       	DJNZ 	CVHL2

       	JR 	NZ,CVHL1

       	CP 	10
       	INC 	B
       	JR 	NC,CVHL1

CVHL4  	CP 	10
       	SBC 	A,$69
       	DAA
       	LD 	(DE),A
       	INC 	DE
       	POP 	AF
       	JR 	NZ,CVHL4

       	RET

;****************

XTRACT 	OR 	A
       	JR 	Z,COPY

SKIP   	BIT 	7,(HL)
       	INC 	HL
       	JR 	Z,SKIP

       	DEC 	A
       	JR 	NZ,SKIP

COPY   	LD 	A,(HL)
       	RLCA
       	SRL 	A
       	LD 	(DE),A

       	INC 	DE
       	INC 	HL
       	JR 	NC,COPY

       	RET

;*******************

FETCH  	LD 	A,(DE)
       	INC 	DE
       	INC 	(IX+0)
       	PUSH 	AF
       	CALL 	BYTSP
       	POP 	AF
       	RET

ADRSP  	LD 	A,D
       	CALL 	BYTOP
       	LD 	A,E

BYTSP  	CALL 	BYTOP
       	LD 	A,$20
       	JR 	CHROP

BYTOP  	PUSH 	AF
       	RRA
       	RRA
       	RRA
       	RRA
       	CALL 	HEXOP
       	POP 	AF

HEXOP  	AND 	$0F
       	CP 	10
       	SBC 	A,$69
       	DAA

; -----------------------------------
;
; End of John Kerr's DIS-Z80 routine.
; 
; The next routine outputs a character.
;
; -------------------------------------

CHROP  	PUSH 	HL
       	PUSH 	DE
       	PUSH 	BC

       	CALL 	RITE

       	POP 	BC
       	POP 	DE
       	POP 	HL

       	RET

;=======================
;
; This scrolling subroutine scrolls the lower 15 lines up by one character 
; position. Text line 8 is copied across a third of the screen to text 
; line 7. Text line 8 is also, for simplicity, copied to line 15 just before
; line 15 is cleared. This is purely to enable the DE register to advance 
; linearly while the source register is adjusted to pick up the appropriate
; text. 
;
;=======================


SCROLL  LD 	HL,$4020		; set source
	LD 	DE,$4000		; set destination

SLOOP	LD 	BC,$00E0		; 7 lines to move

	LDIR				; copy the lines 

	LD 	C,$20			; prepare to copy one line - 32 bytes.

	LD 	A,H			; fetch the high byte of source
	CP 	$50			; is it in lower third ?
	JR 	Z, CLINE		; exit if so to clear 15'th
					; line to accept new text..

	CP 	$49			; if in middle third of screen
	JR 	NC,SAME 		; don't adjust source.

    	ADD 	A,7			; but if destination is text line 7
	LD 	H,A			; then adjust to point across a third.

	LDIR				; copy 32 bytes across thirds.

	SUB 	7			; restore source to top third again as
	LD 	H,A			; there are more moves within third.
	
	JR 	SLOOP			; back to scrolling loop.

SAME	LDIR				; this briefly copies line 8 to 15.
					; copying line 16 to 15 is harmless 
					; but looks awful.

	JR 	SLOOP			; back to scrolling loop.


;====================
;
;This routine clears text line 15 which consists of eight pixel lines.
;
;====================

CLINE  	LD 	BC,$0800 		; set counter to 8, C to zero.
       	LD 	H,$48   		; high byte of initial screen address.

CLOOP1 	LD 	L,$E0    		; all pixel lines have $E0 as start,
					; and $FF as end.

CLOOP2 	LD 	(HL),C   		; insert a zero.
       	INC 	L			; address next horizontal byte
       	JR 	NZ,CLOOP2		; loop until L is zero.   

       	INC 	H			; address next vertical byte.
       	DJNZ 	CLOOP1			; and repeat for all 8 lines, 
					; continuing to set print position.

; Set up print plot mask in the alternate accumulator.

	LD 	A,$80			; prepare plotting mask 10000000
	EX 	AF,AF'			; save in alternate accumulator

	LD 	A,$E0			; start of line 15 is $E0
	LD 	(PRIPOS),A		; set print position variable.

	RET				; return.

;======================
;
; This is the PRINT routine which prints on line 15 only. The line must have 
; been cleared previously. As the bitmaps are stored as vertical slices of
; a character and have to be laid down one pixel at a time, the 
; routine 'plots' the characters onto the screen.
;
;======================

RITE  	LD 	C,6			; prepare to advance 6 pixels for a 
					; space


      	CP 	123			; is character higher than 'z' ? 
      	JR 	NC,UPD6			; forward to update by six pixels

      	SUB 	39			; reduce to range 0 - 83 decimal
      	JR 	C,UPD6			; forward to print as space if less
					; than "'"

      	LD 	D,$56 			; high byte of character set start.

      	LD 	B,A   			; multiply
      	RLC 	B    			; by
      	ADD 	A,B  			; three  - max is 249 decimal.
      	ADD 	A,B			; five   - max is 415 decimal
      	JR 	NC,RITE1		; if last addition produced no carry
                                        ; skip to use $56 as high byte.

      	INC 	D 			; else increment high byte in D to $57.

RITE1 	LD 	E,A			; transfer low byte to E

      	LD 	B,$05 			; count five source bytes.

RITE2  	LD 	HL,(PRIPOS)		; fetch screen address low byte.

	LD 	H,$48			; set high byte.

      	LD 	A,(DE)			; fetch a character bitmap.
      	INC 	DE    			; address next source byte.

RITE3  	RRCA      			; is the bit set?
      	JR 	NC,RITE4		; forward to leave corresponding 
					; screen pixel unset if not so.

  	EX 	AF,AF'                  ; switch in the 'plot' mask.
 	PUSH 	AF			; preserve it on machine stack.
	OR 	(HL)			; combine with what's on the screen.
	LD 	(HL),A			; and update screen address
	POP 	AF			; restore mask.
	EX 	AF,AF'      		; and save for future use.

RITE4  	INC 	H     			; advance vertically down the screen.

      	BIT 	4,H   			; when high byte reaches $50 then this
					; program is about to be overwritten.

      	JR  	Z,RITE3			; otherwise loop for all 8 bits.

      	CALL 	UPD1  			; update mask and possibly the low 
					; byte of screen address.

      	DJNZ 	RITE2			; repeat for all 5 vertical slices.

; then continue into update routine to create a 1 pixel gap between characters.


;===================
;
; The update routine modifies the plotting mask rotating by a single pixel 
; if C holds 1 but by 6 pixels if C holds 6. The screen address may be 
; incremented.
; The routine is also entered at UPD6 with C holding 6 to print a space.
;
;===================


UPD1	LD 	C,$01			; update by 1 pixel.

; -->

UPD6 	EX 	AF,AF'    		; switch in mask.

ULOOP  	RRCA 				; rotate mask to right.

	JR 	NC,NOCHNG		; skip if no carry.
	
	LD 	HL,PRIPOS		; address print position low.
	INC 	(HL)			; and move to right.

NOCHNG	DEC 	C			; decrement pixel counter.
	JR 	NZ,ULOOP		; back to ULOOP for more.

	EX 	AF,AF'			; save mask.

       	RET				; return.

; ----------------------------
; Routine to validate a keypress 
; against a table of valid keys and 
; loop until a meaningful key is pressed. 
; ----------------------------

KEY    	PUSH 	HL			; save HL throughout.

KEY1   	CALL 	KSCAN			; scan the keyboard.

       	LD 	HL,TABLE		; address keys table.

KLOOP  	CP 	(HL)			; compare key in A against an entry.
       	JR 	Z,FOUND			; forward with a match.

       	INC 	L			; address next table entry.
       	JR 	Z,KEY1 			; end of table so back to read the 
					; keyboard again

       	JR 	KLOOP			; loop back until table read.

; but a match is found so transfer low byte of address to A.

FOUND  	LD 	A,L			; transfer table location to A

       	CPL				; entries were in reverse order so
					; complement to give translated value.

       	POP 	HL			; restore initial value of HL.

L55DA 	RET				; return.

; Note there is a gap of approx 18 unused bytes here.

; ---

; Of the 40 keys on the Spectrum keyboard, only nineteen are used by this 
; program.

ORG $55ED 

TABLE   DEFB 	$25 			; Q
	DEFB 	$0D 			; R
	DEFB 	$21 			; ENTER
	DEFB 	$0E 			; F
	DEFB 	$15 			; E
	DEFB 	$16 			; D
	DEFB 	$0F 			; C
	DEFB 	$00 			; B
	DEFB 	$26 			; A
	DEFB 	$1B 			; 9
	DEFB 	$13 			; 8
	DEFB 	$0B 			; 7
	DEFB 	$03 			; 6
	DEFB 	$04 			; 5
	DEFB 	$0C 			; 4
	DEFB 	$14 			; 3
	DEFB 	$1C 			; 2
	DEFB 	$24 			; 1
L55FF 	DEFB 	$23 			; 0

; ---

ORG $5600 

; The character set consists of characters 39d(') to 122d(z)
; Characters outside this range are printed blank.
; Some characters within this range have been intentionally left blank as they 
; are not required by the disassembler and are unlikely to occur in text 
; messages.
; Characters are stored as vertical slices so the letter A is

; 01111110 = 126
; 00001001 = 9
; 00001001 = 9
; 00001001 = 9
; 01111110 = 126

;CSET
	DEFB 	0,4,2,1,0        		; '
	DEFB 	0,28,34,65,0     		; (
	DEFB 	0,65,34,28,0     		; )

	DEFB 	0,0,0,0,0        		; *

	DEFB 	8,8,62,8,8       		; +
	DEFB 	0,80,48,0,0      		; ,
	DEFB 	8,8,8,8,8        		; -
	DEFB 	0,0,96,96,0      		; =

	DEFB 	0,0,0,0,0        		; /

	DEFB 	62,81,73,69,62   		; 0
	DEFB 	0,66,127,64,0   		; 1
	DEFB 	66,97,81,73,70   		; 2
	DEFB 	33,65,69,75,49   		; 3
	DEFB 	24,20,18,127,16  		; 4
	DEFB 	39,69,69,69,57   		; 5
	DEFB 	60,74,73,73,48   		; 6
	DEFB 	1,1,121,5,3      		; 7
	DEFB 	54,73,73,73,54   		; 8
	DEFB 	6,73,73,41,30    		; 9
	DEFB 	0,0,36,0,0       		; :
	DEFB 	0,64,50,0,0      		; ; 

	DEFB 	0,0,0,0,0        		; <
	DEFB 	0,0,0,0,0        		; =
	DEFB 	0,0,0,0,0        		; >

	DEFB 	2,1,81,9,6       		; ?

	DEFB 	0,0,0,0,0        		; @

	DEFB 	126,9,9,9,126    		; A
	DEFB 	127,73,73,73,54  		; B
	DEFB 	62,65,65,65,34   		; C
	DEFB 	127,65,65,34,28  		; D
	DEFB 	127,73,73,73,65  		; E
	DEFB 	127,9,9,9,1      		; F
	DEFB 	62,65,73,73,122  		; G
	DEFB 	127,8,8,8,127    		; H
	DEFB 	0,65,127,65,0   		; I
	DEFB 	32,64,65,63,1    		; J
	DEFB 	127,12,18,33,64  		; K
	DEFB 	127,64,64,64,64  		; L
	DEFB 	127,2,12,2,127   		; M
	DEFB 	127,4,8,16,127   		; N
	DEFB 	62,65,65,65,62   		; O
	DEFB 	127,9,9,9,6      		; P
	DEFB 	62,65,113,193,62 		; Q
	DEFB 	127,9,25,41,70   		; R
	DEFB 	38,73,73,73,50   		; S
	DEFB 	1,1,127,1,1      		; T
	DEFB 	63,64,64,64,63   		; U
	DEFB 	7,24,96,24,7     		; V
	DEFB 	31,96,28,96,31   		; W
	DEFB 	99,20,8,20,99    		; X
	DEFB 	3,4,120,4,3      		; Y
	DEFB 	97,81,73,69,67   		; Z

	DEFB 	0,0,0,0,0			; [
	DEFB 	0,0,0,0,0			; /
	DEFB 	0,0,0,0,0			; ]
	DEFB 	0,0,0,0,0			; ^
	DEFB 	0,0,0,0,0			; _
	DEFB 	0,0,0,0,0			; uk currency symbol

	DEFB 	32,84,84,84,120   		; a
	DEFB 	126,72,72,72,48   		; b
	DEFB 	56,68,68,68,0     		; c
	DEFB 	48,72,72,72,126   		; d
	DEFB 	56,84,84,84,72    		; e
	DEFB 	0,124,10,2,0      		; f
	DEFB 	24,164,164,164,124		; g
	DEFB 	126,8,8,8,112     		; h
	DEFB 	0,72,122,64,0     		; i
	DEFB 	64,128,128,122,0  		; j
	DEFB 	126,24,36,64,0    		; k
	DEFB 	0,62,64,64,0      		; l
	DEFB 	124,4,120,4,120   		; m
	DEFB 	124,4,4,4,120     		; n
	DEFB 	56,68,68,68,56    		; o
	DEFB 	252,36,36,36,24   		; p
	DEFB 	24,36,36,252,128  		; q
	DEFB 	120,4,4,4,0       		; r
	DEFB 	72,84,84,84,32    		; s
	DEFB 	4,62,68,64,0      		; t
	DEFB 	60,64,64,64,60    		; u
	DEFB 	12,48,64,48,12    		; v
	DEFB 	60,64,56,64,60    		; w
	DEFB 	68,40,16,40,68    		; x
	DEFB 	28,160,160,160,124		; y
	DEFB 	68,100,84,76,68   		; z

; End of font.

;=====================
;
; This routine first prints the message ROMx then continues into the
; big print routine.
;
;=====================

ROMTXT	LD 	DE,$50FC 		; address ROMx
      	CALL 	CLINE			; clear line 15.

RLOOP  	LD 	A,(DE)    		; fetch a character.
     	CALL 	CHROP   		; print it on line 15.
     	INC 	E        		; point to next character 
     	JR 	NZ,RLOOP    		; and loop until 4 characters printed.
					; continue into big print routine.

; Routine to scan text at start of line 15 
; producing big text in lower third of screen 
; by updating colour attributes.

BIGPR 	LD 	HL,$5A20		; attribute address for line 17 decimal
       	LD 	D,$48			; display file address of line 15 top.

       	LD 	BC,$0001		; colour in B starts as black ink on
					; black paper (0).
					; C is used as an eight counter.

BIGPR2 	LD 	E,$E0			; low byte of address in display file.

BIGPR3 	LD 	A,(DE)			; fetch a display file byte.

BIGPR4 	RLCA				; rotate bits to carry

       	LD 	(HL),63 		; load attributes with white/white.

       	JR 	NC,BIGPR5		; if no carry leave as it is.

       	LD 	(HL),B  		; else overwrite attribute byte with 
					; a colour.

BIGPR5 	INC 	L			; point to next attribute byte 
       	RLC 	C      			; rotate the eight counter.
       	JR 	NC,BIGPR4		; loop back for all eight bits

       	INC 	E			; bump the screen address
       	BIT 	2,E			; check that bytes don't exceed 4
       	JR 	Z,BIGPR3		; loop back for bytes $E0-$E3.

       	LD 	A,9			; now manipulate the colour attribute
       	ADD 	A,B			; to give a rainbow gradation.
       	AND 	$1F 			; but pure colours are hard to see as
       	LD 	B,A			; they get lighter so this compromise
					; was arrived at by accident.

       	INC 	D			; move vertically down display file.	
       	BIT 	3,D  			; check high byte to ensure still
       	JR 	NZ,BIGPR2 		; within middle third and continue.

       	RET				; return when all 7 pixel lines have 
					; been enlarged.

;=====================
;
; The keyboard scanning routine is similar to
; that in the Spectrum ROM at address $028E
;
; For each of the 40 keys  a number in the range
; 0-39 ($00-$27)  is returned.
;
;=====================

KSCAN  	LD 	DE,$FF2F		; initialize D to receive key.
					; E is starting key value + 8
					; $27 is 39 decimal.

       	LD 	BC,$FEFE		; commencing port address
					; B is also an 8 counter.

KLINE  	IN 	A,(C)			; read a keyboard half row. 
       	CPL				; pressed keys now equate to a set bit.
       	AND 	$1F			; isolate lower meaningful 5 bits.
       	JR 	Z,KDONE			; forward if no keys pressed in half-
					; row.

       	INC 	D			; test D - result should be zero.

       	JR 	NZ,KSCAN                ; two keys are unacceptable so start
                                        ; from the beginning again.

       	LD 	H,A			; transfer bit to H
       	LD 	A,E			; key value to A.

KBITS  	SUB 	8			; subtract eight from value
       	SRL 	H			; shift bit to carry 
       	JR 	NC,KBITS		; loop until carry is set

       	JR 	NZ,KSCAN		; if two keys pressed in the same 
					; row then start again.

       	LD 	D,A			; otherwise pass key value to D
					; and continue to check that no other
					; key is pressed in other rows.

KDONE  	DEC 	E			; decrease starting key value for 
					; a new row. 
       	RLC 	B 			; form next port address.
       	JR 	C,KLINE 		; repeat for all 8 rows while a carry
					; is set.

       	LD 	A,D			; transfer key value to A
       	INC 	D			; test for a valid key in D/A
       	JR 	Z,KSCAN			; repeat from beginning if was $FF.

L57FE 	RET				; return with key value $00 - $27 in A.

; ---      

ORG $57FF

	DEFB 	56   			; white/white 63 but it helps to use 
					; black/white 56 while testing.


; Note the above attribute
; which immediately
; precedes the attr.file
; is used to flood the
; screen with white/white before
; the return to BASIC.


; Normally this file builds a 2K object file 
; e.g. tasm -80 -b u3.asm
; This can be loaded into the Z80 emulator using the extra functions
; Load a Block of memory/screen 
; Set start to #4000, length to #0800 and name to u3.obj or whatever.
; execute with PRINT USR 16384.

; Since not all emulators can 
; load an arbitrary block of code, by removing the semicolon from 
; the start of the next two lines and building with 
; tasm -80 -b -f38 u3.asm
; then a binary file of 6912 bytes will be produced which can be 
; renamed to u3.scr which loads into most emulators.
; This will have black and white stripes in the lower two thirds of
; the display which may be cleared from basic. To highlight the ascii
; column in cyan, say, use PRINT AT 15,28; PAPER 5; "    " .
;
; This file is difficult to work on, but I have now removed the self-modifying
; code that was present in the original version.

; .org $5aff+$1000
; .byte $38

.END 					; cross-assembler directive
                         
