# Rohith — Phase 2: Survivability Research Summary

> ## ⚠ CORRECTION NOTICE (2026-09-01)
> **Every performance figure in this document is inflated and must be treated
> as an upper bound, not a measurement.** The tier-2 runs behind it excluded M1
> data from `load_bars`, so the engine ran at M15-bar resolution, not the "M1
> sub-bar fidelity" claimed throughout. Measured impact on the window where M1
> exists: profit factor overstated ~24% (1.444 → 1.160), net profit overstated
> ~3× (+$866.61 → +$290.97), with 78.6% of trades ambiguity-resolved instead of
> 0.5%. The *directional* conclusions (EMA_STACK best of those tested, session
> effects entry-specific, several entries ruin the account) still stand; the
> *numbers* do not. See `reports/PHASE_0_RESEARCH_AUDIT.md` and ledger COR-001.
>
> Additionally, §2's account-constraint claim is superseded: the broker imposes
> no minimum stop distance, so 0.01 lot does **not** force 15–20% risk. See
> `reports/ACCOUNT_100_USD_FEASIBILITY.md` and ledger COR-002.


**Session label:** "rohith" / "rohith-1" (continuous with the 2026-08-31 audit —
see `docs/research/MASTER_WEEKEND_AUDIT_AUG28.md` for phase 1). This document
covers phase 2: 2026-08-31 evening through 2026-09-01.

**The actual goal, stated by the user:** a rules-based system that survives
XAUUSD trading on a **~$100 account at fixed 0.01 lots**, going live with real
money on **2026-09-30**. Everything below is measured against that constraint,
not against abstract edge. All dollar figures assume the real starting balance
of **$105.74**, fixed 0.01-lot sizing, and the live 6%-daily-loss breaker
switched **on** — not the $100,000/breaker-off setup used for earlier edge
isolation work, which does not answer "will this survive."

Every number below cites a run directory under `research/runs/` per the
project's own rule: a verdict without a run directory is an opinion.

---

## 1. Why this phase started

The user pushed back on the discovery-phase conclusion that "no strategy
performed well," citing MorningMomentum's claimed 83% win rate and asking for
a Parabolic-SAR-based strategy to be tested, under the explicit constraint
that they only ever trade 0.01 lots and want "a system that will survive
that."

| Question | Answer |
|---|---|
| Is MorningMomentum's 83% win rate real? | **No.** Traces to an unverifiable README note. Measured: PF 0.87, −$417 over 674 trades (HYP-006, already settled in phase 1). |
| Does a 7-condition EMA/SAR/ADX/ChoCh/volume strategy work? | **No.** Rejected (HYP-025). |
| Does a simpler EMA200+SAR strategy work? | **No**, despite ranking #11 of 120 in the fast screen. Rejected (HYP-026). |
| Does *anything* survive the real $105.74/0.01-lot/breaker-on constraint? | **Yes — one candidate: EMA_STACK.** The rest of this document is the search for anything that beats it. |

---

## 2. The structural constraint underneath everything

XAUUSDm is a 100oz contract with a 0.01-lot minimum. At the current ATR, that
fixes minimum risk per trade at **$15.84 — 15% of a $105.74 account** —
regardless of which strategy is used. No smaller gold contract exists on this
broker (all six XAU symbols checked; HYP-024). This means the lever available
isn't "find a bigger edge," it's exit geometry, session choice, and account
growth over time diluting that percentage.

Because lot size is fixed, **% risk per trade shrinks as the balance grows.**
The first few weeks of live trading at ~$100 are therefore the structurally
riskiest stretch of the entire plan — not a risk that fades with time, one
that's front-loaded.

---

## 3. Top-10 tier-1 candidates, tested for real survivability

The fast tier-1 screen (120 candidates, next-bar entry, no daily caps) ranked
these ten highest by edge over a matched random-entry control. All ten were
rerun through the full tier-2 engine — M1 sub-bar execution, real costs, the
actual `RiskManager`, at $105.74 / 0.01 lots / breaker on — because the tier-1
screen had already been shown to miss compounding failure: the SAR candidate
that ranked #11 with edge_z +1.88 went to ~$0 under this exact test.

**Result: all 10 finished net positive. None beat EMA_STACK.**

