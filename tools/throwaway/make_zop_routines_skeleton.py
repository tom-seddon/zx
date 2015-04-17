#!/usr/bin/python
for i in range(256):
    b=""
    for j in range(8): b+="1" if i&(1<<(7-j)) else "0"

    print ";;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;"
    print ";;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;"
    print
    print ".zop%02X ; %s %s %s"%(i,b[0:2],b[2:5],b[5:8])
    print "{"
    print "ZBAD"
    print "}"
    print
    
    
