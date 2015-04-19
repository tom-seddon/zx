#!/usr/bin/python
import collections,itertools,sys

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
    0xdd:[reg_b,  reg_c,  reg_d,  reg_e,  reg_ixh,reg_ixl,None,   reg_a],
    0xfd:[reg_b,  reg_c,  reg_d,  reg_e,  reg_iyh,reg_iyl,None,   reg_a],
}

class Reg16:
    def __init__(self,h,l,full=None,indfull=None):
        self.h=h
        self.l=l
        self.full=h+l if full is None else full
        self.indfull=self.full if indfull is None else indfull

reg_af=Reg16("a","f")
reg_bc=Reg16("b","c")
reg_de=Reg16("d","e")
reg_hl=Reg16("h","l")
reg_sp=Reg16("sph","spl","sp")
reg_ix=Reg16("ixh","ixl","ix","ix+d")
reg_iy=Reg16("iyh","iyl","iy","iy+d")

regs_16bit={
    None:[reg_bc,reg_de,reg_hl,reg_sp],
    0xdd:[reg_bc,reg_de,reg_ix,reg_sp],
    0xfd:[reg_bc,reg_de,reg_iy,reg_sp],
}
            
stackable_regs_16bit={
    None:[reg_bc,reg_de,reg_hl,reg_af],
    0xdd:[reg_bc,reg_de,reg_ix,reg_af],
    0xfd:[reg_bc,reg_de,reg_iy,reg_af],
}

class Instr:
    def __init__(self,dis,lines,nt):
        self.dis=dis
        self.lines=lines[:]
        self.nt=nt[:]
        self.label=None

class ManualInstr:
    def __init__(self,label,dis):
        self.label=label
        self.dis=dis

##########################################################################
##########################################################################

# On entry to instruction-specific code: byte in A.
def x_read_ind(r,lines):
    if r is reg_ix or r is reg_iy:
        return (["jsr zfetch:clc:adc zr%s:tax"%r.l,
                "ldy zr%s:{bcc nc:iny:.nc}"%r.h,
                "LOAD_XY"]+
                lines)
    else:
        return ["ldx zr%s:ldy zr%s:LOAD_XY"%(r.l,r.h)]

def x_write_ind_imm(r):
    if r is reg_ix or r is reg_iy:
        return (["jsr zfetch:clc:adc zr%s:sta zindex__tmp+0"%r.l,
                 "ldy zr%s:{bcc nc:iny:.nc}:sty zindex__tmp+1"%r.h,
                 "jsr zfetch",
                 "ldx zindex__tmp+0:ldy zindex__tmp+1:STORE_XY"])
    else:
        return ["jsr zfetch",
                "ldx zr%s:ldy zr%s:STORE_XY"%(r.l,r.h)]
    
# On entry to instruction-specific code: address in YX, that must be
# preserved. (Use of zindex__tmp+0 and zindex__tmp+1 is fine.) Put
# byte to write in A.
def x_write_ind(r,lines):
    if r is reg_ix or r is reg_iy:
        return (["jsr zfetch:clc:adc zr%s:tax"%r.l,
                 "ldy zr%s:{bcc nc:iny:.nc}"%r.h]+
                lines+
                ["STORE_XY"])
    else:
        # This could be done more cunningly...
        return (["ldx zr%s:ldy zr%s"%(r.l,r.h)]+
                lines+
                ["STORE_XY"])
    
# On entry to instruction-specific code: bte in A, and address in YX,
# that must be preserved. (Use of zindex__tmp+0 and zindex__tmp+1 is
# fine.) Put byte to write in A.
def x_rmw_ind(r,lines):
    if r is reg_ix or r is reg_iy:
        return (["jsr zfetch:clc:adc zr%s:tax"%r.l,
                 "ldy zr%s:bcc nc:iny:.nc"%r.h,
                 "LOAD_XY"]+
                lines+
                ["STORE_XY"])
    else:
        return (["ldx zr%s:ldy zr%s:LOAD_XY"%(r.l,r.h)]+
                lines+
                ["STORE_XY"])

