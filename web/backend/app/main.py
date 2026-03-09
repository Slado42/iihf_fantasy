import asyncio
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base, SessionLocal
from .models import Match
from .routers import auth, players, matches, lineup, scores

app = FastAPI(title="IIHF Fantasy Hockey API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(players.router)
app.include_router(matches.router)
app.include_router(lineup.router)
app.include_router(scores.router)


async def _auto_score_loop():
    """Hourly background task: recalculate scores for any day whose matches started 5+ hours ago."""
    while True:
        try:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            cutoff = now - timedelta(hours=5)
            db = SessionLocal()
            try:
                days = {
                    m.day
                    for m in db.query(Match).filter(Match.match_time <= cutoff).all()
                }
                for day in sorted(days):
                    scores._calculate_day_scores(day, db)
                    print(f"[auto-score] Recalculated scores for day {day}", flush=True)
            except Exception as e:
                print(f"[auto-score] Error: {e}", flush=True)
            finally:
                db.close()
        except Exception as e:
            print(f"[auto-score] Unexpected error: {e}", flush=True)
        await asyncio.sleep(3600)  # run every hour


@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)
    asyncio.create_task(_auto_score_loop())


@app.get("/health")
def health():
    return {"status": "ok"}
