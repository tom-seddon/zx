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
        return (["jsr zget_%s_displaced"%r.full,
                "jsr load_xy"]+
                lines)
    else:
        return ["ldx zr%s:ldy zr%s:jsr load_xy"%(r.l,r.h)]

def x_write_ind_imm(r):
    if r is reg_ix or r is reg_iy:
        return (["jsr zget_%s_displaced"%r.full,
                 "jsr zfetch",  # imm
                 "ldx zindex__tmp+0:ldy zindex__tmp+1:jsr store_xy"])
    else:
        return ["jsr zfetch",   # imm
                "ldx zr%s:ldy zr%s:jsr store_xy"%(r.l,r.h)]
    
# On entry to instruction-specific code: address in YX, that must be
# preserved. (Use of zindex__tmp+0 and zindex__tmp+1 is fine.) Put
# byte to write in A.
#
# (this could be done more optimally... but it makes stuff like ld
# (hl),l simpler if the addresses is loaded first.)
def x_write_ind(r,lines):
    if r is reg_ix or r is reg_iy:
        return (["jsr zget_%s_displaced"%r.full]+
                lines+
                ["jsr store_xy"])
    else:
        return (["ldx zr%s:ldy zr%s"%(r.l,r.h)]+
                lines+
                ["jsr store_xy"])
    
# On entry to instruction-specific code: bte in A, and address in YX,
# that must be preserved. (Use of zindex__tmp+0 and zindex__tmp+1 is
# fine.) Put byte to write in A.
def x_rmw_ind(r,lines):
    if r is reg_ix or r is reg_iy:
        return (["jsr zget_%s_displaced"%r.full,
                 "jsr load_xy"]+
                lines+
                ["jsr store_xy"])
    else:
        return (["ldx zr%s:ldy zr%s:jsr load_xy"%(r.l,r.h)]+
                lines+
                ["jsr store_xy"])

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
                 ["jsr zfetch:sta zr%s"%d], # imm
                 [4,3])

def ld_ind8_imm(ir):
    return Instr("ld (%s),n"%ir.indfull,
                 x_write_ind(ir,["stx zindex__tmp+0:sty zindex__tmp+1",
                                 "jsr zfetch",
                                 "ldx zindex__tmp+0:ldy zindex__tmp+1"]),
                 [4,3,3])

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
                 ["jsr zfetcha:jsr load_xy",
                  "sta zr%s"%d],
                 [4,3,3,3])

def ld_mem_r8(s):
    if s is None: return None
    return Instr("ld (nn),%s"%s,
                 ["jsr zfetcha:lda zr%s:jsr store_xy"%s],
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
                  "jsr load_xy_postinc:sta zr%s"%r.l,
                  "jsr load_xy_postinc:sta zr%s"%r.h],
                 [4,3,3,3,3])

def ld_mem_r16(r):
    if r is None: return None
    return Instr("ld (nn),%s"%(r.full),
                 ["jsr zfetcha",
                  "lda zr%s:jsr store_xy_postinc"%r.l,
                  "lda zr%s:jsr store_xy"%r.h],
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
            "lda zr%s:jsr store_xy_predec"%r.h,
            "lda zr%s:jsr store_xy_predec"%r.l,
            "stx zrspl:sty zrsph"]
    
    return Instr("push %s"%(r.full),
                 lines,
                 [5,3,3])

def pop_r16(r):
    if r is None: return None
    lines=["ldx zrspl:ldy zrsph",
           "jsr load_xy_postinc:sta zr%s"%r.l,
           "jsr load_xy_postinc:sta zr%s"%r.h,
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
                  "jsr load_xy_postinc:sta zop__tmp", # low
                  "jsr load_xy:pha",                  # high
                  "lda zr%s:jsr store_xy"%r.h,        # high
                  "pla:sta zr%s"%r.h,             # high
                  "lda zr%s:jsr store_xy_predec"%r.l, # low
                  "lda zop__tmp:sta zr%s"%r.l,    # low
                 ],
                 [4,3,4,3,5])

def exx():
    return Instr("exx",
                 ex_alt_lines(reg_bc)+ex_alt_lines(reg_de)+ex_alt_lines(reg_hl),
                 [4])

