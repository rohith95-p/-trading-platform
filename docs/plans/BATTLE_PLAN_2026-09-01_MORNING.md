# Battle Plan — Morning of 2026-09-01

Written overnight while you slept, for you to review on waking. Nothing in
this document has been executed against the live/demo account. Every action
below needs your explicit go-ahead -- see section 4.

## READ THIS FIRST: likely duplicate live-trading process

Two main_loop.py processes are running simultaneously against the demo
account, both launched at the exact same second (2026-08-31 20:50:35):

| PID | Interpreter |
|---|---|
| 47068 | C:/projects/ultra_core/venv/Scripts/python.exe (project venv) |
| 30140 | C:/Users/rohit/AppData/Local/Programs/Python/Python311/python.exe (global install) |

Identical timestamp, identical command, two different interpreters -- this
has the signature of an accidental double-launch, not an intentional setup.
If it is a duplicate, every trading signal since 20:50 last night has
potentially been acted on twice independently, which is the *exact* failure
mode your own research ledger already documented once (HYP-010: a duplicate
fill doubled a live loss to -$55.58). Since this is the demo account the
financial cost is zero, but it means:
- Any live behaviour observed since 20:50 is not clean data -- two processes
  racing on the same signals.
- If you only meant to run one, kill the one you don't recognize starting
  (`taskkill /F /PID <pid>`) before trusting anything about "how the account
  behaved overnight."

Not killed automatically -- restarting a currently-running trading process is
a call I left for you, not something to do unsupervised at 3am.

**Root cause found, and it's bigger than main_loop:** while parallelizing
tonight's research (section 3), every single python launch in this
environment -- via PATH, via absolute interpreter path, no matter how
invoked -- spawned twice: once through the project's venv interpreter, once
through a separate global Python 3.11 install. Reproduced 3 times with
different launch methods. This is almost certainly what happened to
main_loop.py too -- not a manual double-launch, an environment-level quirk
(likely a Windows python.exe App Execution Alias or similar redirect layer).
**This needs to be understood and fixed before Sept 30** -- any live
automation launched the normal way in this environment will double-spawn by
default, which is a real risk for real money, not just a research-compute
inefficiency. Worth a `where python` / `Get-Command python -All` investigation
and a decision to pin one interpreter explicitly everywhere before going live.

---

## 1. What got done overnight

- Tested **13 candidate strategies** and **3 deliberate modifications** against
  your real constraint: $105.74 balance, fixed 0.01 lots, live 6%-daily-loss
  breaker on. Full detail: `docs/research/ROHITH_PHASE2_SURVIVABILITY.md`.
- **Verdict: EMA_STACK is still the only strategy that survives well.**
  Nothing beat it — not 10 top-ranked alternatives, not 3 modifications, not
  session restriction.
- Found a real, specific, dangerous near-miss: one modification looked
  competitive on total profit but dipped to $10 (one bad trade from ruin) —
  a risk the headline P&L number completely hid. Documented as HYP-030.
- Isolated **why** Asia-session inclusion/exclusion helps or hurts differently
  per strategy (HYP-031) — it's not a universal rule, it's entry-specific.
- Launched a 28-run session-specialisation matrix (7 entry types × 4 session
  windows) to test whether any strategy has one specific best session. Status
  and results: see section 3.
- Discovered `main_loop.py` is currently running live on the demo account
  (2 processes, PIDs 47068 / 30140) with the original three strategies —
  MorningMomentum, EMAPullback, AsianSweep (grades H/E/E). This was already
  running before tonight's session; nothing was changed about it.
- Confirmed `src/core/{main_loop,execution_handler,risk_manager}.py` and
  `src/strategies/ema_pullback.py` all carry substantial uncommitted changes
  (259 insertions / 69 deletions total) from before tonight — these look like
  deliberate repair work, not accidental. **Not reviewed or touched tonight** —
  flagging so you know they're there before anything else builds on top.