| Rank | ID | Strategy | Trades | Win% | PF | Net $ | End Bal | Min Bal | Max DD (%pk) | Daily Breaches |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | XAU-062 | Squeeze breakout [NY] | 203 | 42.4 | **1.300** | +$435 | $540 | $38 | 68.1% | 35 |
| 2 | XAU-005 | EMA stack [ALL(London+NY) 3.0/1.5] | 838 | 39.6 | 1.245 | +$1,563 | $1,669 | $55 | 61.8% | 52 |
| 3 | XAU-075 | Opening range break [NY] | 492 | 40.0 | 1.192 | +$737 | $843 | $37 | 79.6% | 48 |
| 4 | XAU-006 | EMA stack [ALL(London+NY) 1.5/1.5] | 1495 | 55.1 | 1.166 | +$1,399 | $1,505 | $74 | 53.7% | 25 |
| 5 | XAU-049 | Range rejection wick [LONDON] | 127 | 38.6 | 1.156 | +$142 | $248 | $62 | 75.3% | 43 |
| 6 | XAU-092 | Fair value gap [NY] | 420 | 38.8 | 1.150 | +$505 | $610 | $71 | 72.2% | 38 |
| 7 | XAU-026 | HH/HL structure [NY] | 498 | 39.0 | 1.128 | +$491 | $597 | $77 | 51.2% | 37 |
| 8 | XAU-003 | EMA stack [NY 3.0/1.5] | 509 | 37.5 | 1.121 | +$472 | $578 | $55 | 75.3% | 68 |
| 9 | XAU-002 | EMA stack [LONDON 1.5/1.5] | 513 | 54.2 | 1.090 | +$258 | $364 | $53 | 87.6% | 49 |
| 10 | XAU-004 | EMA stack [NY 1.5/1.5] | 767 | 53.5 | 1.082 | +$371 | $477 | $51 | 73.7% | 67 |
| **—** | **EMA_STACK (live)** | **EMA20/50/200, no fixed TP, 24h** | **1436** | **44.0** | **1.319** | **+$3,769** | **$3,875** | **$72** | **32.2%** | **9** |

*Run: `research/runs/20260831-190849_screen_survivors`, script:
`scripts/tier2_screen_survivors.py` (in-sample window, 2025-04-03 to
2026-08-29).*

### What each column means, and its trade-off

| Term | What it measures | Advantage | Disadvantage / what it hides |
|---|---|---|---|
| **Trades (n)** | Completed trades in the 17-month window | Bigger n = more confidence WR/PF isn't luck | Under ~100 trades, results are noise (project rule); XAU-049's 127 is thin |
| **Win % (WR)** | % of trades closed in profit | Intuitive gut-check | Misleading alone — a 38% WR with 2:1 payoff beats a 55% WR with 1:1 payoff. Several "worse" WR rows above have better PF because TP=3×ATR pays double the 1.5×ATR SL |
| **PF (profit factor)** | Gross $ won ÷ gross $ lost | The real "is there edge" number, after realistic costs | Says nothing about *how* you get there — a PF of 1.3 from one huge lucky trade is fragile, from many small edges is robust |
| **Net $ / End $** | Total profit / final balance from $105.74 | The dollar answer you actually care about | A high end balance can hide a near-death dip in the middle — see Min Bal |
| **Min Bal** | Lowest balance ever touched, mid-sequence | The real "did I almost blow up" number | Single historical path — a different trade *order* (same trades, different luck) could dip deeper or shallower |
| **Max DD (% of peak)** | Largest drop from any equity high to the following low | Standard, comparable across account sizes | Doesn't say *when* — a 75% DD after growing to $2,000 is uncomfortable; the same 75% DD in week one is fatal. Use with Min Bal, not alone |
| **Daily Breaches** | Days the 6%-daily-loss breaker tripped (same live mechanism) | Best proxy for "how often does this feel awful to operate," not just P&L | The breaker caps the damage each time, but frequent trips (XAU-003/004: 67-68 times over 17 months) mean frequent stressful shutdown days even on a net-winning strategy |

**Reading the table:** every one of the ten alternatives runs meaningfully
hotter than EMA_STACK on drawdown and breach count, even where PF is
competitive or higher (XAU-062, XAU-005). None is a clear upgrade.

*(Ledger: HYP-028.)*

---

## 4. Why EMA_STACK wins: isolating the two levers

