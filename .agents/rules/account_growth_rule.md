# Account Sizing Rule

**Superseded 2026-09-02 (rohith-2).** The earlier version of this file said the
bot used "dynamic position sizing (15% risk)" and must not be touched until
$200. That dynamic sizing was a bug: on the ~$105 account it opened 0.02-0.03
lot positions (live evidence: tickets 633818770, 633822753, 633836998) and one
losing cluster could have ended the account.

## Current rule (owner's directive, not a risk model)

- **Every order is 0.01 lots.** Enforced in `ExecutionHandler.send_order` via
  `FIXED_LOT_SIZE` — the single chokepoint. No dynamic sizing anywhere in the
  live path. `RiskManager.calculate_dynamic_lot_size` still exists but
  `main_loop` no longer calls it.
- **Total open exposure never exceeds 0.02 lots** (`MAX_TOTAL_VOLUME`), max 2
  concurrent positions.
- **Do not raise either number without an explicit new instruction from the
  owner.** These are hard limits the owner set, not tunables.

## At $200 balance

Revisit the **exposure cap** (0.02 -> maybe 0.03-0.04), NOT the per-order lot
size. The per-trade dollar risk shrinks as the balance compounds because lot
size is fixed, so there is no urgency to scale. Any change is a proposal to the
owner first, backtested on the validation window.

See [[rohith-2-live-hardening]] in agent memory and
`docs/plans/DAILY_BATTLE_PLAN.md` section 3.