def fixup_ir_r(ir,r):
    if ir is reg_ix or ir is reg_iy:
        if r is reg_iyl or r is reg_ixl: r=reg_l
        elif r is reg_iyh or r is reg_ixh: r=reg_h

    return ir,r
    
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
    if d is None or ir is None: return None
    ir,d=fixup_ir_r(ir,d)
    return Instr("ld %s,(%s)"%(d,ir.indfull),
                 x_read_ind(ir,["sta zr%s"%d]),
                 [4,3])

def ld_ind_r8(ir,s):
    if s is None: return None
    if ir is None: return None
    ir,s=fixup_ir_r(ir,s)
    return Instr("ld (%s),%s"%(ir.indfull,s),
                 x_write_ind(ir,["lda zr%s"%s]),
                 [4,3])

def ld_r8_mem(d):
    if d is None: return None
    return Instr("ld %s,(nn)"%d,
                 ["jsr zfetcha:LOAD_XY",
                  "sta zr%s"%d],
                 [4,3,3,3])

def ld_mem_r8(s):
    if s is None: return None
    return Instr("ld (nn),%s"%s,
                 ["jsr zfetcha:lda zr%s:STORE_XY"%s],
                 [4,3,3,3])

def ld_ind_imm8(r):
    if r is None: return None
    return Instr("ld (%s),n"%(r.indfull),
                 x_write_ind_imm(r),
                 [4,3,3])

def ld_r16_imm(r):
    if r is None: return None
    return Instr("ld %s,nn"%(r.full),
                 ["jsr zfetch2",
                  "sta zr%s:lda zfetch2_lsb:sta zr%s"%(r.h,r.l)],
                 [4,3,3])

def ld_r16_mem(r):
    if r is None: return None
    return Instr("ld %s,(nn)"%(r.full),
                 ["jsr zfetcha",
                  "LOAD_XY_POSTINC:sta zr%s"%r.l,
                  "LOAD_XY_POSTINC:sta zr%s"%r.h],
                 [4,3,3,3,3])

def ld_mem_r16(r):
    if r is None: return None
    return Instr("ld (nn),%s"%(r.full),
                 ["jsr zfetcha",
                  "lda zr%s:STORE_XY_POSTINC"%r.l,
                  "lda zr%s:STORE_XY"%r.h],
                 [4,3,3,3,3])

def ld_r16_r16(d,s):
    if d is None or s is None: return None
    lines=[]
    if d!=s: lines+=["lda zr%s:sta zr%s"%(s.l,d.l),
                     "lda zr%s:sta zr%s"%(s.h,d.h)]
    
    return Instr("ld %s,%s"%(d.full,s.full),
                 lines,
                 [6])

def push(r):
    if r is None: return None
    lines=[]
    if r is reg_af: lines=["jsr zpack_flags"]
    lines+=["ldx zrspl:ldy zrsph",
            "lda zr%s:STORE_XY_PREDEC"%r.h,
            "lda zr%s:STORE_XY_PREDEC"%r.l,
            "stx zrspl:sty zrsph"]
    
    return Instr("push %s"%(r.full),
                 lines,
                 [5,3,3])

def pop_r16(r):
    if r is None: return None
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

def ex_sp(r):
    return Instr("ex (sp),%s"%r.full,
                 ["ldx zrspl:ldy zrsph",
                  "LOAD_XY_POSTINC:sta zop__tmp", # low
                  "LOAD_XY:pha",                  # high
                  "lda zr%s:STORE_XY"%r.h,        # high
                  "pla:sta zr%s"%r.h,             # high
                  "lda zr%s:STORE_XY_PREDEC"%r.l, # low
                  "lda zop__tmp:sta zr%s"%r.l,    # low
                 ],
                 [4,3,4,3,5])

def exx():
    return Instr("exx",
                 ex_alt_lines(reg_bc)+ex_alt_lines(reg_de)+ex_alt_lines(reg_hl),
                 [4])

def alu_imm(mnem):
    return Instr("%s a,n"%mnem,
                 ["jsr zfetch:jmp z%s"%mnem],
                 [4])

