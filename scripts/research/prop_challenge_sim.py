"""Prop-challenge pass odds from a per-trade series (entry_time, net_pl@0.01, risk$@0.01).

Position size is set by risk% of INITIAL balance per trade (static, like most
prop firms' sizing), so R = net_pl / risk$. Challenge: reach +target% before the
equity falls -max_dd% below the start (static drawdown). A challenge is started
at every trade in the history (rolling start). Daily-loss limit is checked
per calendar day on realised P/L. Unfinished = history ended first.
"""
import sys, json, datetime as dt
import numpy as np

def sim(trades, risk_pct, target=8.0, max_dd=10.0, daily=5.0):
    t = np.array([x[0] for x in trades]); pl = np.array([x[1] for x in trades], float)
    rk = np.array([x[2] for x in trades], float)
    R = pl / (rk * 1.0 * 1.0 / 1.0)                    # 0.01 lot = 1 oz -> risk$ = distance
    day = (t // 86400)
    res = {"pass": 0, "fail_dd": 0, "fail_daily": 0, "open": 0}
    days_to_pass = []
    for s in range(len(R)):
        eq = 0.0; cur_day = day[s]; day_pl = 0.0; status = "open"
        for k in range(s, len(R)):
            if day[k] != cur_day: cur_day = day[k]; day_pl = 0.0
            p = R[k] * risk_pct
            eq += p; day_pl += p
            if day_pl <= -daily: status = "fail_daily"; break
            if eq <= -max_dd: status = "fail_dd"; break
            if eq >= target: status = "pass"; days_to_pass.append((t[k] - t[s]) / 86400); break
        res[status] += 1
    n = len(R)
    return {k: round(v / n * 100, 1) for k, v in res.items()}, (np.median(days_to_pass) if days_to_pass else None)

if __name__ == "__main__":
    for f in sys.argv[1:]:
        tr = json.load(open(f)); pl = np.array([x[1] for x in tr]); rk = np.array([x[2] for x in tr])
        R = pl / rk; w = R[R > 0].sum(); l = -R[R < 0].sum()
        yrs = (tr[-1][0] - tr[0][0]) / 86400 / 365
        print(f"\n{f.split('/')[-1]}: n={len(R)} ({len(R)/yrs:.0f}/yr) win={np.mean(R>0)*100:.1f}% PF(R)={w/l:.2f} "
              f"expectancy={R.mean():+.3f}R  avgWin={R[R>0].mean():.2f}R avgLoss={R[R<0].mean():.2f}R")
        for rp in (0.25, 0.5, 1.0):
            r, med = sim(tr, rp)
            print(f"   risk {rp}%/trade: {r}  median days to pass={med if med is None else round(med)}")
