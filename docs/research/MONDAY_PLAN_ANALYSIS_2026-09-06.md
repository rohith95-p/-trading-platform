# Analysis: "XAUUSD Monday Battle Plan" (Sept 8, 2026)

*2026-09-06. Every claim in the plan checked against this project's own
measured data. Where the plan makes a testable claim, it was tested rather
than argued with -- the two new scripts are
`scripts/validation/sprint_100_to_130.py` and
`scripts/validation/survivable_size.py`.*

---

## Verdict up front

**Do not run the sprint blueprint on Monday.** Its central claim was tested
directly against 355 real trading days and it loses: the plan's own $80 halt
is hit **more often** than its $30 target (36.9% vs 28.7%), and the median day
finishes at **−$3.72**. The plan is not badly reasoned -- large parts of it are
correct and align with findings here -- but the specific "$100 → $130 in a
day" mechanism it proposes is measurably negative-expectancy as a repeated
strategy.

---

## What the plan gets RIGHT (and this matters)

These are genuinely correct and independently corroborated by our data:

1. **"80-90% win rate claims are almost entirely false or overfit."** Correct,
   and our own ledger (HYP-039) reached the same conclusion from academic
   data. The plan's explanation of *how* they fake it (no stop / huge stop /
   tiny TP, or backtests excluding spread) is accurate.
2. **"Realistic M15 win rate is 35-45% with winners 2-3x losers."** Close to
   what we measure: the holdout runs **27.9% WR with avg win $21.50 vs avg
   loss $6.62** — a 3.25:1 ratio. The plan's shape is right; the win rate is
   optimistic by ~7-17 points.
3. **"A fixed $5 stop is guaranteed to be hit by noise."** Strongly confirmed,
   twice over. Our NY noise-floor measurement is $8.69 median adverse
   excursion against FVG_NY's ~$5.50 stop, and the 26-year D1 study
   independently puts gold's median *daily* true range at levels that dwarf it.
   This was already logged as a real defect.
4. **Session restriction to London/NY.** Consistent with the decision you made
   separately (11:30-21:30 IST), now enforced in code
   (`src/core/market_hours.py`).
5. **ATR-based stops rather than fixed dollar stops.** Already how the system
   works, and correct.

## What the plan gets WRONG

### 1. The sprint mechanism is negative-expectancy — tested, not argued

The plan's arithmetic is *"two $9 losses (−$18) and one $36 win (+$36) = +$18.
Two wins gets you to your $30 target."* That is true arithmetic about a
sequence it assumes; it never establishes how often that sequence happens.

Measured, by replaying all 355 real trading days in the holdout, each starting
fresh at $100 and walking that day's actual trade sequence until it touched
either barrier:

| Outcome | Days | Share |
|---|---:|---:|
| Hit **+$30 target** first | 102 | **28.7%** |
| Hit **−$20 halt** first | 131 | **36.9%** |
| Neither (day just ended) | 122 | 34.4% |

- **target:halt ratio = 0.78.** The sprint hits its stop *more often* than its
  goal. For a plan whose entire premise is "cap downside at $80, sprint to
  $130," that ratio needs to be comfortably above 1.
- **Median day: −$3.72.** Mean is +$2.99, but that mean is carried by rare
  outliers (best day +$146.81). Over half of days lose money.
- Only 44.2% of days finish profitable at all.

The plan would work if you got to *choose* the good days. Run repeatedly, it
bleeds.

### 2. Its entry rule was then backtested, and it loses money

The described entry (EMA20>50>200 stack + pullback + 60% rejection wick) is
**not** what either RangeRejection or EMAStack does -- it's a new hybrid. So it
was implemented exactly as specified and run on the same holdout
(`scripts/validation/monday_sprint_strategy.py`, 2025-01-01 -> 2026-05-20,
11:30-21:30 session, 1 position, 0.01 lot, SL 0.75x / TP 3.0x ATR as the plan
states).

The plan is internally inconsistent about the pullback reference -- its prose
says "pullback to the EMA 20", its pseudocode tests `last_candle.low <= ema50`.
Both readings were run:

