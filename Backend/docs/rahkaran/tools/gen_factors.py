"""Profile every HCM3.CompensationFactor (usage in PayCalcItem/PeriodicCalcItem) -> factors.json (input of gen_glossary_payroll.py)."""
import json, os
from db import q
rows=q("""select f.CompensationFactorID id,f.Name,f.Title,f.CategoryCode cat,f.AssignTypeCode asg,f.MeasurementUnitCode unit,t.Title calctype
 from HCM3.CompensationFactor f join HCM3.CompensationCalcType t on t.CompensationCalcTypeID=f.CompensationCalcTypeRef""")
pay={r['id']:r for r in q("select i.CompensationFactorRef id,count(*) n,sum(case when i.Value<>0 then 1 else 0 end) nz,max(i.ApplyYearMonth) lastm from HCM3.PayCalcItem i group by i.CompensationFactorRef")}
per={r['id']:r for r in q("select CompensationFactorRef id,count(*) n,sum(case when Value<>0 then 1 else 0 end) nz,max(IssueYearMonth) lastm from HCM3.PeriodicCalcItem group by CompensationFactorRef")}
MONTH=int(os.environ.get('RAHKARAN_REF_MONTH','140504'))  # latest complete payroll month
lm={r['id']:r for r in q("select i.CompensationFactorRef id,sum(case when i.Value<>0 then 1 else 0 end) nz,sum(i.Value) s from HCM3.PayCalcItem i join HCM3.PayCalc p on p.PayCalcID=i.PayCalcRef where p.IssueYearMonth=%s and i.ApplyYearMonth=%s group by i.CompensationFactorRef",(MONTH,MONTH))}
out=[]
for r in sorted(rows,key=lambda r:(r['cat'],r['id'])):
    p=pay.get(r['id']); e=per.get(r['id']); l=lm.get(r['id'])
    out.append(dict(id=r['id'],name=r['Name'],title=r['Title'],cat=r['cat'],unit=r['unit'],asg=r['asg'],calctype=r['calctype'],pay_n=p and p['n'] or 0,pay_nz=p and p['nz'] or 0,pay_last=p and p['lastm'],per_n=e and e['n'] or 0,per_nz=e and e['nz'] or 0,m_nz=l and l['nz'] or 0,m_sum=float(l['s']) if l and r['unit']==1 else None))
json.dump(out,open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'factors.json'),'w'),ensure_ascii=False)