def alu_r8(mnem,r):
    if r is None: return None
    return Instr("%s a,%s"%(mnem,r),
                 ["lda zr%s:jmp z%s"%(r,mnem)],
                 [4])

def alu_ind(mnem,r):
    if r is None: return None
    return Instr("%s a,(%s)"%(mnem,r.indfull),
                 x_read_ind(r,["jmp z%s"%mnem]),
                 [4,3])

def inc_r8(r):
    if r is None: return None
    return Instr("inc %s"%r,
                 ["lda zr%s:DO_ZINC zr%s"%(r,r)],
                 [4])

def inc_ind8(r):
    if r is None: return None
    return Instr("inc (%s)"%r.indfull,
                 x_rmw_ind(r,["sty zindex__tmp+1",
                              "DO_ZINC zop__tmp:lda zop__tmp",
                              "ldy zindex__tmp+1"]),
                 [4,4,3])

def dec_r8(r):
    if r is None: return None
    return Instr("dec %s"%r,
                 ["lda zr%s:DO_ZDEC zr%s"%(r,r)],
                 [4])

def dec_ind8(r):
    if r is None: return None
    return Instr("dec (%s)"%r.indfull,
                 x_rmw_ind(r,["sty zindex__tmp+1",
                              "DO_ZDEC zop__tmp:lda zop__tmp",
                              "ldy zindex__tmp+1"]),
                 [4,4,3])

def inc_r16(r):
    if r is None: return None
    return Instr("inc %s"%r.full,
                 ["inc zr%s:bne nc:inc zr%s:.nc"%(r.l,r.h)],
                 [6])

def dec_r16(r):
    if r is None: return None
    return Instr("dec %s"%r.full,
                 ["lda zr%s:beq nc:dec zr%s:.nc:dec zr%s"%(r.l,r.h,r.l)],
                 [6])

def add_r16_r16(d,s):
    if d is None or s is None: return None
    return Instr("add %s,%s"%(d.full,s.full),
                 ["DO_ZADD16_OR_ADC16 zr%s,zr%s,zr%s,zr%s,1"%(d.l,d.h,s.l,s.h)],
                 [4,4,3])

def adc_r16_16(d,s):
    if d is None or s is None: return None
    return Instr("adc %s,%s"%(d.full,s.full),
                 ["DO_ZADD16_OR_ADC16 zr%s,zr%s,zr%s,zr%s,1"%(d.l,d.h,s.l,s.h)],
                 [4,4,4,3])

def jp():
    return Instr("jp nn",
                 ["jsr zfetch2",
                  "sta zrpch:lda zfetch2_lsb:sta zrpcl"],
                 [4,3,3])

def jpcc(cond):
    return Instr("jp %s,nn"%cond_names[cond],
                 ["jsr zfetch2:tay",
                  conds[cond],
                  "lda zfetch2_lsb:sta zrpcl:sty zrpch",
                  ".no"],
                 [4,3,3])

def ret():
    return Instr("ret",
                 ["ldx zrspl:ldy zrsph",
                  "LOAD_XY_POSTINC:sta zrpcl",
                  "LOAD_XY_POSTINC:sta zrpch",
                 "stx zrspl:sty zrsph"],
                 [4,3,3])

def retcc(cond):
    return Instr("ret %s"%cond_names[cond],
                 [conds[cond],
                  "ldx zrspl:ldy zrsph",
                  "LOAD_XY_POSTINC:sta zrpcl",
                  "LOAD_XY_POSTINC:sta zrpch",
                  "stx zrspl:sty zrsph",
                  "ZTSTATES(3):ZTSTATES(3)",
                  ".no"],
                 [5])

def jp_ind(r):
    if r is None: return None
    return Instr("jp (%s)"%r.full,
                 ["lda zr%s:sta zrpcl:lda zr%s:sta zrpch"%(r.l,r.h)],
                 [4,4])

def callcc(cond):
    return Instr("call %s,nn"%cond_names[cond],
                 ["jsr zfetch2:sta zop__tmp",
                  conds[cond],
                  "ZPUSH_PC",
                  "lda zfetch2_lsb:sta zrpcl",
                  "lda zop__tmp:sta zrpch",
                  "ZTSTATES(4):ZTSTATES(3)",
                  ".no"],
                 [4,3,3])

