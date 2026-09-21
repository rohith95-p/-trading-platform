"""Versioned runtime policy loader for live controls.

This replaces markdown-parsed control logic with deterministic structured config.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any, Dict, List


DEFAULT_POLICY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "config",
    "runtime_policy.json",
)


@dataclass(frozen=True)
class StageLimits:
    name: str
    min_balance: float
    max_balance: float
    lot_size: float
    max_concurrent_positions: int
    max_same_direction_positions: int
    max_total_volume: float

    def contains(self, balance: float) -> bool:
        return self.min_balance <= balance <= self.max_balance


class RuntimePolicy:
    def __init__(self, raw: Dict[str, Any]):
        self.raw = raw
        self.version = int(raw.get("version", 1))
        self.macro = raw.get("macro", {})
        self.breakers = raw.get("breakers", {})
        self.operations = raw.get("operations", {})

        promo = raw.get("promotion", {})
        self.default_stage_name = str(promo.get("default_stage", "demo"))
        self.stages: List[StageLimits] = [
            StageLimits(
                name=str(s["name"]),
                min_balance=float(s["min_balance"]),
                max_balance=float(s["max_balance"]),
                lot_size=float(s["lot_size"]),
                max_concurrent_positions=int(s["max_concurrent_positions"]),
                max_same_direction_positions=int(s["max_same_direction_positions"]),
                max_total_volume=float(s["max_total_volume"]),
            )
            for s in promo.get("stages", [])
        ]

    def strict_short_stops(self) -> bool:
        return bool(self.macro.get("strict_short_stops", False))

    def daily_loss_pct(self, default: float) -> float:
        return float(self.breakers.get("daily_loss_pct", default))

    def weekly_loss_pct(self) -> float:
        return float(self.breakers.get("weekly_loss_pct", 0.15))

    def monthly_loss_pct(self) -> float:
        return float(self.breakers.get("monthly_loss_pct", 0.25))

    def stage_for_balance(self, balance: float) -> StageLimits:
        for s in self.stages:
            if s.contains(balance):
                return s
        # Fallback to named default stage, then last configured stage.
        for s in self.stages:
            if s.name == self.default_stage_name:
                return s
        if self.stages:
            return self.stages[-1]
        return StageLimits(
            name="fallback",
            min_balance=0.0,
            max_balance=1e12,
            lot_size=0.01,
            max_concurrent_positions=2,
            max_same_direction_positions=2,
            max_total_volume=0.02,
        )


def load_runtime_policy(path: str | None = None) -> RuntimePolicy:
    path = path or os.getenv("ULTRA_CORE_RUNTIME_POLICY") or DEFAULT_POLICY_PATH
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return RuntimePolicy(raw)