| Variant | n | WR | PF | Net | Min balance | Max DD | P(ruin) | I.1 |
|---|---:|---:|---:|---:|---:|---:|---:|:-:|
| **As pseudocoded (EMA50)** | 377 | 20.4% | **0.9271** | **−$89.52** | **$16.22** | 93.8% | **76.2%** | FAIL |
| As prose says (EMA20) | 702 | 21.8% | 1.0664 | +$171.57 | $46.70 | 87.4% | 62.7% | FAIL |
| *FVG_NY alone (existing)* | *990* | *23.5%* | ***1.5004*** | *+$1,477* | *$104.20* | *35.7%* | *8.6%* | ***PASS*** |

**As literally specified, the rule loses money and takes a $105 account to
$16.22.** The prose variant is marginally profitable but with an 87% drawdown
and a 63% chance of ruin. Both are far worse than a leg the system already has.

Its win rate also lands at 20-22%, not the 35-45% the plan's own section 2
says legitimate M15 strategies achieve — the rule doesn't meet the standard the
plan itself sets.

This is also exactly the pattern `REAL_MONEY_READINESS.md` V.7 warns against:
*"No new strategies. No new indicators... The missing piece is proof, not more
system."*

### 3. Its macro reasoning contradicts our own 26-year measurement

The plan says high real yields "historically crushes gold." Our D1 study
(6,527 days, 2000-2026) measured the opposite: gold's forward 5-day return was
**+21.8bp after yields fell** and **+30.1bp after yields rose**. Gold did
*better* when yields rose. The relationship is also weak (corr −0.163). H3 was
formally rejected on this evidence today.

### 4. Internal inconsistency on session

It states the trading window as 11:30-21:30 IST in one section and
"London-New York Overlap... 13:30 to 17:30 IST" in another. These are
different rules.

### 5. Unverifiable point-in-time macro claims

PBoC tonnage, 10Y at 4.78%, TIPS at 2.42%, silver at $66, ratio 66:1 — none
verifiable from this repo. The internal consistency checks out (4330/66 ≈ 65.6),
but none of it is actionable without a source, and the plan's own trading logic
never actually uses these numbers.

---

## The real answer to "$100 → $130"

The plan asks the right question and reaches the wrong mechanism. Our
`survivable_size.py` sweep answers it directly, using the same measured edge
and varying only risk-per-trade:

| Risk scale | Route | P(ruin) | Median max DD | Median $/day |
|---|---|---:|---:|---:|
| 1.00 | Standard 0.01 lot @ $100 **(today)** | **39.4%** | 74.5% | $5.99 |
| 0.50 | ~$200 account | 17.1% | 50.4% | $3.00 |
| 0.25 | ~$400 account | 3.4% | 33.3% | $1.50 |
| **0.15** | **~$670 account** | **0.29%** | 24.0% | $0.90 |
| 0.10 | **CENT account 0.10 lot** (or ~$1000) | 0.03% | 18.3% | $0.60 |

**Survivability and daily return are the same dial.** There is no setting that
delivers $20-30/day and an acceptable ruin probability on $100. At the risk
level where the account reliably survives, it earns well under $1/day.

The one genuinely useful, executable option this surfaces is the **Exness Cent
account** (`XAUUSDc`) — already proposed as option (B) in
`REAL_MONEY_READINESS.md` Part II.1 and never acted on. At 0.10 cent-lot the
same edge runs at 1/10th the risk: **P(ruin) 0.03%** instead of 39.4%. It turns
a coin-flip on ruin into a survivable account *today*, at $100, without waiting
to grow capital. The cost is honest and unavoidable: ~$0.60/day, not $30.

---

## Recommendation

1. **Do not deploy the sprint blueprint.** It is measurably negative as a
   repeatable process (target:halt 0.78, median day −$3.72).
2. **Do not code a new strategy for Monday.** Nothing in the plan's entry logic
   has been tested; the project's entire failure history is untested strategies
   deployed on deadlines.
3. **Do move to a Cent account** if the goal is to trade real money at $100
   soon. It is the only change measured to make $100 survivable, and it is
   available now.
4. **Keep the honest number in view**: at survivable risk, this edge produces
   roughly **$0.60-0.90/day on $100**, and reaches $20-30/day only at
   roughly **$3,000-10,000** of capital. The gap is capital, exactly as the
   plan's own Part 6 concluded — that part of it is right.