def call():
    return Instr("call nn",
                 ["jsr zfetch2:sta zop__tmp",
                  "ZPUSH_PC",
                  "lda zfetch2_lsb:sta zrpcl",
                  "lda zop__tmp:sta zrpch"],
                 [4,3,4,3,3])
                  

# def family(prefix,opcode,d1_val,mnem):
#     d0=(opcode>>6)&3
#     d1=(opcode>>3)&7
#     d2=(opcode>>0)&7

#     if d0==3 and d1==d1_val and d2==6: ins(family_imm(mnem))
#     if d0==2 and d1==d1_val: ins(family_r8(mnem,regs_8bit[prefix][d2]))
#     if d0==2 and d1==d1_val and d2==6: ins(family_ind(mnem,regs_16bit[prefix][2]))

##########################################################################
##########################################################################

alu_mnemonics=["add","adc","sub","sbc","and","xor","or","cp"]

# these code snippests test a flag and branch to a label `no' if the
# condition was NOT met.
#
# A/X changed. Y preserved.
conds=["ldx zfszval:beq no", # NZ
       "ldx zfszval:bne no", # Z
       "bit zfcval:bmi no",  # NC
       "bit zfcval:bpl no",  # C
       "ldx zfpval:lda p_flag_values,X:bne no", # PO
       "ldx zfpval:lda p_flag_values,X:beq no", # PE
       "bit zfszval:bmi no",                    # P
       "bit zfszval:bpl no"]                    # M
cond_names=["nz","z","nc","c","po","pe","p","m"]

