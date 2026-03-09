import os
os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', '/opt/render/project/src')

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base, SessionLocal
from .models import Match
from .routers import auth, players, matches, lineup, scores

# Make web/backend/ importable so scraper_bridge can be imported
_backend_dir = str(Path(__file__).resolve().parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

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
    """Hourly background task: scrape stats and recalculate scores for matches 5+ hours old."""
    while True:
        try:
            from scraper_bridge import import_match_stats_to_db
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            cutoff = now - timedelta(hours=5)
            db = SessionLocal()
            try:
                # Step 1: scrape stats for unprocessed matches that started 5+ hours ago
                unprocessed = (
                    db.query(Match)
                    .filter(
                        Match.match_time <= cutoff,
                        Match.status != "completed",
                        Match.url_playbyplay.isnot(None),
                        Match.url_statistics.isnot(None),
                    )
                    .all()
                )
                for match in unprocessed:
                    try:
                        print(f"[auto-score] Scraping stats for match {match.id} (day {match.day})", flush=True)
                        await asyncio.to_thread(import_match_stats_to_db, match.id)
                    except Exception as e:
                        print(f"[auto-score] Failed to scrape match {match.id}: {e}", flush=True)

                db.expire_all()  # ensure newly committed PlayerStat rows are visible

                # Step 2: recalculate scores for all days with matches 5+ hours ago
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
    import subprocess
    subprocess.run(
        ['python', '-m', 'playwright', 'install', 'chromium'],
        capture_output=True, check=False
    )
    Base.metadata.create_all(bind=engine)
    asyncio.create_task(_auto_score_loop())


@app.get("/health")
def health():
    return {"status": "ok"}
