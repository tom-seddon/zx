#!/usr/bin/python
import collections

Reg16=collections.namedtuple("Reg16","h l")

reg_b="b"
reg_c="c"
reg_d="d"
reg_e="e"
reg_h="h"
reg_l="l"
reg_a="a"

regs_8bit=[reg_b,reg_c,reg_d,reg_e,reg_h,reg_l,None,reg_a]

reg_af=Reg16("a","f")
reg_bc=Reg16("b","c")
reg_de=Reg16("d","e")
reg_hl=Reg16("h","l")
reg_sp=Reg16("sph","spl")
            
regs_16bit=[reg_bc,reg_de,reg_hl,reg_sp]
stackable_regs_16bit=[reg_bc,reg_de,reg_hl,reg_af]

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
    return Instr("ld %s,(%s%s)"%(d,ir.h,ir.l),
                 ["ldx zr%s:ldy zr%s:LOAD_XY"%(ir.l,ir.h),
                  "sta zr%s"%d],
                 [4,3])

def ld_ind_r8(ir,s):
    if s is None: return None
    return Instr("ld (%s%s),%s"%(ir.h,ir.l,s),
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
    return Instr("ld (%s%s),n"%(r.h,r.l),
                 ["jsr zfetch:ldx zr%s:ldy zr%s:STORE_XY"%(r.l,r.h)],
                 [4,3,3])

def ld_r16_imm(r):
    return Instr("ld %s%s,nn"%(r.h,r.l),
                 ["jsr zfetch2",
                  "sta zr%s:lda zfetch2_lsb:sta zr%s"%(r.h,r.l)],
                 [4,3,3])

def ld_r16_mem(r):
    return Instr("ld %s%s,(nn)"%(r.h,r.l),
                 ["jsr zfetcha",
                  "LOAD_XY_POSTINC:sta zr%s"%r.l,
                  "LOAD_XY_POSTINC:sta zr%s"%r.h],
                 [4,3,3,3,3])

def ld_mem_r16(r):
    return Instr("ld (nn),%s%s"%(r.h,r.l),
                 ["jsr zfetcha",
                  "lda zr%s:STORE_XY_POSTINC"%r.l,
                  "lda zr%s:STORE_XY"%r.h],
                 [4,3,3,3,3])

def ld_r16_r16(d,s):
    lines=[]
    if d!=s: lines+=["lda zr%s:sta zr%s"%(s.l,d.l),
                     "lda zr%s:sta zr%s"%(s.h,d.h)]
    
    return Instr("ld %s%s,%s%s"%(d.h,d.l,s.h,s.l),
                 lines,
                 [6])

def push(r):
    return Instr("push %s%s"%(r.h,r.l),
                 ["ldx zrspl:ldy zrsph",
                  "lda zr%s:STORE_XY_PREDEC"%r.h,
                  "lda zr%s:STORE_XY_PREDEC"%r.l,
                  "stx zrspl:sty zrsph"],
                 [5,3,3])

def pop(r):
    return Instr("pop %s%s"%(r.h,r.l),
                 ["ldx zrspl:ldy zrsph",
                  "LOAD_XY_POSTINC:sta zr%s"%r.l,
                  "LOAD_XY_POSTINC:sta zr%s"%r.h,
                  "stx zrspl:sty zrsph"],
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
                 ex_alt_lines(reg_af),
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

for i in range(256):
    b=""
    for j in range(8): b+="1" if i&(1<<(7-j)) else "0"

    print ";;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;"
    print ";;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;"
    print
    print ".zop%02X ; %s %s %s"%(i,b[0:2],b[2:5],b[5:8])
    print "{"

    #   7   6   5   4   3   2   1   0
    # +---+---+---+---+---+---+---+---+
    # |  d0   |    d1     |     d2    |
    # +---+---+---+---+---+---+---+---+

    d0=(i>>6)&3
    d1=(i>>3)&7
    d2=(i>>0)&7

    instr=None
    
    if d0==1: ins(ld_r8_r8(regs_8bit[d2],regs_8bit[d1]))
    if d0==0 and d2==6: ins(ld_r8_imm(regs_8bit[d1]))
    if d0==1 and d2==6: ins(ld_r8_ind(regs_8bit[d1],reg_hl))
    if d0==1 and d1==6: ins(ld_ind_r8(reg_hl,regs_8bit[d2]))
    if i==0x36: ins(ld_ind_imm8(reg_hl))
    if i==0x0a: ins(ld_r8_ind(reg_a,reg_bc))
    if i==0x1a: ins(ld_r8_ind(reg_a,reg_de))
    if i==0x3a: ins(ld_r8_mem(reg_a))
    if i==0x02: ins(ld_ind_r8(reg_bc,reg_a))
    if i==0x12: ins(ld_ind_r8(reg_de,reg_a))
    if i==0x32: ins(ld_mem_r8(reg_a))
    if d0==0 and d2==1 and (d1&1)==0: ins(ld_r16_imm(regs_16bit[d1>>1]))
    if i==0x2a: ins(ld_r16_mem(reg_hl))
    if i==0x22: ins(ld_mem_r16(reg_hl))
    if i==0xf9: ins(ld_r16_r16(reg_sp,reg_hl))
    if d0==3 and d2==5 and (d1&1)==0: ins(push(stackable_regs_16bit[d1>>1]))
    if d0==3 and d2==1 and (d1&1)==0: ins(pop(stackable_regs_16bit[d1>>1]))
    if i==0xeb: ins(ex_de_hl())
    if i==0x08: ins(ex_af_af())
    if i==0xd9: ins(exx())

    if instr is None:
        print "ZBAD"
    else:
        print "; %s"%instr.dis
        for line in instr.lines: print line
        print "ZNEXT %d"%sum(instr.nt)
        
    print "}"
    print
    
    
