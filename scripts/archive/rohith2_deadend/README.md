# rohith-2 dead-end scripts (2026-09-03)

Every A/B test run while trying to save portfolio_v4. All confirmed the same
thing: portfolio_v4 has no out-of-sample edge (4-year holdout PF 0.965).

- `d1_gate_ab`, `direction_gate_ab`, `gate_refine_ab` -- direction-gate variants; D1 EMA20 was best, nothing beat it
- `exit_trail_ab`, `be_exit_ab` -- trailing / breakeven exits; every variant worse than fixed TP
- `confluence_ab`, `structure_screen`, `luxalgo_fvg_ab` -- SMC / structure filters; all worse or no-op
- `fvg_improve_ab` -- FVG min-gap filter; the ONE in-sample improvement (PF 1.478->1.53), moot given no OOS edge
- `live_config_ab` -- found trailing+pyramiding were live and net-negative (fixed)
- `edge_by_period`, `proximity_holdout`, `regime_filter_ab` -- the holdout tests that killed portfolio_v4

Kept for reference. The A/B *pattern* carries forward to the new system; these
specific tests do not. See docs/research/D1_SYSTEM_PLAN.md.
