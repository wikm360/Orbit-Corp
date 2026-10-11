import sys
from db import conn
c=conn(); cur=c.cursor(as_dict=True)
def Q(s,a=()): cur.execute(s,a); return cur.fetchall()
def peek(full,n=3,w=45,skip=('Version',)):
    sch,tbl=full.split('.')
    cnt=Q(f"select count(*) n from [{sch}].[{tbl}]")[0]['n']
    print(f"## {full} ({cnt})")
    rows=Q(f"select top {n} * from [{sch}].[{tbl}] order by newid()") if cnt>n else Q(f"select * from [{sch}].[{tbl}]")
    for r in rows[:n]:
        print('  ~',{k:(str(v)[:w]) for k,v in r.items() if v is not None and k not in skip and v!='' and not isinstance(v,(bytes,bytearray))})
    print()
if __name__=='__main__':
    for t in sys.argv[1:]: 
        try: peek(t)
        except Exception as e: print(t,'ERR',str(e)[:80])
