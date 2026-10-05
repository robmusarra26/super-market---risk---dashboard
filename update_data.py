import csv, io, json, os, urllib.request
from datetime import datetime, timezone

SERIES=["DGS10","BAMLH0A0HYM2","T10Y2Y","VIXCLS","ICSA","PCEPILFE","DCOILWTICO"]

def fetch(sid):
    url=f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 MarketRiskDashboard/2.0"})
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
    return rows[-500:]

def latest(series, sid):
    a=series[sid]["observations"]
    return a[-1]["value"] if a else 0.0

def yoy_core(series):
    a=series["PCEPILFE"]["observations"]
    if len(a)<14:
        return (0.0,0.0)
    cur=a[-1]["value"]/a[-13]["value"]-1
    prev=a[-2]["value"]/a[-14]["value"]-1
    return (cur*100,prev*100)

def calc_risk(series):
    y=latest(series,"DGS10")
    cr=latest(series,"BAMLH0A0HYM2")
    v=latest(series,"VIXCLS")
    claims=series["ICSA"]["observations"]
    cl=claims[-1]["value"] if claims else 0
    cl4=claims[-5]["value"] if len(claims)>4 else cl
    inf,ip=yoy_core(series)
    r=0
    r += 2.2 if y>=5.3 else 1.6 if y>=4.8 else 1.0 if y>=4 else 0.4
    r += 2.4 if cr>=5 else 1.7 if cr>=4 else 1.0 if cr>=3 else 0.3
    r += 0.2  # default earnings = strong
    r += 1.4 if inf>ip+0.1 else 0.8 if inf>2.7 else 0.2
    r += 1.3 if cl>cl4*1.08 else 0.7 if cl>cl4*1.03 else 0.2
    r += 0.4  # default breadth = mixed
    r += 0.8 if v>=30 else 0.4 if v>=22 else 0.1
    return min(10,round(r,1))

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

entry={
    "date":datetime.now(timezone.utc).date().isoformat(),
    "risk":calc_risk(out["series"]),
    "DGS10":latest(out["series"],"DGS10"),
    "credit":latest(out["series"],"BAMLH0A0HYM2"),
    "VIX":latest(out["series"],"VIXCLS")
}
existing=[x for x in history.get("history",[]) if x.get("date")!=entry["date"]]
existing.append(entry)
history["history"]=existing[-400:]
with open("history.json","w",encoding="utf-8") as f:
    json.dump(history,f,indent=2)
