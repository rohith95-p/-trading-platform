"""Download XAUUSDm history from the live MT5 terminal into the research cache.

    python -m scripts.fetch_history

Writes research/data/<SYMBOL>_<TF>.npy plus a manifest carrying the content
hash, the broker server name, the contract spec and every gap found. Backtests
load only from this cache, so a result is always traceable to a specific hash.
"""

from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone

from src.backtesting.data import DATA_ROOT, fetch_and_cache

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("fetch_history")

# How far back to ask for each timeframe. MT5 serves what it has; the manifest
# records what actually arrived.
DEFAULT_SPANS = {
    "D1": datetime(2018, 1, 1, tzinfo=timezone.utc),
    "H1": datetime(2020, 1, 1, tzinfo=timezone.utc),
    "M15": datetime(2022, 1, 1, tzinfo=timezone.utc),
    "M5": datetime(2024, 1, 1, tzinfo=timezone.utc),
    "M1": datetime(2025, 1, 1, tzinfo=timezone.utc),
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="XAUUSDm")
    ap.add_argument("--timeframes", nargs="*", default=["D1", "M15", "M5", "M1"])
    ap.add_argument("--data-root", default=DATA_ROOT)
    args = ap.parse_args()

    for tf in args.timeframes:
        start = DEFAULT_SPANS.get(tf, datetime(2022, 1, 1, tzinfo=timezone.utc))
        try:
            rates, mf = fetch_and_cache(args.symbol, tf, start, data_root=args.data_root)
        except Exception as exc:
            log.error("%s %s failed: %s", args.symbol, tf, exc)
            continue
        weekend = sum(1 for g in mf.gaps if g["weekend"])
        log.info(
            "%-4s %7d bars  %s -> %s  sha=%s  gaps=%d (%d weekend)  zero-vol=%d",
            tf, mf.bars, mf.first_time, mf.last_time, mf.sha256[:12],
            len(mf.gaps), weekend, mf.zero_volume_bars,
        )


if __name__ == "__main__":
    main()
