---
# QUANT-X Algorithm Engine — Render.com Deployment

**Multi-Asset Algorithmic Trading & Backtesting API**

A production-grade quantitative research engine supporting 5 instruments and 6 trading strategies.

## Supported Instruments
- **Crypto**: BTCUSD, ETHUSD, SOLUSD
- **Metals**: XAUUSD, XAGUSD

## Strategies
1. EMA Trend Pullback + Breakout (BTCUSD, ETHUSD)
2. Market Structure Shift — BOS/MSS (ETHUSD, BTCUSD)
3. Volatility Breakout + Retest (SOLUSD)
4. Gold EMA + VWAP Trend Pullback (XAUUSD)
5. Silver Range Breakout + Retest (XAGUSD)
6. Universal Liquidity Sweep (all 5 assets)

## API Documentation
Visit `/docs` for the interactive Swagger UI after deployment.

## Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Engine health & version |
| GET | `/api/v1/strategies` | List all strategies |
| GET | `/api/v1/data/instruments` | Supported instruments |
| POST | `/api/v1/backtest/run` | Run a backtest |
| GET | `/api/v1/analytics/compare` | Compare strategy results |
| WS | `/ws/backtest/{job_id}` | Live backtest progress |

## Deployment
Deployed on [Render.com](https://render.com) free tier using Docker.
