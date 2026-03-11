from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Player, Match, DailyLineup, User
from ..auth import get_current_user
from ..schemas import PlayerOut

router = APIRouter(prefix="/players", tags=["players"])


@router.get("", response_model=list[PlayerOut])
def get_players(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    position: str | None = Query(None),
    team: str | None = Query(None),
    day: int | None = Query(None),
):
    query = db.query(Player)
    if position:
        query = query.filter(Player.position == position)
    if team:
        query = query.filter(Player.team_abbr == team)

    locked_teams: set[str] = set()
    playing_teams: set[str] | None = None
    stage = "group"
    usage_limit = 3
    picks_dict: dict[int, int] = {}
    if day is not None:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        playing_teams = set()
        for m in db.query(Match).filter(Match.day == day).all():
            playing_teams.add(m.home_team)
            playing_teams.add(m.away_team)
            if m.match_time <= now:
                locked_teams.add(m.home_team)
                locked_teams.add(m.away_team)
            stage = m.stage  # all matches on same day share the same stage

        usage_limit = 3 if stage == "group" else 1
        # Use a subquery to avoid JOIN fan-out (multiple matches per day × lineup entries)
        stage_days = db.query(Match.day).filter(Match.stage == stage).distinct()
        rows = (
            db.query(DailyLineup.player_id, func.count(DailyLineup.player_id).label("cnt"))
            .filter(
                DailyLineup.user_id == current_user.id,
                DailyLineup.day != day,
                DailyLineup.day.in_(stage_days),
            )
            .group_by(DailyLineup.player_id)
            .all()
        )
        picks_dict = {row.player_id: row.cnt for row in rows}

    result = []
    for p in query.order_by(Player.team_abbr, Player.name).all():
        out = PlayerOut.model_validate(p)
        out.is_locked = p.team_abbr in locked_teams
        out.has_match = playing_teams is None or p.team_abbr in playing_teams
        out.picks_used = picks_dict.get(p.id, 0)
        out.picks_limit = usage_limit
        result.append(out)
    return result
