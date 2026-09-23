---
name: agy-audit-lookahead
description: "Static code analysis workflow to identify and prevent lookahead bias in vectorized Pandas trading strategies."
---

# Lookahead Bias Auditor Skill

## Context
In the `ultra_core` repository, strategies are evaluated using a custom vectorized Pandas engine (`src/research/market_study.py`, `src/strategies/`). The single most fatal flaw in backtesting is **lookahead bias**—where a trading decision at time $t$ relies on data that is only available at time $t+1$ or later. This skill provides a rigorous checklist to manually or programmatically audit new strategies for this flaw before they are merged.

## Instructions
When asked to "audit for lookahead", "check for lookahead bias", or "review this strategy for safety", follow these steps:

### 1. Identify Target Files
- Target any files modified recently in `src/strategies/` or `src/research/`.
- Look specifically for classes inheriting from `_Strategy` or `_SessionSpecialist`, and functions returning numpy arrays (like `_c_fvg`).

### 2. The Vector Audit (Regex & Syntax Checks)
1. Use `grep_search` to find all occurrences of array indexing in the target files: `grep_search(Query: "\[i.*?\]", SearchPath: "<file>")`
2. **Rule 1 (The Open Bar Rule):** In `ultra_core`, trading decisions at bar `i` are made at the *open* of bar `i`. Therefore, `close[i]`, `high[i]`, and `low[i]` DO NOT YET EXIST. 
   - *Valid:* `close[i-1]`, `high[i-2]`, `low[i-1]`
   - *Invalid:* `close[i]`, `high[i]`, `low[i]`. If you see `f["close"][i]`, this is a fatal lookahead bias.
3. **Rule 2 (The Shift Rule):** When using vectorized `np.where` or `_shift` functions:
   - *Valid:* `_shift(f["close"], 1)` (Shifting by 1 means the value at index `i` is actually `close[i-1]`).
   - *Invalid:* Using unshifted arrays (e.g., `bull = f["high"] > f["low"]`) directly in a signal that evaluates at index `i`.

### 3. The Resolution Report
- Create an artifact named `lookahead_audit_report.md`.
- List the files audited.
- Highlight any code blocks that violate Rule 1 or Rule 2.
- Provide the corrected code block using GitHub markdown diffs, explicitly replacing the current-bar index with the previous-bar index (e.g. replacing `[i]` with `[i-1]`).
- If the code is perfectly clean, explicitly declare: `✅ No lookahead bias detected. Vector indexing strictly respects historical boundaries.`
