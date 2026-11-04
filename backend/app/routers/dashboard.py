"""Dashboard endpoints. Every logged-in user may read them; all accept an optional ?type= filter."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.schemas.dashboard import (
    AttentionItem,
    DashboardParams,
    DashboardSummary,
    StateBreakdown,
    TrendPoint,
    TypeBreakdown,
)
from app.services import dashboard_service

# Logging in is required for every endpoint in this router.
router = APIRouter(prefix="/dashboard", tags=["dashboard"], dependencies=[Depends(get_current_user)])

Params = Annotated[DashboardParams, Query()]


@router.get("/summary", response_model=DashboardSummary)
def summary(params: Params, db: Session = Depends(get_db)) -> DashboardSummary:
    return dashboard_service.summary(db, params.type)


@router.get("/by-type", response_model=list[TypeBreakdown])
def by_type(params: Params, db: Session = Depends(get_db)) -> list[TypeBreakdown]:
    return dashboard_service.by_type(db, params.type)


@router.get("/by-state", response_model=list[StateBreakdown])
def by_state(params: Params, db: Session = Depends(get_db)) -> list[StateBreakdown]:
    return dashboard_service.by_state(db, params.type)


@router.get("/trend", response_model=list[TrendPoint])
def trend(params: Params, db: Session = Depends(get_db)) -> list[TrendPoint]:
    return dashboard_service.trend(db, params.type)


@router.get("/attention", response_model=list[AttentionItem])
def attention(params: Params, db: Session = Depends(get_db)) -> list[AttentionItem]:
    return dashboard_service.attention(db, params.type)
