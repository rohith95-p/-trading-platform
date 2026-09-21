# Ultra Core Incident Runbook

## Severity levels
- **SEV-1**: Account safety at risk (unexpected fills, breaker not halting, runaway restarts, wrong account).
- **SEV-2**: Trading degraded (data stale, strategy disabled, partial outage).
- **SEV-3**: Non-trading issue (reporting/docs only).

## Immediate actions (SEV-1/SEV-2)
1. Create `STOP` file at repository root to activate kill switch.
2. Verify all open positions are flattened; if not, flatten manually in terminal.
3. Confirm `src/core/main_loop` is halted.
4. Preserve evidence:
   - `logs/main_loop.log`
   - `logs/heartbeat`
   - `logs/loop_state.json`
   - broker terminal journal/exported deals
5. Record incident start time, account login, and impacted strategies.

## Diagnosis checklist
- Confirm runtime policy loaded from `/home/runner/work/-trading-platform/-trading-platform/config/runtime_policy.json`.
- Confirm account identity matches `resilience.EXPECTED_LOGIN`.
- Confirm breaker trigger reason (daily/weekly/monthly) from logs.
- Confirm spread and execution environment (broker status/news windows).

## Recovery checklist
1. Root cause documented in `docs/research/RESEARCH_LEDGER.md`.
2. Fix implemented and peer-reviewed in PR.
3. Regression tests pass.
4. Production validation (`python -m scripts.production_validation`) run and gates pass.
5. Remove `STOP` file only after all checks pass.

## Communication template
- Incident ID
- Start/end timestamps (UTC + IST)
- Impact summary (positions, P/L, downtime)
- Root cause
- Permanent fix
- Follow-up actions
