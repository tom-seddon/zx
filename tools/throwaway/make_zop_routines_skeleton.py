#!/usr/bin/python
import collections

reg_b="b"
reg_c="c"
reg_d="d"
reg_e="e"
reg_h="h"
reg_l="l"
reg_a="a"
reg_ixh="ixh"
reg_ixl="ixl"
reg_iyh="iyh"
reg_iyl="iyl"

regs_8bit={
    None:[reg_b,  reg_c,  reg_d,  reg_e,  reg_h,  reg_l,  None,   reg_a],
    0xdd:[None,   None,   None,   None,   reg_ixh,reg_ixl,None,   reg_a],
    0xfd:[None,   None,   None,   None,   reg_iyh,reg_iyl,None,   reg_a]
}

class Reg16:
    def __init__(self,h,l,full=None):
        self.h=h
        self.l=l
        self.full=h+l if full is None else full

reg_af=Reg16("a","f")
reg_bc=Reg16("b","c")
reg_de=Reg16("d","e")
reg_hl=Reg16("h","l")
reg_sp=Reg16("sph","spl","sp")
reg_ix=Reg16("ixh","ixl","ix")
reg_iy=Reg16("iyh","iyl","iy")

regs_16bit={
    None:[reg_bc,reg_de,reg_hl,reg_sp],
    0xdd:[None,  None,  reg_ix,None  ],
    0xfd:[None,  None,  reg_iy,None  ],
}
            
stackable_regs_16bit={
    None:[reg_bc,reg_de,reg_hl,reg_af],
    0xdd:[None,  None,  reg_ix,None  ],
    0xfd:[None,  None,  reg_iy,None  ],
}

class Instr:
    def __init__(self,dis,lines,nt):
        self.dis=dis
        self.lines=lines[:]
        self.nt=nt[:]

def ld_r8_r8(d,s):
    if d is None or s is None: return None

    lines=[]
    if d!=s: lines+=["lda zr%s:sta zr%s"%(s,d)]
    
    return Instr("ld %s,%s"%(d,s),
                 lines,
                 [4])

def ld_r8_imm(d):
    if d is None: return None
    return Instr("ld %s,n"%d,
                 ["jsr zfetch:sta zr%s"%d],
                 [4,3])

def ld_r8_ind(d,ir):
    if d is None: return None
    return Instr("ld %s,(%s)"%(d,ir.full),
                 ["ldx zr%s:ldy zr%s:LOAD_XY"%(ir.l,ir.h),
                  "sta zr%s"%d],
                 [4,3])

def ld_ind_r8(ir,s):
    if s is None: return None
    return Instr("ld (%s),%s"%(ir.full,s),
                 ["ldx zr%s:ldy zr%s:lda zr%s:STORE_XY"%(ir.l,ir.h,s)],
                 [4,3])

def ld_r8_mem(d):
    return Instr("ld %s,(nn)"%d,
                 ["jsr zfetcha:LOAD_XY",
                  "sta zr%s"%d],
                 [4,3,3,3])

def ld_mem_r8(s):
    return Instr("ld (nn),%s"%s,
                 ["jsr zfetcha:lda zr%s:STORE_XY"%s],
                 [4,3,3,3])

def ld_ind_imm8(r):
    return Instr("ld (%s),n"%(r.full),
                 ["jsr zfetch:ldx zr%s:ldy zr%s:STORE_XY"%(r.l,r.h)],
                 [4,3,3])

def ld_r16_imm(r):
    return Instr("ld %s,nn"%(r.full),
                 ["jsr zfetch2",
                  "sta zr%s:lda zfetch2_lsb:sta zr%s"%(r.h,r.l)],
                 [4,3,3])

def ld_r16_mem(r):
    return Instr("ld %s,(nn)"%(r.full),
                 ["jsr zfetcha",
                  "LOAD_XY_POSTINC:sta zr%s"%r.l,
                  "LOAD_XY_POSTINC:sta zr%s"%r.h],
                 [4,3,3,3,3])

