"""Chart data generators for UI and API."""
from typing import List, Dict, Any
import numpy as np
from app.models.domain import Trade


def generate_equity_curve(trades: List[Trade], initial_capital: float) -> List[Dict[str, Any]]:
    points = [{"timestamp": "Start", "equity": initial_capital}]
    running = initial_capital
    for t in sorted(trades, key=lambda x: x.exit_time or x.entry_time):
        running += t.net_pnl
        ts_str = t.exit_time.isoformat() if t.exit_time else t.entry_time.isoformat()
        points.append({
            "timestamp": ts_str,
            "equity": round(running, 2)
        })
    return points


def generate_drawdown_curve(equity_points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    points = []
    peak = 0.0
    for pt in equity_points:
        eq = pt["equity"]
        peak = max(peak, eq)
        dd_pct = round(((peak - eq) / max(peak, 1e-6)) * 100.0, 2)
        points.append({
            "timestamp": pt["timestamp"],
            "drawdown_pct": dd_pct
        })
    return points


def generate_monthly_returns(trades: List[Trade], initial_capital: float) -> List[Dict[str, Any]]:
    monthly: Dict[str, float] = {}
    for t in trades:
        ts = t.exit_time or t.entry_time
        k = ts.strftime("%Y-%m")
        monthly[k] = monthly.get(k, 0.0) + t.net_pnl

    results = []
    for m, pnl in sorted(monthly.items()):
        results.append({
            "month": m,
            "pnl": round(pnl, 2),
            "return_pct": round((pnl / initial_capital) * 100.0, 2)
        })
    return results


def generate_r_distribution(trades: List[Trade]) -> List[Dict[str, Any]]:
    buckets = {"<-2R": 0, "-2R to -1R": 0, "-1R to 0R": 0, "0R to 1R": 0, "1R to 2R": 0, "2R to 3R": 0, ">3R": 0}
    for t in trades:
        r = t.r_multiple if t.r_multiple is not None else 0.0
        if r < -2.0:
            buckets["<-2R"] += 1
        elif r < -1.0:
            buckets["-2R to -1R"] += 1
        elif r < 0.0:
            buckets["-1R to 0R"] += 1
        elif r < 1.0:
            buckets["0R to 1R"] += 1
        elif r < 2.0:
            buckets["1R to 2R"] += 1
        elif r < 3.0:
            buckets["2R to 3R"] += 1
        else:
            buckets[">3R"] += 1

    return [{"bucket": k, "count": v} for k, v in buckets.items()]