EMA_STACK and the tier-1 candidate XAU-005 share the *identical* entry rule
and the *identical* 3.0×ATR TP / 1.5×ATR SL. Yet EMA_STACK outperforms
(PF 1.319 vs 1.245, 32.2% DD vs 61.8%). The only remaining difference: XAU-005
was restricted to London+NY hours (11:30–21:30 IST); EMA_STACK has no session
gate at all.

**Test:** rerun the same rule and exit with the session gate removed.
**Result:** exact reproduction of EMA_STACK's own numbers — 1,436 trades,
PF 1.319, $105.74→$3,874.76, 32.2% DD, 9 breaches. Confirmed, not assumed.

*(Ledger: HYP-029. Run: `research/runs/20260831-203444_modified_variants`,
variant MOD-2.)*

### But 24-hour trading is not a free upgrade for every entry

Two further tests, same setup, different entries:

| Modification | Result | Verdict |
|---|---|---|
| **HH/HL structure entry, widened to 24h** | 7 trades, PF 0.000, balance went **negative (−$9)** — effectively ruined almost immediately | Catastrophic. Overnight conditions (thin liquidity, wider relative spread, gap risk) are specifically hostile to this entry |
| **EMA_STACK's own entry, 24h, but with a *tighter* 1.5/1.5 exit instead of its native 3.0/1.5** | 2,751 trades, PF 1.221, $105.74→$3,643 (headline looks nearly as good as plain EMA_STACK) — but the account dipped to **$10**, one bad trade from the $5 ruin floor, with a 91.1% peak drawdown | Deceptively dangerous. The near-miss is invisible in the net-P&L number alone |

**Conclusion:** session width and exit width are not independent levers you
can freely swap onto any entry. EMA_STACK's specific combination — no fixed
TP, no session gate — is not automatically reproducible elsewhere, and testing
it on other entries revealed real, different failure modes each time.

*(Ledger: HYP-030. Run: same as above, variants MOD-1 and MOD-3.)*

---

## 5. Does removing the Asian session fix or improve anything?

*(This section fills in once `research/runs/<timestamp>_no_asia` completes —
see the live table below.)*

The naive assumption is that Asia/overnight hours (02:30-11:30 IST) are the
dangerous ones -- thin liquidity, wider relative spread, gap risk -- and that
cutting them should improve everything. **That is wrong, and the direction of
the error depends on the exit style.**

| Variant | Session | Trades | Win% | PF | Net $ | End Bal | Min Bal | Max DD (%pk) | Breaches |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| EMA_STACK, native 3.0/1.5 exit | **24h (champion)** | 1436 | 44.0 | **1.319** | +$3,769 | $3,875 | $72 | **32.2%** | **9** |
| EMA_STACK, native 3.0/1.5 exit | no-Asia | 974 | 40.1 | 1.221 | +$1,767 | $1,873 | $41 | 79.6% | 60 |
| EMA_STACK, tight 1.5/1.5 exit | 24h | 2751 | 59.4 | 1.221 | +$3,537 | $3,643 | **$10** | 91.1% | 14 |
| EMA_STACK, tight 1.5/1.5 exit | no-Asia | 1825 | 56.6 | 1.179 | +$1,897 | $2,002 | $66 | 42.7% | 17 |
| HH/HL structure, 3.0/1.5 exit | NY-only | 498 | 39.0 | 1.128 | +$491 | $597 | $77 | 51.2% | 37 |
| HH/HL structure, 3.0/1.5 exit | 24h | 7 | 0.0 | **0.000** | −$115 | **−$9 (RUINED)** | −$9 | 108.7% | 6 |
| HH/HL structure, 3.0/1.5 exit | no-Asia | 1110 | 39.2 | 1.135 | +$1,233 | $1,339 | $20 | 81.3% | 31 |

*Run: `research/runs/20260831-*_no_asia`, script: `scripts/tier2_no_asia.py`.*

### The two results point in opposite directions

**For the native wide exit (3.0×ATR TP), removing Asia is harmful on every
axis.** Profit halves (+$3,769 -> +$1,767), PF drops (1.319 -> 1.221), max
drawdown more than doubles (32.2% -> 79.6%), and daily-breaker trips go from 9
to 60 -- a 6.7x increase in stressful shutdown days. Asia hours are not noise
for this setup; they are actively carrying part of the edge. This also
retroactively explains HYP-029: the reason 24h beat London+NY was not merely
"more trades," it was specifically the Asia contribution.

