import csv, io, json, os, urllib.request
from datetime import datetime, timezone, date, timedelta

SERIES=["DGS10","BAMLH0A0HYM2","T10Y2Y","VIXCLS","ICSA","PCEPILFE","DCOILWTICO"]

def fetch(sid):
    url=f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 MarketRiskDashboard/3.0"})
    with urllib.request.urlopen(req,timeout=30) as r:
        text=r.read().decode("utf-8")
    rows=[]
    rd=csv.reader(io.StringIO(text))
    next(rd,None)
    for row in rd:
        if len(row)<2 or row[1] in ("","."):
            continue
        try:
            rows.append({"date":row[0],"value":float(row[1])})
        except ValueError:
            pass
    return rows[-800:]

def idx_before(obs, ds):
    idx=-1
    for i,x in enumerate(obs):
        if x["date"]<=ds:
            idx=i
        else:
            break
    return idx

def val_before(series, sid, ds):
    a=series[sid]["observations"]
    i=idx_before(a,ds)
    return a[i]["value"] if i>=0 else 0.0

def risk_at(series, ds):
    y=val_before(series,"DGS10",ds)
    cr=val_before(series,"BAMLH0A0HYM2",ds)
    v=val_before(series,"VIXCLS",ds)

    claims=series["ICSA"]["observations"]
    ci=idx_before(claims,ds)
    cl=claims[ci]["value"] if ci>=0 else 0
    cl4=claims[ci-4]["value"] if ci>=4 else cl

    pce=series["PCEPILFE"]["observations"]
    pi=idx_before(pce,ds)
    inf=ip=0.0
    if pi>=13:
        inf=(pce[pi]["value"]/pce[pi-12]["value"]-1)*100
        ip=(pce[pi-1]["value"]/pce[pi-13]["value"]-1)*100

    r=0.0
    r += 2.2 if y>=5.3 else 1.6 if y>=4.8 else 1.0 if y>=4 else 0.4
    r += 2.4 if cr>=5 else 1.7 if cr>=4 else 1.0 if cr>=3 else 0.3
    r += 0.2  # default earnings = strong
    r += 1.4 if inf>ip+0.1 else 0.8 if inf>2.7 else 0.2
    r += 1.3 if cl>cl4*1.08 else 0.7 if cl>cl4*1.03 else 0.2
    r += 0.4  # default breadth = mixed
    r += 0.8 if v>=30 else 0.4 if v>=22 else 0.1
    return min(10,round(r,1))

def month_end(y,m):
    if m==12:
        return date(y,12,31)
    return date(y,m+1,1)-timedelta(days=1)

out={"updated_utc":datetime.now(timezone.utc).isoformat(),"series":{}}
for sid in SERIES:
    out["series"][sid]={"observations":fetch(sid)}

with open("data.json","w",encoding="utf-8") as f:
    json.dump(out,f,indent=2)

history={"history":[]}
if os.path.exists("history.json"):
    try:
        with open("history.json","r",encoding="utf-8") as f:
            history=json.load(f)
    except Exception:
        pass

# Rebuild monthly backfill for the latest 12 completed month-ends.
today=datetime.now(timezone.utc).date()
monthly=[]
for offset in range(11,-1,-1):
    y=today.year
    m=today.month-offset
    while m<=0:
        m+=12; y-=1
    while m>12:
        m-=12; y+=1
    me=month_end(y,m)
    if me>today:
        continue
    ds=me.isoformat()
    monthly.append({"date":ds,"risk":risk_at(out["series"],ds),"kind":"monthly_backfill"})

# Preserve non-monthly stored entries and replace today's daily entry.
existing=[x for x in history.get("history",[]) if x.get("kind")!="monthly_backfill" and x.get("date")!=today.isoformat()]
existing.append({
    "date":today.isoformat(),
    "risk":risk_at(out["series"],today.isoformat()),
    "DGS10":val_before(out["series"],"DGS10",today.isoformat()),
    "credit":val_before(out["series"],"BAMLH0A0HYM2",today.isoformat()),
    "VIX":val_before(out["series"],"VIXCLS",today.isoformat()),
    "kind":"daily"
})
allhist=monthly+existing
allhist=sorted(allhist,key=lambda x:x.get("date",""))[-450:]
history["history"]=allhist

with open("history.json","w",encoding="utf-8") as f:
    json.dump(history,f,indent=2)