# This is the scheme described in http://www.z80.info/decoding.htm.
def get_unprefixed_opcodes(prefix):
    instrs=256*[None]

    for bx,by,bz in itertools.product(range(4),range(8),range(8)):
        bq=by&1
        bp=by>>1

        opcode=(bx<<6)|(by<<3)|(bz<<0)
        instr=None
        if bx==0:
            if bz==0:
                if by==0:
                    # nop
                    pass
                elif by==1:
                    # ex af,af'
                    instr=ex_af_af()
                elif by==2:
                    # djnz d
                    instr=Instr("djnz d",
                                ["jsr zfetch",
                                 "dec zrb:beq nb",
                                 "clc:adc zrpcl:sta zrpcl:bcc nc:inc zrpch:.nc",
                                 "ZTSTATES(5)",
                                 ".nb"],
                                [5,3])
                elif by==3:
                    # jr d
                    instr=Instr("jr d",
                                ["jsr zfetch",
                                 "clc:adc zrpcl:sta zrpcl:bcc nc:inc zrpch:.nc"],
                                [4,3,5])
                elif by>=4:
                    # jr cc[y-4],d
                    instr=Instr("jr %s,d"%(["nz","z","nc","c"][by-4]),
                                ["jsr zfetch",
                                 conds[by-4],
                                 "clc:adc zrpcl:sta zrpcl:bcc nc:inc zrpch:.nc",
                                 "ZTSTATES(5)",
                                 ".no"],
                                [4,3])
            elif bz==1:
                if bq==0: instr=ld_r16_imm(regs_16bit[prefix][bp])
                elif bq==1: instr=add_r16_r16(regs_16bit[prefix][2],regs_16bit[prefix][bp])
            elif bz==2:
                if bq==0 and bp==0: instr=ld_ind_r8(regs_16bit[prefix][0],reg_a)
                elif bq==0 and bp==1: instr=ld_ind_r8(regs_16bit[prefix][1],reg_a)
                elif bq==0 and bp==2: instr=ld_mem_r16(regs_16bit[prefix][2])
                elif bq==0 and bp==3: instr=ld_mem_r8(regs_8bit[prefix][7])
                elif bq==1 and bp==0: instr=ld_r8_ind(reg_a,regs_16bit[prefix][0])
                elif bq==1 and bp==1: instr=ld_r8_ind(reg_a,regs_16bit[prefix][1])
                elif bq==1 and bp==2: instr=ld_r16_mem(regs_16bit[prefix][2])
                elif bq==1 and bp==3: instr=ld_r8_mem(regs_8bit[prefix][7])
            elif bz==3:
                if bq==0: instr=inc_r16(regs_16bit[prefix][bp])
                elif bq==1: instr=dec_r16(regs_16bit[prefix][bp])
            elif bz==4:
                if by==6: instr=inc_ind8(regs_16bit[prefix][2])
                else: instr=inc_r8(regs_8bit[prefix][by])
            elif bz==5:
                if by==6: instr=dec_ind8(regs_16bit[prefix][2])
                else: instr=dec_r8(regs_8bit[prefix][by])
            elif bz==6:
                instr=ld_r8_imm(regs_8bit[prefix][by])
            elif bz==7:
                if by==0: instr=Instr("rlca",
                                      ["lda zra:cmp #$80:rol a:sta zra",
                                       "ror zfcval",
                                       "stz zfhval",
                                       "stz zfnval"],
                                      [4])
                elif by==1: instr=Instr("rrca",
                                        ["lda zra:lsr a:lda zra:ror a:sta zra",
                                         "ror zfcval",
                                         "stz zfhval",
                                         "stz zfnval"],
                                        [4])
                elif by==2: instr=Instr("rla",
                                        ["asl zfcval:rol zra",
                                         "ror zfcval",
                                         "stz zfhval",
                                         "stz zfnval"],
                                        [4])
                elif by==3: instr=Instr("rra",
                                        ["asl zfcval:ror zra",
                                         "ror zfcval",
                                         "stz zfhval",
                                         "stz zfnval",],
                                        [4])
                elif by==4: instr=ManualInstr("zdaa","daa")
                elif by==5: instr=Instr("cpl",
                                        ["lda zra:eor #$ff:sta zra",
                                         "lda #1:sta zfhval",
                                         "sta zfnval"],
                                        [4])
                elif by==6: instr=Instr("scf",
                                        ["lda #128:sta zfcval",
                                         "stz zfhval",
                                         "stz zfnval"],
                                        [4])
                elif by==7: instr=Instr("ccf",
                                        ["ldx #0",
                                         "lda zfcval:eor #$80:sta zfcval",
                                         "bmi was_reset:ldx #$ff:.was_reset",
                                         "stz zfnval"],
                                        [4])
        elif bx==1:
            if bz==6 and by==6:
                # HALT
                pass
            elif bz==6: instr=ld_r8_ind(regs_8bit[prefix][by],regs_16bit[prefix][2])
            elif by==6: instr=ld_ind_r8(regs_16bit[prefix][2],regs_8bit[prefix][bz])
            else: instr=ld_r8_r8(regs_8bit[prefix][by],regs_8bit[prefix][bz])
        elif bx==2:
            if bz==6: instr=alu_ind(alu_mnemonics[by],regs_16bit[prefix][2])
            else: instr=alu_r8(alu_mnemonics[by],regs_8bit[prefix][bz])
        elif bx==3:
            if bz==0:
                instr=retcc(by)
            elif bz==1:
                if bq==0:
                    instr=pop_r16(stackable_regs_16bit[prefix][bp])
                elif bq==1:
                    if bp==0: instr=ret()
                    elif bp==1: instr=exx()
                    elif bp==2: instr=jp_ind(regs_16bit[prefix][2])
                    elif bp==3: instr=ld_r16_r16(reg_sp,regs_16bit[prefix][2])
            elif bz==2:
                instr=jpcc(by)
            elif bz==3:
                if by==0: instr=jp()
                elif by==1: pass    # CB
                elif by==4: instr=ex_sp(regs_16bit[prefix][2])
                elif by==5: instr=ex_de_hl()
                elif by==6: instr=ManualInstr("zdi","di")
                elif by==7: instr=ManualInstr("zei","ei")
            elif bz==4:
                instr=callcc(by)
            elif bz==5:
                if bq==0: instr=push(regs_16bit[prefix][bp])
                elif bq==1:
                    if bp==0: instr=call()
                    elif bp==1: pass # DD
                    elif bp==2: pass # ED
                    elif bp==3: pass # FD
            elif bz==6:
                instr=alu_imm(alu_mnemonics[by])
            elif bz==7:
                instr=ManualInstr("zrst","rst %02Xh"%(by*8))
            pass

        if instr is not None: instrs[opcode]=instr

    return instrs
        