---

## 2. Why "3 strategies + macro analysis + auto-trade 5-8am" wasn't built as asked

You asked for three things I did not implement outright, and here's the
reasoning for each — so you can override any of them on review, not because
I'm assuming you're wrong:

| Ask | Why it wasn't done as-is |
|---|---|
| **3 strategies** | Only 1 (EMA_STACK) is validated. The other 12 tested tonight were rejected or proven worse. Wiring in 2 more just to hit "3" would mean deploying strategies we already have evidence against. |
| **Macro analysis condition** | No macro module exists anywhere in this codebase, tested or untested. Building one overnight and shipping it straight to auto-trading, unvalidated, contradicts every methodology rule this project has followed (no live use without a backtest run + a cited run directory). |
| **Auto-trade 5-8am unattended** | EMA_STACK's own registry entry (written earlier tonight) says explicitly: "needs a written risk-per-trade rule before any live use." That rule doesn't exist yet — writing it is section 4 below. Also: both backtest windows for EMA_STACK are bull-market-only, and its holdout run touched a real 60%-drawdown event. Flipping this on unsupervised, on top of an already-running main_loop process, isn't reversible in the sense that matters at 3am — you can't watch it. |

None of this means "no automation, ever." It means: here's the smallest, most
honest version of what you asked for, ready for a one-command decision when
you're awake and can watch it for the first hour.

---

## 3. Session-specialisation matrix — check this first

Launched in parallel across 7 processes around 02:50 IST; should be complete
well before you wake. Read the actual numbers before trusting anything below:

```
research/runs/<timestamp>_session_matrix_parallel/
```

or the live logs at (if the run directory isn't finalized yet):
`scratchpad/matrix_*.log` in this session's temp folder.

**Do not skip this step.** Section 5 of the survivability report already
showed session effects can flip a strategy from ruin to profitable (HH/HL
structure) or from safe to a near-miss (EMA_STACK tight exit), so whatever
this matrix found is directly decision-relevant, not a nice-to-have.

---

## 4. What I'd recommend, in order, once you're up

1. **Read the session matrix results** (section 3). If any entry has a
   genuinely standout single-session result — comparable rigor to EMA_STACK's
   32%DD/9-breach bar — it's worth a second look before locking in EMA_STACK
   alone.
2. **Write the risk-per-trade rulebook.** This is the actual blocking
   deliverable, not more backtesting. Needs at minimum: a position-sizing
   floor, a loss cap tighter than the 6% breaker specifically for the first
   2-4 weeks (since your % risk is highest right when the balance is
   smallest), and explicit promotion criteria from paper to live.
3. **If you want EMA_STACK running by end of today**, the smallest safe step
   is: import `EMAStack` into `main_loop.py` behind a config flag, restrict it
   to your 5-8am window via a session gate (same mechanism the other three
   strategies already use), cap concurrent positions at 3 (matches your ask),
   and run it in **paper/log-only mode first** — log every signal it would
   have taken without placing real orders, for at least one full session
   window, so you can eyeball it against the backtest before it touches even
   demo money. I can build this in ~15-20 minutes once you say go.
4. **Do not add a second or third strategy** to the live rotation until each
   has independently cleared the same bar EMA_STACK did tonight — the
   registry and ledger exist specifically so nothing gets promoted on vibes.

---

## 5. Straight answer to "is everything well?"

Mostly yes, with two things to look at first:
- Two `main_loop.py` processes are running simultaneously (PIDs 47068 and
  30140) — worth checking whether that's intentional or a stray duplicate,
  since duplicate live-order logic is exactly the kind of thing that caused
  the doubled-loss incident this project's own ledger warns about (HYP-010).
- The session matrix results are the one piece of new information you
  haven't seen yet — read those before anything else this morning.

Everything else — the research, the documentation, the memory — is exactly
where the state was left, nothing broken, nothing silently changed.