def ld_mem_r16(r):
    return Instr("ld (nn),%s"%(r.full),
                 ["jsr zfetcha",
                  "lda zr%s:STORE_XY_POSTINC"%r.l,
                  "lda zr%s:STORE_XY"%r.h],
                 [4,3,3,3,3])

def ld_r16_r16(d,s):
    lines=[]
    if d!=s: lines+=["lda zr%s:sta zr%s"%(s.l,d.l),
                     "lda zr%s:sta zr%s"%(s.h,d.h)]
    
    return Instr("ld %s,%s"%(d.full,s.full),
                 lines,
                 [6])

def push(r):
    lines=[]
    if r is reg_af: lines=["jsr zpack_flags"]
    lines+=["ldx zrspl:ldy zrsph",
            "lda zr%s:STORE_XY_PREDEC"%r.h,
            "lda zr%s:STORE_XY_PREDEC"%r.l,
            "stx zrspl:sty zrsph"]
    
    return Instr("push %s"%(r.full),
                 lines,
                 [5,3,3])

def pop(r):
    lines=["ldx zrspl:ldy zrsph",
           "LOAD_XY_POSTINC:sta zr%s"%r.l,
           "LOAD_XY_POSTINC:sta zr%s"%r.h,
           "stx zrspl:sty zrsph"]
    if r is reg_af: lines+=["jsr zunpack_flags"]
    
    return Instr("pop %s"%(r.full),
                 lines,
                 [4,3,3])

def ex8_lines(a,b): return ["ldx zr%s:lda zr%s:sta zr%s:stx zr%s"%(a,b,a,b)]
def ex_lines(a,b): return ex8_lines(a.l,b.l)+ex8_lines(a.h,b.h)
def ex_alt_lines(r): return ex8_lines(r.l,r.l+"2")+ex8_lines(r.h,r.h+"2")
        
def ex_de_hl():
    return Instr("ex de,hl",
                 ex_lines(reg_de,reg_hl),
                 [4])


def ex_af_af():
    return Instr("ex af,af'",
                 ["jsr zpack_flags"]+
                 ex_alt_lines(reg_af)+
                 ["jsr zunpack_flags"],
                 [4])

def exx():
    return Instr("exx",
                 ex_alt_lines(reg_bc)+ex_alt_lines(reg_de)+ex_alt_lines(reg_hl),
                 [4])

def ins(x):
    global instr,i
    
    if x is not None:
        assert instr is None,(oct(i),hex(i),instr.dis,x.dis)
        instr=x

def family_imm(mnem):
    return Instr("%s a,n"%mnem,
                 ["jsr zfetch:jmp z%s"%mnem],
                 [4])

def family_r8(mnem,r):
    if r is None: return None
    return Instr("%s a,%s"%(mnem,r),
                 ["lda zr%s:jmp z%s"%(r,mnem)],
                 [4])

def family_ind(mnem,r):
    return Instr("%s a,(%s)"%(mnem,r.full),
                 ["ldx zr%s:ldy zr%s:jsr zfetch:jmp z%s"%(r.l,r.l,mnem)],
                 [4,3])

def inc_r8(r):
    return Instr("inc %s"%r,
                 ["lda zr%s:tax:inc a:sta zr%s"%(r,r),
                  "sta zfsval",
                  "sta zf53val",
                  "cmp #$80:beq nv:dec a:sta zfpval",
                  "txa:eor #1:eor zr%s:sta zfhval"%r],
                 [4])
                  

def family(prefix,opcode,d1_val,mnem):
    d0=(opcode>>6)&3
    d1=(opcode>>3)&7
    d2=(opcode>>0)&7

    if d0==3 and d1==d1_val and d2==6: ins(family_imm(mnem))
    if d0==2 and d1==d1_val: ins(family_r8(mnem,regs_8bit[prefix][d2]))
    if d0==2 and d1==d1_val and d2==6: ins(family_ind(mnem,regs_16bit[prefix][2]))

