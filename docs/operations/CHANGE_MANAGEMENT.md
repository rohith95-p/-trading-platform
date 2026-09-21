# Ultra Core Change Management

## Non-negotiable flow
1. Hypothesis documented in `docs/research/RESEARCH_LEDGER.md`.
2. Change implemented on branch with deterministic config updates.
3. Regression tests pass.
4. `python -m scripts.production_validation` executed.
5. Promotion gates must pass before moving from demo -> paper-forward -> small-live.

## Forbidden changes
- No live hot-patching without PR and validation evidence.
- No tuning using holdout period data.
- No markdown-only rule changes that alter runtime behavior.

## Required artifacts per release
- Updated `/home/runner/work/-trading-platform/-trading-platform/config/runtime_policy.json`
- Updated `/home/runner/work/-trading-platform/-trading-platform/config/validation_profile.json` (if validation criteria changed)
- Validation report under `research/runs/*_production_validation/report.json`
- Rollback note: previous known-good commit hash + runtime policy version
