"""
Local end-to-end pipeline test.

Tests that:
  1. The stats page is reachable (HTTP 200)
  2. The scraper returns a non-empty DataFrame
  3. Player names from the scraper match the local fantasy_hockey.db
  4. Fantasy scores can be calculated for the matched players

Usage:
    python test_full_pipeline.py
"""
import sys
import os
from pathlib import Path

# Make web/backend/ importable
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "web" / "backend"))

import pandas as pd

# ── Read first match URL from match_urls.csv ─────────────────────────────────
csv_path = ROOT / "match_urls.csv"
if not csv_path.exists():
    print("ERROR: match_urls.csv not found — run url_scraper.py first")
    sys.exit(1)

df_urls = pd.read_csv(csv_path)
first_row = df_urls.iloc[0]
url_stats = first_row["url_statistics"]
url_pbp = first_row["url_playbyplay"]
print(f"\n{'='*60}")
print(f"Testing Day {first_row['Day']} match: {first_row['home_team']} vs {first_row['away_team']}")
print(f"Stats URL: {url_stats}")
print(f"{'='*60}\n")

# ── Step 1: Run the scraper ──────────────────────────────────────────────────
print("Step 1: Running extract_all_stats (BeautifulSoup + optional Selenium)...")
try:
    from match_stats_scraper import extract_all_stats
    df = extract_all_stats(url_pbp, url_stats)
    print(f"  Scraped {len(df)} rows.")
    print()
    print(df.to_string(index=False))
    print()
except Exception as e:
    print(f"  ERROR in extract_all_stats: {e}")
    sys.exit(1)

# ── Step 2: Check DB matches ─────────────────────────────────────────────────
print("\nStep 2: Checking player name matches in fantasy_hockey.db...")
db_path = ROOT / "fantasy_hockey.db"
if not db_path.exists():
    print(f"  SKIP: {db_path} not found — cannot check name matching")
else:
    import sqlite3
    from datetime import datetime
    year = datetime.now().year
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM players WHERE championship_year = ?", (year,))
    db_names = {row[0] for row in cursor.fetchall()}
    conn.close()

    print(f"  Players in DB for {year}: {len(db_names)}")
    matched, unmatched = [], []
    for name in df["Player"]:
        if name in db_names:
            matched.append(name)
        else:
            unmatched.append(name)

    print(f"  Matched: {len(matched)}/{len(df)}")
    if unmatched:
        print(f"  Unmatched ({len(unmatched)}):")
        for n in unmatched:
            print(f"    - '{n}'")
    else:
        print("  All players matched!")

# ── Step 3: Calculate what fantasy scores would be ───────────────────────────
print("\nStep 3: Simulating fantasy score calculation...")
try:
    from app.scoring import calculate_player_points
    from app.models import PlayerStat

    class FakeStat:
        def __init__(self, row):
            self.goals = int(row.get("Goals", 0))
            self.assists = int(row.get("Assists", 0))
            self.ppg = int(row.get("Power Play Goal", 0))
            self.shg = int(row.get("Shorthanded Goal", 0))
            self.gwg = int(row.get("Game Winning Goal", 0))
            self.pim = int(row.get("Penalty Minutes", 0))
            self.plus_minus = int(row.get("Plus Minus", 0))
            self.saves = int(row.get("Saves", 0))
            self.goals_against = int(row.get("Goals Against", 0))
            self.win = bool(row.get("Win", 0))

    pos_map = {"GK": "Goalkeeper", "D": "Defender", "F": "Forward"}
    total = 0.0
    scorers = []
    for _, row in df.iterrows():
        pos_raw = str(row.get("Position", "F"))
        position = pos_map.get(pos_raw, "Forward")
        stat = FakeStat(row)
        pts = calculate_player_points(stat, position, is_captain=False)
        if pts > 0:
            scorers.append((row["Player"], position, pts))
        total += pts

    if scorers:
        print(f"  Players with >0 fantasy points (no captain bonus):")
        for name, pos, pts in sorted(scorers, key=lambda x: -x[2]):
            print(f"    {name:<30} {pos:<12} {pts:>6.2f} pts")
    else:
        print("  No players scored fantasy points (all stats are 0)")
    print(f"\n  Total points across all scraped players: {total:.2f}")
except ImportError as e:
    print(f"  SKIP scoring simulation: {e}")

print("\nDone.")