def alu_imm(mnem):
    return Instr("%s a,n"%mnem,
                 ["jsr zfetch:jsr zdo_%s"%mnem], # imm
                 [4])

def alu_r8(mnem,r):
    if r is None: return None
    return Instr("%s a,%s"%(mnem,r),
                 ["lda zr%s:jsr zdo_%s"%(r,mnem)],
                 [4])

def alu_ind(mnem,r):
    if r is None: return None
    return Instr("%s a,(%s)"%(mnem,r.indfull),
                 x_read_ind(r,["jsr zdo_%s"%mnem]),
                 [4,3])

def inc_r8(r):
    if r is None: return None
    return Instr("inc %s"%r,
                 ["lda zr%s:jsr zdo_inc:sta zr%s"%(r,r)],
                 [4])

def inc_ind8(r):
    if r is None: return None
    return Instr("inc (%s)"%r.indfull,
                 x_rmw_ind(r,["stx zindex__tmp+0",
                              "jsr zdo_inc",
                              "ldx zindex__tmp+0"]),
                 [4,4,3])

def dec_r8(r):
    if r is None: return None
    return Instr("dec %s"%r,
                 ["lda zr%s:jsr zdo_dec:sta zr%s"%(r,r)],
                 [4])

def dec_ind8(r):
    if r is None: return None
    return Instr("dec (%s)"%r.indfull,
                 x_rmw_ind(r,["stx zindex__tmp+0",
                              "jsr zdo_dec",
                              "ldy zindex__tmp+0"]),
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
                 ["ldx #zr%s:ldy #zr%s:jsr do_zadd16"%(d.l,s.l)],
                 [4,4,3])

def adc_hl_r16(r):
    return Instr("adc hl,%s"%(r.full),
                 ["ldx #zr%s:jsr do_zadc16_hl"%(r.l)],
                 [4,4,4,3])