##########################################################################
##########################################################################

op_labels={}

for prefix in [None]:#,0xdd,0xfd]:
    op_labels[prefix]=256*[None]
    for i in range(256):
        b=""
        for j in range(8): b+="1" if i&(1<<(7-j)) else "0"

        print ";;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;"
        print ";;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;"
        print

        op_label="zop"
        if prefix is not None: op_label+="%02X"%prefix
        op_label+="%02X"%i
        
        #   7   6   5   4   3   2   1   0
        # +---+---+---+---+---+---+---+---+
        # |  d0   |    d1     |     d2    |
        # +---+---+---+---+---+---+---+---+

        d0=(i>>6)&3
        d1=(i>>3)&7
        d2=(i>>0)&7

        instr=None

        if d0==1: ins(ld_r8_r8(regs_8bit[prefix][d2],regs_8bit[prefix][d1]))
        if d0==0 and d2==6: ins(ld_r8_imm(regs_8bit[prefix][d1]))
        if d0==1 and d2==6: ins(ld_r8_ind(regs_8bit[prefix][d1],regs_16bit[prefix][2]))
        if d0==1 and d1==6: ins(ld_ind_r8(regs_16bit[prefix][2],regs_8bit[prefix][d2]))
        if i==0x36: ins(ld_ind_imm8(regs_16bit[prefix][2]))
        if i==0x0a: ins(ld_r8_ind(reg_a,reg_bc))
        if i==0x1a: ins(ld_r8_ind(reg_a,reg_de))
        if i==0x3a: ins(ld_r8_mem(reg_a))
        if i==0x02: ins(ld_ind_r8(reg_bc,reg_a))
        if i==0x12: ins(ld_ind_r8(reg_de,reg_a))
        if i==0x32: ins(ld_mem_r8(reg_a))
        if d0==0 and d2==1 and (d1&1)==0: ins(ld_r16_imm(regs_16bit[prefix][d1>>1]))
        if i==0x2a: ins(ld_r16_mem(regs_16bit[prefix][2]))
        if i==0x22: ins(ld_mem_r16(regs_16bit[prefix][2]))
        if i==0xf9: ins(ld_r16_r16(reg_sp,regs_16bit[prefix][2]))
        if d0==3 and d2==5 and (d1&1)==0: ins(push(stackable_regs_16bit[prefix][d1>>1]))
        if d0==3 and d2==1 and (d1&1)==0: ins(pop(stackable_regs_16bit[prefix][d1>>1]))
        if i==0xeb: ins(ex_de_hl())
        if i==0x08: ins(ex_af_af())
        if i==0xd9: ins(exx())

        family(prefix,i,0,"add")
        family(prefix,i,1,"adc")
        family(prefix,i,2,"sub")
        family(prefix,i,3,"sbc")
        family(prefix,i,4,"and")
        family(prefix,i,5,"or")
        family(prefix,i,6,"xor")
        family(prefix,i,7,"cp")

        # if d0==0 and d2==4: ins(inc(regs_8bit[d1]))

        if instr is not None:
            op_labels[prefix][i]=op_label
            print ".%s"%op_label
            print "{"
            print "; %s"%instr.dis
            for line in instr.lines: print line
            print "ZNEXT %d"%sum(instr.nt)
            print "}"
        
##########################################################################
##########################################################################

def do_table(labels,prefix,b7):
    label="zop_table_"
    if prefix is not None: label+="%X_"%prefix
    label+="%dxxxxxxx"%b7

    print ".%s"%label
    for i in range(128):
        opcode=i
        if b7: opcode|=128

        if labels[opcode] is not None: print "equw %s"%labels[opcode]
        else: print "equw zbad"

for prefix in [None]:#,0xcc,0xdd]:
    do_table(op_labels[prefix],prefix,0)
    do_table(op_labels[prefix],prefix,1)
