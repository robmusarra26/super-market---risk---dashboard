import csv, io, json, urllib.request
from datetime import datetime, timezone

SERIES=["DGS10","BAMLH0A0HYM2","T10Y2Y","VIXCLS","ICSA","PCEPILFE","DCOILWTICO"]

def fetch(sid):
    url=f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 MarketRiskDashboard/1.0"})
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

out={"updated_utc":datetime.now(timezone.utc).isoformat(),"series":{}}
for sid in SERIES:
    out["series"][sid]={"observations":fetch(sid)}

with open("data.json","w",encoding="utf-8") as f:
    json.dump(out,f,indent=2)