**For the tight exit (1.5×ATR TP), removing Asia is a genuine safety trade.**
The dangerous near-ruin dip that made the 24h tight-exit variant
unrecommendable ($10 minimum balance, 91.1% drawdown) largely disappears:
minimum balance rises to $66 and drawdown falls to 42.7%. The cost is roughly
half the profit (+$3,537 -> +$1,897) and a marginally lower PF. This is the
clearest risk/return trade-off surfaced anywhere in this research: **you can
buy a large reduction in ruin risk by giving up about half the return.**

### But neither beats the champion

Both no-Asia variants remain worse than plain EMA_STACK (24h, native exit) on
every metric simultaneously -- PF, net profit, drawdown, breach count, and
minimum balance. Removing Asia is therefore **not** a route to a better
strategy; it is only a route to making an already-inferior variant less
dangerous.

### Asia was the poison for HH/HL structure -- removing it rescues the entry

This is the sharpest single result in the whole phase. The HH/HL structure
entry was **ruined** by 24h trading (7 trades, balance to -$9). Excluding Asia
hours -- and changing nothing else -- turns that into **+$1,233 profit over
1,110 trades**. The Asia session alone accounts for the entire difference
between total ruin and a profitable strategy.

But it is still not a safe configuration, and it is instructive about *why*
raw profit misleads. Against its own NY-only version:

- no-Asia makes **2.5x more money** (+$1,233 vs +$491)
- but touches a **$20 minimum balance** vs NY-only's $77, and runs an **81.3%
  drawdown** vs 51.2%

So the ranking flips depending on which question is asked. "Which made more?"
-> no-Asia. "Which would you survive at $105 starting capital?" -> NY-only,
comfortably. At a $105 balance a dip to $20 is a hair from the $5 floor; at
$77 there is still room to recover.

**Practical reading:** Asia hours are hostile to structure-breakout entries
and helpful to the wide-exit EMA ribbon. This is a real, measured,
entry-specific effect -- not a general rule about overnight trading.

*(Ledger: HYP-031.)*

---

## 6. Full hypothesis log — everything tested, passed and failed

This mirrors `docs/research/RESEARCH_LEDGER.md`, condensed here for one-place
reading. Full detail and exact run citations live in that file.

### Settled in phase 1 (2026-08-31 audit)

| ID | Hypothesis | Verdict |
|---|---|---|
| HYP-001 | Old backtest describes the deployed system | REJECTED — measured a system never deployed |
| HYP-002 | Yahoo `GC=F` is an acceptable XAUUSDm proxy | REJECTED — different instrument entirely |
| HYP-003 | Strategies profitable before costs | SUPPORTED — PF 1.072 frictionless |
| HYP-004 | Strategies profitable after real costs | NOT ESTABLISHED — 86% of gross edge consumed by spread/slippage |
| HYP-005 | The 0.3×ATR trailing stop protects profit | REJECTED — it's the most harmful component tested |
| HYP-006 | MorningMomentum is a validated 83%-WR strategy | REJECTED — PF 0.87, unverifiable claim source |
| HYP-007 | EMAPullback should stay disabled | REJECTED — actually the best of the original three |
| HYP-008 | Consolidation exit is an active risk control | REJECTED — has never fired in 17 months |
| HYP-009 | 250-bar EMA200 warm-up distorts results | REJECTED — correctness issue only, no P&L effect |
| HYP-010 | Per-candle dedup improves profitability | REJECTED but kept anyway — for risk control, not return |
| HYP-011 | D1 bias gate is redundant | REJECTED — the gate filters real losers |
| HYP-012 | London Open is the highest-value session | REJECTED — it's the worst of the three main windows |
| HYP-013 | Asia/overnight is the most profitable session | REJECTED — artifact of an unfiltered pyramiding bug |
| HYP-014 | Broker clock is offset from UTC | REJECTED — clock is correct (UTC+0.00) |
| HYP-015 | 0.01-lot floor protects a small account | REJECTED — it's the minimum, not a cap; forces 15-20% risk |
| HYP-016 | Repairing known defects makes the system survivable | REJECTED — repairs slow the bleed, don't create edge |
| HYP-017 | Tighter take-profits raise win rate enough to compensate | REJECTED — monotonically the wrong direction |
| HYP-018 | Some trailing-stop configuration beats no trailing | REJECTED — no-trail wins across the entire grid |
| HYP-019 | "Wider TP is better" is just gold's uptrend in disguise | REJECTED — shorts outperform too, rules out drift artifact |
| HYP-020 | Entry signals contribute anything beyond exit geometry | OPEN / random-control test (ongoing methodology) |
| HYP-021 | Wide-TP result is a deployable edge, not a lottery | DOUBTFUL — rests on ~65 winning trades, fat right tail |
| HYP-022 | Locked holdout can validate a candidate | PARTIALLY BLOCKED — no bear-market data exists on this broker |
| HYP-023 | AsianSweep has an edge | INSUFFICIENT EVIDENCE — only 29 trades |
| HYP-024 | Account can trade XAUUSDm safely at any risk setting | REJECTED — 0.01 lot forces 15-20% risk at $105.74 |

