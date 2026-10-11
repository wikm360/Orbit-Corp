import os, collections
from db import q
OUT=os.environ.get('RAHKARAN_DOCS_OUT','/home/wikm/Documents/Orbit-Corp/Backend/docs/rahkaran')
dlt={r['DLTypeID']:r['Title'] for r in q("select DLTypeID,Title from FIN3.DLType")}
rel=collections.defaultdict(list)
for r in q("select SLRef,Level,DLTypeRef from FIN3.DLTypeRelation order by SLRef,Level"): rel[r['SLRef']].append((r['Level'],r['DLTypeRef']))
act={r['SLRef']:r for r in q("""select i.SLRef,count(*) n,min(v.Date) first,max(v.Date) last,
 sum(case when v.FiscalYearRef=117 then 1 else 0 end) n117,
 sum(case when v.FiscalYearRef=117 and v.VoucherTypeRef not in (5,6,7) then isnull(i.Debit,0) else 0 end) d117,
 sum(case when v.FiscalYearRef=117 and v.VoucherTypeRef not in (5,6,7) then isnull(i.Credit,0) else 0 end) c117
 from FIN3.VoucherItem i join FIN3.Voucher v on v.VoucherID=i.VoucherRef group by i.SLRef""")}
pat=collections.defaultdict(collections.Counter)
for r in q("""select i.SLRef,i.DLTypeRef4 a,i.DLTypeRef5 b,i.DLTypeRef6 c,i.DLTypeRef7 d,count(*) n from FIN3.VoucherItem i join FIN3.Voucher v on v.VoucherID=i.VoucherRef where v.FiscalYearRef>=114 group by i.SLRef,i.DLTypeRef4,i.DLTypeRef5,i.DLTypeRef6,i.DLTypeRef7"""):
    pat[r['SLRef']][(r['a'],r['b'],r['c'],r['d'])]+=r['n']
def patstr(slid):
    c=pat.get(slid)
    if not c: return ''
    tot=sum(c.values()); out=[]
    for k,n in c.most_common(2):
        lv=[f"L{4+i}:{dlt.get(t,t)}" for i,t in enumerate(k) if t is not None]
        out.append(("+".join(lv) or 'بدون تفصیلی')+f" ({round(100*n/tot)}٪)")
    return " ؛ ".join(out)
gls=q("select g.GLID,g.Code,rtrim(g.Title) Title,g.AccountGroupRef,g.Nature,g.Type from FIN3.GL g order by g.Code")
sls=q("select s.SLID,s.Code,rtrim(s.Title) Title,s.GLRef,s.Nature,s.Type,s.State,s.IsTraceable,s.IsMultiCurrency,s.IsQuantifiable from FIN3.SL s order by s.Code")
ag={r['AccountGroupID']:r['Title'].strip() for r in q("select AccountGroupID,Title from FIN3.AccountGroup")}
by_gl=collections.defaultdict(list)
for s in sls: by_gl[s['GLRef']].append(s)
def b(x): return round(float(x)/1e6)  # million rial
L=["# واژه‌نامه‌ی حساب‌ها (کل / معین) — تولید خودکار از داده","",
"هر معین با تعداد ردیف سند (کل تاریخچه)، بازه‌ی استفاده و گردش سال مالی 1404 (به **میلیون ریال**، بدون اسناد افتتاحیه/اختتامیه/بستن) و انواع تفصیلی مجاز در هر سطح. معین‌های «بدون ردیف سند» هرگز استفاده نشده‌اند.","",
"> سطح‌های تفصیلی: `L4/L5/L6` = ستون‌های `DLLevel4/5/6` در `VoucherItem`.","" ]
tot_used=0
for g in gls:
    ss=by_gl[g['GLID']]; used=[s for s in ss if s['SLID'] in act]
    gn=sum(act[s['SLID']]['n'] for s in used)
    L.append(f"## {g['Code']} — {g['Title']}  \n_گروه: {ag.get(g['AccountGroupRef'],'')} · معین‌ها: {len(ss)} (استفاده‌شده: {len(used)}) · ردیف‌های سند: {gn:,}_\n")
    if not ss: continue
    L.append("| کد | معین | ردیف سند | اولین → آخرین | گردش 1404 (بدهکار / بستانکار، م.ر) | الگوی واقعی تفصیلی (1402–1404) | تفصیلی مجاز |\n|---|---|---:|---|---|---|---|")
    for s in ss:
        a=act.get(s['SLID']); tot_used+= 1 if a else 0
        r=rel.get(s['SLID'],[]); dl="، ".join(f"L{lv}:{dlt.get(t,t)}" for lv,t in r)
        if a: L.append(f"| {s['Code']} | {s['Title']}{'' if s['State'] else ' (غیرفعال)'} | {a['n']:,} | {str(a['first'])[:7]} → {str(a['last'])[:7]} | {b(a['d117']):,} / {b(a['c117']):,} | {patstr(s['SLID'])} | {dl} |")
        else: L.append(f"| {s['Code']} | {s['Title']}{'' if s['State'] else ' (غیرفعال)'} | — (بدون ردیف سند) | | | | {dl} |")
    L.append("")
open(f"{OUT}/GLOSSARY_ACCOUNTS.md",'w').write("\n".join(L))
print(len(gls),'GL',len(sls),'SL',tot_used,'used SL')
