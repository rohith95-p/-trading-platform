import sys, os, json, time, numpy as np
sys.path.insert(0, r"C:\projects\ultra_core"); os.chdir(r"C:\projects\ultra_core")
from src.research.candidates import build_library
from src.research.candidates_v2 import build_library_v2
from src.research.market_study import build_features
from src.research.screener import simulate, random_control, _session_mask
rates=np.load("research/data/XAUUSDm_M15.npy")
f=build_features(rates)
t=rates["time"].astype("int64")
split=int(__import__("datetime").datetime(2025,1,1,tzinfo=__import__("datetime").timezone.utc).timestamp())
is_m=t<split; oos_m=t>=split
lib=build_library()+build_library_v2()
print("candidates",len(lib),flush=True)
out=[]; t0=time.time()
for k,c in enumerate(lib):
    try:
        sig=c.rule(f).astype(np.int8)
        sig[~_session_mask(f["ist_hour"],c.session)]=0; sig[:250]=0
        row={"id":c.id,"name":c.name,"family":c.family,"session":list(c.session),"tp":c.tp_atr,"sl":c.sl_atr}
        for lab,m in (("is",is_m),("oos",oos_m)):
            s=np.where(m,sig,0).astype(np.int8)
            r=simulate(f,s,c.tp_atr,c.sl_atr,c.max_bars)
            row[lab]={kk:r.get(kk,0) for kk in("trades","win_rate","expectancy_r","profit_factor")}
            if lab=="is" and r.get("trades",0)>=100:
                cm,csd=random_control(f,c,r["trades"],r["long_trades"]/r["trades"],reps=5)
                row["is"]["edge_z"]=round((r["expectancy_r"]-cm)/csd,2) if csd and csd==csd and csd>0 else 0
        out.append(row)
    except Exception as e:
        pass
    if k%50==0: print(k,round(time.time()-t0),flush=True)
json.dump(out,open(sys.argv[1],"w"))
print("done",len(out),flush=True)
