import json, collections
from db import conn
c=conn(); cur=c.cursor(as_dict=True)
def Q(s,a=()): cur.execute(s,a); return cur.fetchall()
tables=Q("""SELECT s.name sch,t.name tbl,t.object_id oid,p.rows n FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id
 JOIN sys.partitions p ON p.object_id=t.object_id AND p.index_id IN (0,1) WHERE p.rows>0 AND s.name<>'dbo' ORDER BY s.name,t.name""")
cols=collections.defaultdict(dict)
for r in Q("select c.object_id oid,c.name,ty.name typ from sys.columns c join sys.types ty on ty.user_type_id=c.user_type_id"): cols[r['oid']][r['name']]=r['typ']
out=[]
for t in tables:
    cc=cols[t['oid']]
    cand=[n for n in ('CreationDate','LastModificationDate') if n in cc and cc[n].startswith('datetime')]
    rec=dict(sch=t['sch'],tbl=t['tbl'],n=t['n'],created_min=None,created_max=None,mod_max=None,after2021=None)
    try:
        if 'CreationDate' in cand:
            r=Q(f"select min(CreationDate) a,max(CreationDate) b,sum(case when CreationDate>='2021-01-01' then 1 else 0 end) c from [{t['sch']}].[{t['tbl']}]")[0]
            rec.update(created_min=str(r['a'])[:10],created_max=str(r['b'])[:10],after2021=r['c'])
        if 'LastModificationDate' in cand:
            rec['mod_max']=str(Q(f"select max(LastModificationDate) a from [{t['sch']}].[{t['tbl']}]")[0]['a'])[:10]
    except Exception as e: rec['err']=str(e)[:50]
    out.append(rec)
json.dump(out,open('usage.json','w'),ensure_ascii=False)
print(len(out))
