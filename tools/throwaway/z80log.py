#!/usr/bin/python
import sys,os,os.path,argparse,struct

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

class ZException(Exception): pass

##########################################################################
##########################################################################

class Reg:
    def __init__(self,name,mask=255):
        self.name=name
        self.mask=mask

    def clone(self):
        return Reg(self.name,self.mask)

version_reg_tables=[((1,2),[Reg("f"),Reg("a"),
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
                            Reg("pcl"),Reg("pch"),])
]


def find_regs_for_version(ver):
    for vers,regs in version_reg_tables:
        if ver in vers: return [x.clone() for x in regs]

    return None

##########################################################################
##########################################################################

class Log:
    def __init__(self,data):
        ver=ord(data[0])
        
        self.regs=find_regs_for_version(ver)
        if self.regs is None: raise ZException("unknown version: %d"%ver)

        if ver==1:
            self.base_index=0
            self._vlists_data=data[1:]
        elif ver==2:
            self.base_index=struct.unpack("<I",data[1:5])[0]
            self._vlists_data=data[5:]

        if len(self._vlists_data)%len(self.regs)!=0: raise ZException("bad size")

        self.set_keep_53(True)

    def set_keep_53(self,keep_53):
        mask=0b11111111 if keep_53 else 0b11010111
        for x in self.regs:
            if x.name=="f" or x.name=="f'": x.mask=mask


    def get_num_vlists(self): return self.base_index+len(self._vlists_data)/len(self.regs)

    def get_vlist_by_index(self,index):
        if index<self.base_index: return None
        
        i=(index-self.base_index)*len(self.regs)
        # print i,len(self._vlists_data)
        if i>=len(self._vlists_data): return None
        
        vlist=[]
        for j,reg in enumerate(self.regs): vlist.append(ord(self._vlists_data[i+j])&reg.mask)
        return vlist

##########################################################################
##########################################################################

def load_file(fname):
    with open(fname,"rb") as f: return Log(f.read())
    
##########################################################################
##########################################################################

def get_flags_str(x):
    s=""
    bits="SZ5H3PNC"
    for j in range(8):
        if x&(1<<(7-j)): s+=bits[j]
        else: s+="-"
    return s

def get_vlist_str(vlist,log):
    d=dict(zip([x.name for x in log.regs],vlist))
    d["fstr"]=get_flags_str(d["f"])
    
    return "AF=%(a)02X%(f)02X [%(fstr)s] BC=%(b)02X%(c)02X DE=%(d)02X%(e)02X HL=%(h)02X%(l)02X IX=%(ixh)02X%(ixl)02X IY=%(iyh)02X%(iyl)02X PC=%(pch)02X%(pcl)02X SP=%(sph)02X%(spl)02X (AF'=%(a')02X%(f')02X BC'=%(b')02X%(c')02X DE'=%(d')02X%(e')02X HL'=%(h')02X%(l')02X)"%d
    
##########################################################################
##########################################################################

def dump(options):
    log=load_file(options.input_fname)

    i=log.base_index
    while True:
        vlist=log.get_vlist_by_index(i)
        if vlist is None: break

        print "%d: %s"%(i,get_vlist_str(vlist,log))
        i+=1

##########################################################################
##########################################################################

def vlists_match(a,b):
    if len(a)!=len(b): return False

    for x,y in zip(a,b):
        if x!=b: return False

    return True

def are_regs_equivalent(a,b):
    if len(a)!=len(b): return False

    for i in range(len(a)):
        if a[i].name!=b[i].name: return False

    return True

def diff(options):
    good_log=load_file(options.good_fname)
    test_log=load_file(options.test_fname)

    if not are_regs_equivalent(good_log.regs,test_log.regs):
        raise ZException("reg lists not equivalent")

    good_log.set_keep_53(options._53)
    test_log.set_keep_53(options._53)

    print "Good file: %d-%d"%(good_log.base_index,good_log.get_num_vlists())
    print "Test file: %d-%d"%(test_log.base_index,test_log.get_num_vlists())

    if test_log.base_index<good_log.base_index or test_log.get_num_vlists()>good_log.get_num_vlists():
        raise ZException("good log doesn't cover test log's range")

    index=test_log.base_index
    while index<test_log.get_num_vlists():
        good_vlist=good_log.get_vlist_by_index(index)
        test_vlist=test_log.get_vlist_by_index(index)

        if good_vlist!=test_vlist:
            diffs=[]
            for i in range(len(good_vlist)):
                if good_vlist[i]!=test_vlist[i]: diffs.append(good_log.regs[i].name)
            print "Discrepancies found: index=%d: regs=%s"%(index,diffs)
            # print "good_vlist=%s"%good_vlist
            # print "test_vlist=%s"%test_vlist
            print "GOOD: %s"%get_vlist_str(good_vlist,good_log)
            print "TEST: %s"%get_vlist_str(test_vlist,test_log)

            if not options.keep_going: break

        index+=1

    # fnames=[options.input_fname_a,options.input_fname_b]

    # datas=[load_file(fnames[i]) for i in range(len(fnames))]

    # va=ord(datas[0][0])
    # vb=ord(datas[1][0])

    # if va!=vb: fatal("versions mismatch")

    # regs=version_tables.get(va)
    # if regs is None: fatal("unknown file version: %d"%va)

    # if not options._53:
    #     regs=regs[:]
    #     for reg in regs:
    #         if reg.name=="f" or reg.name=="f'": reg.mask=0b11010111

    # print len(regs)
    # for i in range(len(datas)):
    #     if (len(datas[i])-1)%len(regs)!=0: fatal("invalid length: %s"%fnames[i])

    # i=1
    # while i<len(datas[0]) and i<len(datas[1]):
    #     vlists=[get_vlist(data,regs,i) for data in datas]
    #     i+=len(regs)

    #     if not all_match(vlists):
    #         print "Discrepancy found at: offset=%d, instruction=%d"%(i,(i-1)/len(regs))
    #         for k in range(len(fnames)):
    #             print "%s:"%fnames[k]
    #             print "    %s"%get_vlist_str(vlists[k],regs)

    #         if not options.keep_going: break


##########################################################################
##########################################################################

def main(options):
    global g_verbose

    g_verbose=options.verbose

    try:
        options.func(options)
    except IOError,e:
        if e.errno==32:
            # ignore broken pipes - they're probably due to piping
            # through less or whatever.
            pass
        else: raise e
    except ZException,e:
        fatal(e.message)
        sys.exit(1)

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

    diffp.add_argument("-k",
                       "--keep-going",
                       action="store_true",
                       default=False,
                       help="keep going after the first discrepancy")

    diffp.add_argument("--53",
                       action="store_true",
                       default=False,
                       dest="_53",
                       help="check undocumented F bits 5/3 (by default: always clear them)")

    diffp.add_argument("good_fname",
                       metavar="GOOD-FILE")
    
    diffp.add_argument("test_fname",
                       metavar="TEST-FILE")

    main(parser.parse_args(sys.argv[1:]))
    

