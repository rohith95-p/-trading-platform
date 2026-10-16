"""Score strategies against the owner's bar on an Atlas-style account.

Input: per-trade series json files [entry_time, exit_time, net_pl@0.01lot, risk$@0.01lot] (R = net_pl/risk$).
Account model: $5,000, risk% per trade of START balance, Atlas Access limits (see constants).
Owner's bar: PF > 1.2 out of sample; drawdown < 60 % of the firm's limit; no single day > 20 % of profit.
Out-of-sample = 2023-08 -> 2026-10 (3+ yrs, includes the non-trending 2023-24 period); walk-forward rows
choose parameters only from the trailing 12 months, quarter by quarter.
"""
import sys, os, json, glob, datetime as dt, collections
import numpy as np
D = sys.argv[1]
# Atlas "Access" (official help pages): eval target 3%, DD 10% trailing equity, daily 5%;
# funded DD 6% trailing equity, daily 3% (trailing EOD), best day <= 40% of cycle profit, 3 days >=0.5%, split 90%,
# first payout after 28 days. The binding limits for a bot are the FUNDED ones.
LIMIT_DD, LIMIT_DAILY, ACCT = 6.0, 3.0, 5000.0
EVAL_TARGET, EVAL_DD = 3.0, 10.0
OOS_START = int(dt.datetime(2023, 8, 1, tzinfo=dt.timezone.utc).timestamp())
Y2025 = int(dt.datetime(2025, 1, 1, tzinfo=dt.timezone.utc).timestamp())

def load(f):
    a = json.load(open(f)); 
    out = []
    for x in a:
        if len(x) == 3: x = [x[0], x[0], x[1], x[2]]
        if x[3] > 0: out.append((int(x[0]), int(x[1]), x[2] / x[3]))   # R
    return sorted(out)

def pf(R):
    R = np.asarray(R, float); w = R[R > 0].sum(); l = -R[R < 0].sum()
    return (w / l) if l > 0 else float("inf")

