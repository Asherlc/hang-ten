"""Independent exact-rational audit of every actual runtime union support."""
import hashlib,json,struct
from fractions import Fraction as F


def validate(path,output):
    def number(s):return F.from_float(struct.unpack('>d',struct.pack('>Q',int(s,16)))[0])
    def dot(a,b):return sum((x*y for x,y in zip(a,b)),F(0))
    rows=json.loads(path.read_text());unknown=0;checked=0;vertices=0
    for row in rows:
        if row.get('unknown'):unknown+=1;continue
        n=list(map(number,row['n']));lo=number(row['lower']);hi=number(row['upper']);norm=number(row['normUpper'])
        assert norm>0 and norm**2>=dot(n,n),row['group']
        for p in row['vertices']:
            assert lo<=dot(list(map(number,p)),n)<=hi,row['group']
            vertices+=1
        checked+=1
    report={'owner':'strong-owl-live-physics','adopted':False,'checkedGroups':checked,'checkedVertices':vertices,
        'unknownGroups':unknown,'exactUnionSupportsPass':True,'inputSHA256':hashlib.sha256(path.read_bytes()).hexdigest()}
    output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
