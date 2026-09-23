---
name: agy-parameter-sweep
description: "Automate testing of multiple parameters (e.g. SL, TP, gap size) across the ultra_core backtest engine and generate a comparative markdown report."
---

# Parameter Sweep Automation Skill

## Context
When performing research in the `ultra_core` repository, you frequently need to test a strategy across a range of parameters (e.g., changing `tp_atr_mult` from 2.0 to 4.0). Doing this manually is slow and error-prone. This skill automates the workflow.

## Instructions
When the user asks you to sweep a parameter or find the optimal value for a strategy setting, follow these exact steps:

1. **Understand the Target:** Identify the strategy file (usually in `src/strategies/` or `src/research/candidates.py`) and the parameter the user wants to test.
2. **Stash Unrelated Changes:** If there are unrelated uncommitted changes in the repository, stash them temporarily (`git stash push <files>`) to ensure a clean testing environment.
3. **Write the Sweep Script:** Create a temporary python script (e.g., `scratch_sweep.py`) in the root directory. 
   - Import the strategy and the `run_window`, `stats`, `live_config` methods from `scripts.validation.part1_suite`.
   - Iterate over the requested parameter range (e.g., `for tp in [2.5, 3.0, 3.5, 4.0]:`).
   - Inside the loop, dynamically update the strategy class attribute or redefine it.
   - Run the backtest using `run_window(bars, live_config(), start_date, end_date, [ModifiedStrategy])`.
   - Collect the results (`n` trades, `profit_factor`, `max_drawdown_pct`, `win_rate`, `net`).
4. **Execute:** Run the script synchronously. Ensure `$env:PYTHONPATH="c:\projects\ultra_core"` is set in Windows PowerShell.
5. **Format the Output:** Take the results and generate a formatted GitHub Markdown table. 
   - Highlight the "best" result based on Profit Factor and Max Drawdown.
   - Example columns: `Parameter Value`, `Trades`, `Win Rate`, `Profit Factor`, `Max Drawdown`, `Net P&L`.
6. **Persist the Results:** If the user requested an official record, append the table to `docs/research/RESEARCH_LEDGER.md`. Otherwise, output it in a markdown artifact for the user to review.
7. **Cleanup:** Delete the temporary script (`scratch_sweep.py`) and restore any stashed changes (`git stash pop`).

## Important Rules
- Do NOT modify the core strategy files during a sweep to avoid caching hash mismatches or leaving the repo in a broken state. Always monkey-patch the class dynamically in the temporary script.
- Always use the `part1_suite` infrastructure to fetch bars, as it guarantees you are testing with the exact same data layout as the live engine.