### Settled in phase 2 (2026-08-31 evening → 2026-09-01, this document)

| ID | Hypothesis | Verdict |
|---|---|---|
| HYP-025 | 7-condition EMA/SAR/ADX/ChoCh/volume gate has an edge | REJECTED — account → ~$0 under real execution |
| HYP-026 | Simple EMA200+SAR gate has an edge | REJECTED — same failure despite looking strong in the fast screen |
| HYP-027 | EMA_STACK survives the real $105.74/0.01-lot/breaker-on constraint | **SUPPORTED, with caveats** — first and so far only candidate to clear this bar |
| HYP-028 | Top-10 tier-1 candidates survive at least as well as EMA_STACK | REJECTED — all net positive, none beats it (section 3 above) |
| HYP-029 | XAU-005 vs EMA_STACK gap is exit geometry | REJECTED — gap is session width, confirmed by exact reproduction |
| HYP-030 | Widening any candidate to 24h is generally safe | REJECTED as a general rule — entry-specific, can ruin or deceive |

---

## 6b. IN PROGRESS: full session matrix (started 2026-09-01, unfinished)

The no-Asia results in section 5 raised the obvious follow-up: does any entry
have a *specific* best session, strong enough to justify deploying it with a
hard single-session restriction? A full matrix was launched to answer this —
the seven distinct (entry rule, exit geometry) combinations covering all ten
top candidates, each tested under **Asia-only / London-only / NY-only / 24h**,
at the same real-constraint setup. 28 runs total.

It was still running when this document was written. Results append
incrementally to `scripts/tier2_session_matrix.py`'s run directory
(`research/runs/*_session_matrix/`) and to the console log. **Read that
directory before drawing conclusions about session specialisation** — nothing
in this document yet answers that question systematically; section 5 only
covers Asia inclusion/exclusion for three configurations.

Expected value of this test: section 5 already proved session effects are
large (ruin vs +$1,233 on the same entry) and entry-specific, so a
single-session specialist is plausible but unproven.

---

## 7. What's still open, going into the Sept 30 deadline

1. **No bear-market validation exists.** Both the development window and the
   locked holdout are bull-market gold (+40% and +68% respectively). EMA_STACK
   has never been tested against a falling or choppy regime on this broker's
   data (HYP-022, still open).
2. **The holdout run touched 60% underwater once** (HYP-027) — a real,
   historical near-miss, not a hypothetical tail risk.
3. **No written operating rulebook yet** — position-sizing floor, a loss cap
   tighter than 6% for the first weeks specifically, and a paper-to-live
   promotion path are all still undocumented. This is the natural next
   deliverable.
4. **The session matrix (section 6b) is unfinished** — the "is there a
   session specialist" question is open, with the test already built and
   running.
5. **EMA_STACK is grade B, not A** — promising, not yet validated to the
   project's own A-grade bar (needs a passing, not-yet-burned holdout run
   plus bootstrap confidence, which the current holdout run partially
   satisfies but the bull-market caveat weakens).

---

*Document opened 2026-09-01 as part of the "rohith" session. Update it in the
same commit as any new hypothesis that changes section 3-5's conclusions —
this file is a summary of `docs/research/RESEARCH_LEDGER.md`, not a
replacement for it.*
