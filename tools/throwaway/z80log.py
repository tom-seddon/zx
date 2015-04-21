#!/usr/bin/python
import sys,os,os.path,argparse

##########################################################################
##########################################################################

g_verbose=False

def v(x):
    if g_verbose:
        sys.stdout.write(x)
        sys.stdout.flush()

def fatal(msg):
    sys.stderr.write("FATAL: ")
    sys.stderr.write(msg)
    if msg[-1]!='\n': sys.stderr.write("\n")
    sys.stderr.flush()
    sys.exit(1)
        
##########################################################################
##########################################################################

class Reg:
    def __init__(self,name):
        self.name=name
        self.mask=255

version_tables={
    1:[
        Reg("f"),Reg("a"),
        Reg("c"),Reg("b"),
        Reg("e"),Reg("d"),
        Reg("l"),Reg("h"),
        Reg("f'"),Reg("a'"),
        Reg("c'"),Reg("b'"),
        Reg("e'"),Reg("d'"),
        Reg("l'"),Reg("h'"),
        Reg("ixl"),Reg("ixh"),
        Reg("iyl"),Reg("iyh"),
        Reg("spl"),Reg("sph"),
        Reg("pcl"),Reg("pch"),
    ]
}

##########################################################################
##########################################################################

def load_file(fname):
    with open(fname,"rb") as f: return f.read()

    
def get_vlist(data,regs,offset):
    vlist=[]
    for i,reg in enumerate(regs): vlist.append(ord(data[offset+i])&reg.mask)
    return vlist
    
##########################################################################
##########################################################################

def get_flags_str(x):
    s=""
    bits="SZ5H3NPC"
    for j in range(8):
        if x&(1<<(7-j)): s+=bits[j]
        else: s+="-"
    return s

def get_vlist_str(vlist,regs):
    d=dict(zip([x.name for x in regs],vlist))
    d["fstr"]=get_flags_str(d["f"])
    
    return "AF=%(a)02X%(f)02X [%(fstr)s] BC=%(b)02X%(c)02X DE=%(d)02X%(e)02X HL=%(h)02X%(l)02X IX=%(ixh)02X%(ixl)02X IY=%(iyh)02X%(iyl)02X PC=%(pch)02X%(pcl)02X SP=%(sph)02X%(spl)02X (AF'=%(a')02X%(f')02X BC'=%(b')02X%(c')02X DE'=%(d')02X%(e')02X HL'=%(h')02X%(l')02X)"%d
    
##########################################################################
##########################################################################

def dump(options):
    data=load_file(options.input_fname)

    ver=ord(data[0])
    regs=version_tables.get(ver)
    if regs is None: fatal("unknown version: %d"%ver)

    if (len(data)-1)%len(regs)!=0: fatal("invalid length")

    try:
        i=1
        while i<len(data):
            vlist=get_vlist(data,regs,i)
            i+=len(regs)

            print get_vlist_str(vlist,regs)
    except IOError:
        # ignore it... assume broken pipe, e.g., from less.
        pass

##########################################################################
##########################################################################

def all_match(vlists):
    for vlist in vlists[1:]:
        for j in range(len(vlist)):
            if vlist[j]!=vlists[0][j]:
                return False

    return True

def diff(options):
    fnames=[options.input_fname_a,options.input_fname_b]

    datas=[load_file(fnames[i]) for i in range(len(fnames))]

    va=ord(datas[0][0])
    vb=ord(datas[1][0])

    if va!=vb: fatal("versions mismatch")

    regs=version_tables.get(va)
    if regs is None: fatal("unknown file version: %d"%va)

    if not options._53:
        regs=regs[:]
        for reg in regs:
            if reg.name=="f" or reg.name=="f'": reg.mask=0b11010111

    print len(regs)
    for i in range(len(datas)):
        if (len(datas[i])-1)%len(regs)!=0: fatal("invalid length: %s"%fnames[i])

    i=1
    while i<len(datas[0]) and i<len(datas[1]):
        vlists=[get_vlist(data,regs,i) for data in datas]
        i+=len(regs)

        if not all_match(vlists):
            print "Discrepancy found at: offset=%d, instruction=%d"%(i,(i-1)/len(regs))
            for k in range(len(fnames)):
                print "%s:"%fnames[k]
                print "    %s"%get_vlist_str(vlists[k],regs)
            break


##########################################################################
##########################################################################

def main(options):
    global g_verbose

    g_verbose=options.verbose

    options.func(options)

##########################################################################
##########################################################################

if __name__=="__main__":
    parser=argparse.ArgumentParser(description="ZX Z80 log file tools")
    parser.add_argument("-v",
                        "--verbose",
                        action="store_true",
                        default=False,
                        help="verbose")

    subp=parser.add_subparsers(help="sub-command help")

    #
    # dump
    # 

    dumpp=subp.add_parser("dump",
                          help="dump trace file")
    dumpp.set_defaults(func=dump)

    dumpp.add_argument("input_fname",
                       metavar="FILE",
                       help="read data from %(metavar)s")

    #
    # diff
    #

    diffp=subp.add_parser("diff",
                          help="diff trace files")
    diffp.set_defaults(func=diff)

    diffp.add_argument("--53",
                       action="store_true",
                       default=False,
                       dest="_53",
                       help="check undocumented F bits 5/3 (by default: always clear them)")

    diffp.add_argument("input_fname_a",
                       metavar="FILE1")
    
    diffp.add_argument("input_fname_b",
                       metavar="FILE2")

    main(parser.parse_args(sys.argv[1:]))
    