##########################################################################
##########################################################################

instrs_un=get_unprefixed_opcodes(None)
instrs_dd=get_unprefixed_opcodes(0xdd)
instrs_fd=get_unprefixed_opcodes(0xfd)

opcode_by_dis={}
for i,x in enumerate(instrs_un):
    if x is not None:
        assert x.dis not in opcode_by_dis,(hex(i),hex(opcode_by_dis[x.dis]),x.dis)
        opcode_by_dis[x.dis]=i

# Any DD or FD prefix instruction that's an exact match (going by
# disassembly) for one in the unprefixed table can be removed.
def remove_shared(xs,by_dis):
    for i,x in enumerate(xs):
        if xs[i] is not None:
            if xs[i].dis in by_dis:
                xs[i]=None
    
remove_shared(instrs_dd,opcode_by_dis)
remove_shared(instrs_fd,opcode_by_dis)

def get_max_dis_width(xs): return max([len(x.dis) for x in xs if x is not None])

unw=get_max_dis_width(instrs_un)
ddw=get_max_dis_width(instrs_dd)
fdw=get_max_dis_width(instrs_fd)

for i in range(256):
    line="| %02X %03o"%(i,i)
    line+=" | %-*s"%(unw,"" if instrs_un[i] is None else instrs_un[i].dis)
    line+=" | %-*s"%(ddw,"" if instrs_dd[i] is None else instrs_dd[i].dis)
    line+=" | %-*s"%(fdw,"" if instrs_fd[i] is None else instrs_fd[i].dis)
    line+=" |"
    print>>sys.stderr,line

def generate_routines(instrs,fallback_instrs,prefix):
    for i,instr in enumerate(instrs):
        if instr is None: continue
        if instr.label is not None: continue

        instr.label="zop"
        if prefix is not None: instr.label+="%02X"%prefix
        instr.label+="%02X"%i

        print ";;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;"
        print ";;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;"
        print
        print ".%s ; %s"%(instr.label,instr.dis)
        print "{"
        for line in instr.lines: print line
        print "ZNEXT %d"%sum(instr.nt)
        print "}"
        print

    for b7 in [0,1]:
        print ";;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;"
        print ";;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;"
        print

        label="zop_table_"
        if prefix is not None: label+="%02X_"%prefix
        label+="%dxxxxxxx"%b7

        print ".%s"%label

        for i in range(128):
            opcode=i
            if b7: opcode|=128

            instr=instrs[opcode]
            if instr is None:
                if fallback_instrs is not None:
                    instr=fallback_instrs[opcode]

            if instr is None:
                label="zbad"
                dis="?"
            else:
                label=instr.label
                dis=instr.dis

            line="equw %s ; "%label
            if prefix is not None: line+="%02X "%opcode
            line+=dis

            print line

        print
    
generate_routines(instrs_un,None,None)
generate_routines(instrs_dd,instrs_un,0xdd)
generate_routines(instrs_fd,instrs_un,0xfd)
    
##########################################################################
##########################################################################

# rot_mnemonics=["rlc","rrc","rl","rr","sla","sra","sll","srl"]

# cb_instrs=[]
# for bx,by,bz in itertools.product(range(4),range(8),range(8)):
#     bq=by&1
#     bp=by>>1
    
#     opcode=(bx<<6)|(by<<3)|(bz<<0)
#     instr=None
#     if bx==0:
#         if bz==6: instr=rot_ind( 
#         pass
#     elif bx==1:
#         pass
#     elif bx==2:
#         pass
#     elif bx==3:
#         pass
        
# for y in range(16):
#     line=""
#     for x in range(16):
#         opcode=y*16+x
#         c="*" if opcodes[opcode] is not None else "-"
#         line+=c
#     print>>sys.stderr,line
        
# n=0
# for x in instrs:
#     if x is not None: n+=1
# print>>sys.stderr,"%d/%d"%(n,len(instrs))