def report(name, tr):
    tr = [t for t in tr if t[0] >= OOS_START]
    if len(tr) < 30: return f"{name:34s} too few trades ({len(tr)})", None
    R = np.array([t[2] for t in tr]); T = np.array([t[0] for t in tr])
    eq = np.cumsum(R); ddR = (np.maximum.accumulate(np.concatenate([[0], eq])) - np.concatenate([[0], eq])).max()
    day = collections.defaultdict(float)
    for t, r in zip(T, R): day[t // 86400] += r
    pos = sum(v for v in day.values() if v > 0); share = max(day.values()) / pos * 100 if pos else 100
    worst_day = -min(day.values())
    # largest risk% that keeps DD <= 60% of limit AND worst day <= 60% of daily limit
    risk_dd = 0.6 * LIMIT_DD / ddR if ddR > 0 else 9
    risk_day = 0.6 * LIMIT_DAILY / worst_day if worst_day > 0 else 9
    risk = min(risk_dd, risk_day, 1.0)
    yrs = (T[-1] - T[0]) / 86400 / 365
    ann = R.sum() * risk / yrs
    p_all = pf(R); p25 = pf([t[2] for t in tr if t[0] >= Y2025]); p2324 = pf([t[2] for t in tr if t[0] < Y2025])
    ok_pf = p_all > 1.2; ok_day = share <= 20; ok_dd = risk >= 0.25
    verdict = "PASS" if (ok_pf and ok_day and ok_dd) else "fail:" + ",".join(k for k, v in (("PF", ok_pf), ("day%", ok_day), ("DD", ok_dd)) if not v)
    line = (f"{name:34s} n={len(R):4d} PF={p_all:4.2f} (23-24:{p2324:4.2f} 25-26:{p25:4.2f}) E={R.mean():+.2f}R maxDD={ddR:4.1f}R "
            f"bestDay={share:3.0f}% fitRisk={risk:4.2f}% ann={ann:+5.1f}%/yr  {verdict}")
    return line, (R, T, risk)

def lifecycle(R, T, risk):
    """Rolling-start Atlas Access life cycle at `risk`% per trade (closed-trade equity approximation).
    Eval: reach +3% before equity falls 10% below its peak (trailing). Funded: trailing 6% DD from peak,
    daily loss 3%; first payout at day 28 if alive, >=3 days with >=0.5% gain, best day <=40% of cycle profit."""
    n = len(R); res = dict(pass_=0, fail=0, open=0); pay = []; alive28 = 0; qual = 0; funded = 0
    for s0 in range(n):
        eq = 0.0; peak = 0.0; st = "open"; k = s0
        while k < n:
            eq += R[k] * risk; peak = max(peak, eq)
            if eq >= EVAL_TARGET: st = "pass"; break
            if peak - eq >= EVAL_DD: st = "fail"; break
            k += 1
        res["pass_" if st == "pass" else st] += 1
        if st != "pass": continue
        funded += 1; t0 = T[k]; eq = 0.0; peak = 0.0; days = collections.defaultdict(float); dead = False; j = k + 1
        while j < n and T[j] < t0 + 28 * 86400:
            r = R[j] * risk; eq += r; peak = max(peak, eq); days[T[j] // 86400] += r
            if peak - eq >= LIMIT_DD or days[T[j] // 86400] <= -LIMIT_DAILY: dead = True; break
            j += 1
        if dead or j >= n: continue
        alive28 += 1
        cyc = sum(v for v in days.values() if v > 0); good = sum(1 for v in days.values() if v >= 0.5)
        if eq > 0 and good >= 3 and (max(days.values()) <= 0.4 * eq + 1e-9):
            qual += 1; pay.append(0.9 * eq / 100 * ACCT)
    tot = n
    return dict(p_eval=res["pass_"] / tot * 100, p_fail=res["fail"] / tot * 100, p_alive28=(alive28 / funded * 100 if funded else 0),
                p_payout=(qual / funded * 100 if funded else 0), avg_payout=(float(np.mean(pay)) if pay else 0.0))

def geom_wf(label, geoms):
    """quarterly walk-forward over geometries for one leg"""
    series = {g: load(f) for g, f in geoms.items()}
    qs = []; y, q = 2023, 3
    while (y, q) <= (2026, 3):
        qs.append((y, q)); q += 1
        if q == 5: y, q = y + 1, 1
    chosen = []; log = []
    for (y, q) in qs:
        qstart = lambda yy, qq: int(dt.datetime(yy, 3 * qq - 2, 1, tzinfo=dt.timezone.utc).timestamp())
        start = qstart(y, q)
        end = qstart(y + (q == 4), 1 if q == 4 else q + 1)
        lo = start - 365 * 86400
        best, bp = None, 1.05
        for g, tr in series.items():
            hist = [t[2] for t in tr if lo <= t[0] < start]
            if len(hist) >= 40 and pf(hist) > bp: best, bp = g, pf(hist)
        if best: chosen += [t for t in series[best] if start <= t[0] < end]
        log.append(best)
    return chosen, log

if __name__ == "__main__":
    files = sorted(glob.glob(os.path.join(D, "*.json")))
    print(f"Account ${ACCT:.0f}, limits: DD {LIMIT_DD}% static, daily {LIMIT_DAILY}%.  OOS = 2023-08 -> 2026-10\n")
    legs = collections.defaultdict(dict)
    for f in files:
        b = os.path.basename(f)[:-5]
        report_line, extra = report(b, load(f)); print(report_line)
        if extra and "PASS" in report_line:
            lc = lifecycle(*extra); print(f"      lifecycle @ {extra[2]:.2f}% risk: eval pass {lc['p_eval']:.0f}% / fail {lc['p_fail']:.0f}% ; funded alive at day 28: {lc['p_alive28']:.0f}% ; qualifies for 1st payout: {lc['p_payout']:.0f}% ; avg 1st payout ${lc['avg_payout']:.0f}")
        parts = b.rsplit("_", 2)
        if len(parts) == 3 and parts[1].replace(".", "").isdigit() and parts[2].replace(".", "").isdigit():
            legs[parts[0]][(float(parts[1]), float(parts[2]))] = f
    print("\n--- Walk-forward geometry selection (trailing-12-month PF, sit out if < 1.05) ---")
    for leg, g in legs.items():
        if len(g) < 2: continue
        tr, log = geom_wf(leg, g)
        line, _ = report(leg + " [WF geometry]", tr)
        print(line); print("   chosen per quarter:", [f"{x[0]}/{x[1]}" if x else "sit-out" for x in log])