def sbc_hl_r16(r):
    return Instr("sbc hl,%s"%(r.full),
                 ["ldx #zr%s:jsr do_zsbc16_hl"%(r.l)],
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

# def ret():
#     return Instr("ret",
#                  ["ldx zrspl:ldy zrsph",
#                   "jsr load_xy_postinc:sta zrpcl",
#                   "jsr load_xy_postinc:sta zrpch",
#                  "stx zrspl:sty zrsph"],
#                  [4,3,3])

def retcc(cond):
    return Instr("ret %s"%cond_names[cond],
                 [conds[cond],
                  "ldx zrspl:ldy zrsph",
                  "jsr load_xy_postinc:sta zrpcl",
                  "jsr load_xy_postinc:sta zrpch",
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
                  "jsr zpush_pc",
                  "lda zfetch2_lsb:sta zrpcl",
                  "lda zop__tmp:sta zrpch",
                  "ZTSTATES(4):ZTSTATES(3)",
                  ".no"],
                 [4,3,3])

def call():
    return Instr("call nn",
                 ["jsr zfetch2:sta zop__tmp",
                  "jsr zpush_pc",
                  "lda zfetch2_lsb:sta zrpcl",
                  "lda zop__tmp:sta zrpch"],
                 [4,3,4,3,3])

def rot_r8(mnem,r):
    if r is None: return None
    return Instr("%s %s"%(mnem,r),
                 ["lda zr%s:jsr zdo_%s:sta zr%s"%(r,mnem,r)],
                 [4,4])

def rot_ind(mnem,ir,dest_reg=None):
    if ir is None: return None
    
    dis="%s (%s)"%(mnem,ir.indfull)
    lines=["jsr zdo_%s"%mnem]
    
    if dest_reg is not None:
        # dd/fd prefix nonsens
        dis="ld %s,%s"%(dest_reg,dis)
        lines+=["sta zr%s"%dest_reg] 
    
    return Instr(dis,
                 x_rmw_ind(ir,lines),
                 [4,4,4,3])

def bit_r8(bitn,r):
    return Instr("bit %d,%s"%(bitn,r),
                 ["lda zr%s:and #$%02X:jsr zdo_bit"%(r,1<<bitn)],
                 [4,4])

def bit_ind(bitn,ir):
    return Instr("bit %d,(%s)"%(bitn,ir.indfull),
                 x_read_ind(ir,["and #$%02X:jsr zdo_bit"%(1<<bitn)]),
                 [4,4,4])

def set_r8(bitn,r):
    return Instr("set %d,%s"%(bitn,r),
                 ["lda zr%s:ora #$%02X:sta zr%s"%(r,1<<bitn,r)],
                 [4,4])

def set_ind(bitn,ir,dest_reg=None):
    dis="set %d,(%s)"%(bitn,ir.indfull)
    lines=["ora #$%02X"%(1<<bitn)]
    if dest_reg is not None:
        # dd/fd prefix nonsense
        dis="ld %s,%s"%(dest_reg,dis)
        lines+=["sta zr%s"%dest_reg] 
    
    return Instr(dis,
                 x_rmw_ind(ir,lines),
                 [4,4,4,3])

def res_r8(bitn,r):
    return Instr("res %d,%s"%(bitn,r),
                 ["lda zr%s:and #$%02X:sta zr%s"%(r,(~(1<<bitn))&255,r)],
                 [4,4])

def res_ind(bitn,ir,dest_reg=None):
    dis="res %d,(%s)"%(bitn,ir.indfull)
    lines=["and #$%02X"%((~(1<<bitn))&255)]
    if dest_reg is not None:
        # dd/fd prefix nonsense
        dis="ld %s,%s"%(dest_reg,dis)
        lines+=["sta zr%s"%dest_reg] 
    
    return Instr(dis,
                 x_rmw_ind(ir,lines),
                 [4,4,4,3])

def out_c_r(r):
    return Instr("out (C),%s"%(r if r is not None else "0"),
                 ["lda %s"%("zr%s"%r if r is not None else "#0"),
                  "ldx zrc:ldy zrb:jsr zdo_out"],
                 [4,4,4])

def in_r_c(r):
    lines=["ldx zrc:ldy zrb:jsr zdo_in"]
    if r is not None: lines+=["sta zr%s"%r]
    
    return Instr("in %s(C)"%("%s "%r if r is not None else ""),
                 lines,
                 [4,4,4])

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

nop=Instr("nop",
          [],
          [4])


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
                    instr=nop
                elif by==1:
                    # ex af,af'
                    instr=ex_af_af()
                elif by==2:
                    # djnz d
                    instr=Instr("djnz d",
                                ["jsr zfetch", # disp
                                 "dec zrb:beq nb",
                                 "clc:adc zrpcl:sta zrpcl:bcc nc:inc zrpch:.nc",
                                 "ZTSTATES(5)",
                                 ".nb"],
                                [5,3])
                elif by==3:
                    # jr d
                    instr=Instr("jr d",
                                ["jsr zfetch", # disp
                                 "clc:adc zrpcl:sta zrpcl:bcc nc:inc zrpch:.nc"],
                                [4,3,5])
                elif by>=4:
                    # jr cc[y-4],d
                    instr=Instr("jr %s,d"%(["nz","z","nc","c"][by-4]),
                                ["jsr zfetch", # disp
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
                if by==6: instr=ld_ind8_imm(regs_16bit[prefix][2])
                else: instr=ld_r8_imm(regs_8bit[prefix][by])
            elif bz==7:
                if by==0: instr=Instr("rlca",
                                      ["lda zra:jsr zdo_rlc:sta zra"],
                                      [4])
                elif by==1: instr=Instr("rrca",
                                        ["lda zra:jsr zdo_rrc:sta zra"],
                                        [4])
                elif by==2: instr=Instr("rla",
                                        ["lda zra:jsr zdo_rl:sta zra"],
                                        [4])
                elif by==3: instr=Instr("rra",
                                        ["lda zra:jsr zdo_rr:sta zra"],
                                        [4])
                elif by==4: instr=ManualInstr("zop_daa","daa")
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
            if bz==6 and by==6: instr=ManualInstr("zop_halt","halt")
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
                    if bp==0: instr=ManualInstr("zop_ret","ret")
                    elif bp==1: instr=exx()
                    elif bp==2: instr=jp_ind(regs_16bit[prefix][2])
                    elif bp==3: instr=ld_r16_r16(reg_sp,regs_16bit[prefix][2])
            elif bz==2:
                instr=jpcc(by)
            elif bz==3:
                if by==0: instr=jp()
                elif by==1:
                    if prefix==0xdd: instr=ManualInstr("zprefixddcb","prefix_ddcb")
                    elif prefix==0xfd: instr=ManualInstr("zprefixfdcb","prefix_fdcb")
                    elif prefix is None: instr=ManualInstr("zprefixcb","prefix_cb")
                elif by==2: instr=Instr("out (n),a",
                                        ["jsr zfetch:tax:lda zra:tay:jsr zdo_out"],
                                        [4,3,4])
                elif by==3: instr=Instr("in a,(n)",
                                        ["jsr zfetch:tax:ldy zra:jsr zdo_in",
                                         "sta zra"],
                                        [4,3,4])
                elif by==4: instr=ex_sp(regs_16bit[prefix][2])
                elif by==5: instr=ex_de_hl()
                elif by==6: instr=ManualInstr("zop_di","di")
                elif by==7: instr=ManualInstr("zop_ei","ei")
            elif bz==4:
                instr=callcc(by)
            elif bz==5:
                if bq==0: instr=push(regs_16bit[prefix][bp])
                elif bq==1:
                    if bp==0: instr=call()
                    elif bp==1: instr=ManualInstr("zprefixdd","prefix_dd")
                    elif bp==2: instr=ManualInstr("zprefixed","prefix_ed")
                    elif bp==3: instr=ManualInstr("zprefixfd","prefix_fd")
            elif bz==6:
                instr=alu_imm(alu_mnemonics[by])
            elif bz==7:
                instr=ManualInstr("zop_rst","rst %02Xh"%(by*8))
            pass

        if instr is not None: instrs[opcode]=instr

    return instrs

##########################################################################
##########################################################################

rot_mnemonics=["rlc","rrc","rl","rr","sla","sra","sll","srl"]

def get_cb_opcodes(prefix):
    instrs=[]

    instrs=256*[None]

    for bx,by,bz in itertools.product(range(4),range(8),range(8)):
        instr=None
        opcode=(bx<<6)|(by<<3)|(bz<<0)

        if bx==0:
            mnem=rot_mnemonics[by]
            if bz==6: instr=rot_ind(mnem,regs_16bit[prefix][2])
            else:
                if prefix is None: instr=rot_r8(mnem,regs_8bit[prefix][bz])
                else: instr=rot_ind(mnem,regs_16bit[prefix][2],regs_8bit[None][bz])
        elif bx==1:
            if bz==6: instr=bit_ind(by,regs_16bit[prefix][2])
            else: instr=bit_r8(by,regs_8bit[prefix][bz])
        elif bx==2:
            if bz==6: instr=res_ind(by,regs_16bit[prefix][2])
            else:
                if prefix is None: instr=res_r8(by,regs_8bit[prefix][bz])
                else: instr=res_ind(by,regs_16bit[prefix][2],regs_8bit[None][bz])
        elif bx==3:
            if bz==6: instr=set_ind(by,regs_16bit[prefix][2])
            else:
                if prefix is None: instr=set_r8(by,regs_8bit[prefix][bz])
                else: instr=set_ind(by,regs_16bit[prefix][2],regs_8bit[None][bz])

        instrs[opcode]=instr

    return instrs

##########################################################################
##########################################################################

def get_ed_opcodes():
    instrs=[]
    
    instrs=256*[None]

    neg=ManualInstr("zop_neg","neg")
    reti=ManualInstr("zop_reti","reti")
    retn=ManualInstr("zop_retn","retn")
    im=ManualInstr("zop_im","im")

    for bx,by,bz in itertools.product(range(4),range(8),range(8)):
        instr=None
        opcode=(bx<<6)|(by<<3)|(bz<<0)

        bq=by&1
        bp=by>>1

        if bx==0 or bx==3:
            instr=nop
        elif bx==1:
            if bz==0: instr=in_r_c(regs_8bit[None][by])
            elif bz==1: instr=out_c_r(regs_8bit[None][by])
            elif bz==2:
                if bq==0: instr=adc_hl_r16(regs_16bit[None][bp])
                elif bq==1:instr=sbc_hl_r16(regs_16bit[None][bp])
            elif bz==3:
                if bq==0: instr=ld_mem_r16(regs_16bit[None][bp])
                elif bq==1: instr=ld_r16_mem(regs_16bit[None][bp])
            elif bz==4: instr=neg
            elif bz==5:
                if by==1: instr=reti
                else: instr=retn
            elif bz==6: instr=im
            elif bz==7:
                if by==0: instr=ManualInstr("zop_ld_i_a","ld i,a")
                elif by==1: instr=ManualInstr("zop_ld_r_a","ld r,a")
                elif by==2: instr=ManualInstr("zop_ld_a_i","ld a,i")
                elif by==3: instr=ManualInstr("zop_ld_a_r","ld a,r")
                elif by==4: instr=ManualInstr("zop_rrd","rrd")
                elif by==5: instr=ManualInstr("zop_rld","rld")
                elif by==6: instr=nop
                elif by==7: instr=nop
        elif bx==2:
            if bz<=3 and by>=4: pass
            else: instr=nop

        instrs[opcode]=instr

    return instrs

##########################################################################
##########################################################################

instrs_un=get_unprefixed_opcodes(None)
instrs_dd=get_unprefixed_opcodes(0xdd)
instrs_fd=get_unprefixed_opcodes(0xfd)

instrs_cb=get_cb_opcodes(None)
instrs_ddcb=get_cb_opcodes(0xdd)
instrs_fdcb=get_cb_opcodes(0xfd)

instrs_ed=get_ed_opcodes()

def remove_shared(main_list,prefixed_lists):
    opcode_by_dis={}
    for i,x in enumerate(main_list):
        if x is not None:
            assert x.dis not in opcode_by_dis,(hex(i),hex(opcode_by_dis[x.dis]),x.dis)
            opcode_by_dis[x.dis]=i

    # Any prefixed opcode that's an exact match (going by disassembly)
    # for one in the main list can be removed.
    for prefixed_list in prefixed_lists:
        for i,x in enumerate(prefixed_list):
            if x is not None:
                if x.dis in opcode_by_dis:
                    prefixed_list[i]=None

remove_shared(instrs_un,[instrs_dd,instrs_fd])
remove_shared(instrs_cb,[instrs_ddcb,instrs_fdcb])

# (this doesn't work properly (yet?) - e.g., `ld (nn),hl' has multiple encodings)

# # Ensure the remaining opcodes are all unique.
# def ensure_unique(*lists):
#     by_dis={}
#     for xs in lists:
#         for i,x in enumerate(xs):
#             if x is not None:
#                 assert x.dis not in by_dis or by_dis[x.dis][1] is x,(hex(i),
#                                                                      x.dis,
#                                                                      hex(by_dis[x.dis][0]),
#                                                                      by_dis[x.dis][1].dis)
#                 by_dis[x.dis]=(i,x)

# ensure_unique(instrs_un,instrs_dd,instrs_fd,instrs_cb,instrs_ddcb,instrs_fdcb,instrs_ed)

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
        if prefix is not None: instr.label+="%X"%prefix
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

    bads=[]
    for b7 in [0,1]:
        print ";;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;"
        print ";;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;"
        print

        label="zop_table_"
        if prefix is not None: label+="%X_"%prefix
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
                bads.append(opcode)
            else:
                label=instr.label
                dis=instr.dis

            line="equw %s ; "%label
            if prefix is not None: line+="%X"%prefix
            line+="%02X %s"%(opcode,dis)

            print line

        print

    print>>sys.stderr,"%s: %d/256 bad: %s"%("--" if prefix is None else "%02X"%prefix,len(bads),[hex(x) for x in bads])
    
generate_routines(instrs_un,None,None)
generate_routines(instrs_dd,instrs_un,0xdd)
generate_routines(instrs_fd,instrs_un,0xfd)
generate_routines(instrs_cb,None,0xcb)
generate_routines(instrs_ddcb,instrs_cb,0xddcb)
generate_routines(instrs_fdcb,instrs_cb,0xfdcb)
generate_routines(instrs_ed,None,0xed)
    
