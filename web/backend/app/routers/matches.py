from datetime import datetime, timezone, date
from typing import Annotated
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Match
from ..schemas import MatchOut

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("/today", response_model=list[MatchOut])
def get_today_matches(db: Annotated[Session, Depends(get_db)]):
    today = datetime.now(timezone.utc).date()
    return (
        db.query(Match)
        .filter(Match.date == today)
        .order_by(Match.match_time)
        .all()
    )


@router.get("/next", response_model=list[MatchOut])
def get_next_matches(db: Annotated[Session, Depends(get_db)]):
    today = datetime.now(timezone.utc).date()
    earliest = (
        db.query(Match.date)
        .filter(Match.date >= today)
        .order_by(Match.date)
        .first()
    )
    if not earliest:
        return []
    return (
        db.query(Match)
        .filter(Match.date == earliest[0])
        .order_by(Match.match_time)
        .all()
    )


@router.get("", response_model=list[MatchOut])
def get_matches(
    db: Annotated[Session, Depends(get_db)],
    day: int | None = Query(None),
):
    query = db.query(Match)
    if day is not None:
        query = query.filter(Match.day == day)
    return query.order_by(Match.day, Match.match_time).all()
