"""Strategy parameter optimization engine."""
import itertools
from typing import Dict, Any, List
import pandas as pd
from app.models.domain import BacktestConfig
from app.backtesting.engine import BacktestEngine
from app.models.schemas import OptimizationTrialResult, OptimizationResultsResponse


def generate_param_combinations(param_space: Dict[str, Any]) -> List[Dict[str, Any]]:
    keys = list(param_space.keys())
    value_lists = []
    for k in keys:
        spec = param_space[k]
        if isinstance(spec, list):
            value_lists.append(spec)
        elif isinstance(spec, dict) and "min" in spec and "max" in spec:
            step = spec.get("step", 1)
            val = spec["min"]
            vals = []
            while val <= spec["max"]:
                vals.append(val)
                val += step
            value_lists.append(vals)
        else:
            value_lists.append([spec])

    combos = []
    for product in itertools.product(*value_lists):
        combos.append(dict(zip(keys, product)))
    return combos


def run_grid_search(
    base_config: BacktestConfig,
    df: pd.DataFrame,
    strategy_cls: type,
    param_space: Dict[str, Any],
    objective_metric: str = "profit_factor",
    max_trials: int = 50
) -> List[OptimizationTrialResult]:
    combinations = generate_param_combinations(param_space)[:max_trials]
    results = []

    for idx, params in enumerate(combinations, start=1):
        strat = strategy_cls(params)
        engine = BacktestEngine(base_config, df, strat)
        res = engine.run()

        score = 0.0
        if res.metrics:
            if objective_metric == "profit_factor":
                score = res.metrics.profit_factor
            elif objective_metric == "sharpe_ratio":
                score = res.metrics.sharpe_ratio
            elif objective_metric == "net_return_pct":
                score = res.metrics.net_return_pct
            elif objective_metric == "win_rate":
                score = res.metrics.win_rate

        results.append(OptimizationTrialResult(
            trial_number=idx,
            parameters=params,
            metrics=res.metrics,
            score=round(float(score), 4)
        ))

    results.sort(key=lambda x: x.score, reverse=True)
    return results
