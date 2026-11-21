"""Position sizing accounting for contract sizes, tick values, and risk percentage."""
from dataclasses import dataclass
from app.models.domain import Instrument


@dataclass
class SizeResult:
    position_size: float
    lot_size: float
    risk_amount: float
    stop_distance: float
    r_value: float


def calculate_position_size(
    account_balance: float,
    risk_pct: float,
    entry_price: float,
    stop_loss: float,
    instrument: Instrument
) -> SizeResult:
    """
    Computes exact position size and lots based on instrument specifications.
    Standard institutional formula:
       risk_amount = account_balance * (risk_pct / 100)
       stop_dist = |entry_price - stop_loss|
       ticks = stop_dist / tick_size
       risk_per_lot = ticks * tick_value
       lots = risk_amount / risk_per_lot
    """
    if account_balance <= 0:
        raise ValueError("account_balance must be positive")
    if risk_pct <= 0:
        raise ValueError("risk_pct must be positive")

    stop_dist = abs(entry_price - stop_loss)
    if stop_dist < 1e-8:
        raise ValueError("Stop loss cannot equal entry price")

    risk_amount = account_balance * (risk_pct / 100.0)

    # Number of ticks in the stop distance
    ticks = stop_dist / max(instrument.tick_size, 1e-8)
    risk_per_lot = ticks * instrument.tick_value

    if risk_per_lot < 1e-8:
        raise ValueError("Calculated risk per lot is zero")

    raw_lots = risk_amount / risk_per_lot
    # Round to lot step
    step = instrument.lot_step
    lots = round(round(raw_lots / step) * step, 4)
    lots = max(instrument.min_lot, min(instrument.max_lot, lots))

    position_size = round(lots * instrument.contract_size, 6)
    actual_risk = lots * risk_per_lot

    return SizeResult(
        position_size=position_size,
        lot_size=lots,
        risk_amount=round(actual_risk, 2),
        stop_distance=round(stop_dist, 5),
        r_value=round(actual_risk, 2)
    )
