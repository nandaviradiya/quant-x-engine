"""Risk configuration and position sizing API."""
from fastapi import APIRouter, HTTPException
from app.models.schemas import RiskConfigSchema, PositionSizeRequest, PositionSizeResponse
from app.risk.sizing import calculate_position_size
from app.backtesting.engine import INSTRUMENTS_SPEC

router = APIRouter(prefix="/risk")
current_risk_config = RiskConfigSchema()


@router.get("/config", response_model=RiskConfigSchema)
async def get_risk_config():
    return current_risk_config


@router.put("/config", response_model=RiskConfigSchema)
async def update_risk_config(config: RiskConfigSchema):
    global current_risk_config
    current_risk_config = config
    return current_risk_config


@router.post("/calculate-size", response_model=PositionSizeResponse)
async def calculate_size(req: PositionSizeRequest):
    ins = INSTRUMENTS_SPEC.get(req.symbol.upper())
    if not ins:
        raise HTTPException(status_code=400, detail=f"Unknown instrument {req.symbol}")

    try:
        res = calculate_position_size(
            account_balance=req.account_balance,
            risk_pct=req.risk_pct,
            entry_price=req.entry_price,
            stop_loss=req.stop_loss,
            instrument=ins
        )
        return PositionSizeResponse(
            position_size=res.position_size,
            lot_size=res.lot_size,
            risk_amount=res.risk_amount,
            stop_distance=res.stop_distance,
            r_value=res.r_value
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
