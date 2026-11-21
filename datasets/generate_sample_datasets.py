"""Generate realistic historical market datasets — HF Spaces self-contained version."""
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# Output directory: /app/datasets inside the container
DATASETS_DIR = Path(os.environ.get("PARQUET_DATA_DIR", "/app/datasets"))

INSTRUMENTS = [
    {"symbol": "BTCUSD",  "market": "crypto",  "base_price": 50000.0, "volatility": 0.003,  "spread": 1.0,  "is_24_7": True,  "timeframes": ["H1", "M15"]},
    {"symbol": "ETHUSD",  "market": "crypto",  "base_price": 3000.0,  "volatility": 0.0035, "spread": 0.2,  "is_24_7": True,  "timeframes": ["H1", "M15"]},
    {"symbol": "SOLUSD",  "market": "crypto",  "base_price": 140.0,   "volatility": 0.005,  "spread": 0.05, "is_24_7": True,  "timeframes": ["H1", "M15"]},
    {"symbol": "XAUUSD",  "market": "metals",  "base_price": 2050.0,  "volatility": 0.0015, "spread": 0.3,  "is_24_7": False, "timeframes": ["H1", "M15"]},
    {"symbol": "XAGUSD",  "market": "metals",  "base_price": 25.50,   "volatility": 0.002,  "spread": 0.02, "is_24_7": False, "timeframes": ["H1", "M15"]},
]

TF_MINUTES = {"M15": 15, "H1": 60}


def generate_series(symbol, start_dt, n_bars, base_price, vol, spread, is_24_7, minutes):
    timestamps = []
    curr = start_dt
    while len(timestamps) < n_bars:
        if not is_24_7:
            if curr.weekday() == 5 or (curr.weekday() == 6 and curr.hour < 22):
                curr += timedelta(minutes=minutes)
                continue
        timestamps.append(curr)
        curr += timedelta(minutes=minutes)

    np.random.seed(42 + hash(symbol) % 1000)
    returns = np.random.normal(0.0001, vol, len(timestamps))
    price_path = base_price * np.exp(np.cumsum(returns))

    rows = []
    for i, p in enumerate(price_path):
        o = p
        ret = np.random.normal(0, vol * 0.7)
        c = o * (1.0 + ret)
        intra_noise = vol * np.random.uniform(0.5, 1.8)
        h = max(o, c) * (1.0 + abs(np.random.normal(0, intra_noise)))
        lo = min(o, c) * (1.0 - abs(np.random.normal(0, intra_noise)))
        v = float(np.random.lognormal(mean=5, sigma=1))
        half_sp = spread / 2.0
        rows.append({
            "timestamp": timestamps[i],
            "open":   round(o, 4),
            "high":   round(h, 4),
            "low":    round(lo, 4),
            "close":  round(c, 4),
            "volume": round(v, 2),
            "bid":    round(c - half_sp, 4),
            "ask":    round(c + half_sp, 4),
            "spread": round(spread, 4),
        })
    return pd.DataFrame(rows)


def save_parquet(df: pd.DataFrame, out_dir: Path, symbol: str, timeframe: str):
    dest = out_dir / symbol / timeframe
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / "data.parquet"
    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(table, str(path), compression="snappy")
    return path


def main():
    print(f"Generating QUANT-X datasets -> {DATASETS_DIR}")
    DATASETS_DIR.mkdir(parents=True, exist_ok=True)
    start_dt = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)

    for item in INSTRUMENTS:
        sym = item["symbol"]
        market = item["market"]
        market_dir = DATASETS_DIR / market
        market_dir.mkdir(parents=True, exist_ok=True)

        for tf in item["timeframes"]:
            mins = TF_MINUTES[tf]
            n_bars = 2500 if tf == "H1" else 5000
            print(f"  -> {sym} [{tf}] {n_bars} bars ...")

            df = generate_series(
                symbol=sym, start_dt=start_dt, n_bars=n_bars,
                base_price=item["base_price"], vol=item["volatility"],
                spread=item["spread"], is_24_7=item["is_24_7"], minutes=mins
            )

            # Save CSV
            csv_path = market_dir / sym / f"{tf}.csv"
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(csv_path, index=False)

            # Save Parquet (flat structure at DATASETS_DIR level)
            parquet_path = save_parquet(df, DATASETS_DIR, sym, tf)
            print(f"     {len(df)} candles -> {parquet_path}")

    print("\nAll datasets generated successfully!")


if __name__ == "__main__":
    main()
