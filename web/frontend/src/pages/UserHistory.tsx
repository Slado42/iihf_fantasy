import { useEffect, useState } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import { getUserScores } from "../api/client";
import type { PlayerScoreDetail, UserDayScore } from "../types";

function PlayerStatsRow({ player }: { player: PlayerScoreDetail }) {
  const isGoalkeeper = player.position === "Goalkeeper";
  const hasAnyStats = player.goals !== null || player.assists !== null || player.saves !== null;

  if (!hasAnyStats) {
    return (
      <div className="text-xs text-gray-500 pl-10 pb-1 italic">No stats recorded</div>
    );
  }

  const parts: string[] = [];

  if (!isGoalkeeper) {
    if (player.goals) parts.push(`G: ${player.goals}`);
    if (player.assists) parts.push(`A: ${player.assists}`);
    if (player.ppg) parts.push(`PPG: ${player.ppg}`);
    if (player.shg) parts.push(`SHG: ${player.shg}`);
    if (player.gwg) parts.push(`GWG: ${player.gwg}`);
    if (player.pim) parts.push(`PIM: ${player.pim}`);
    if (player.plus_minus !== null && player.plus_minus !== undefined) {
      const pm = player.plus_minus;
      if (pm !== 0) parts.push(`\u00b1${pm > 0 ? "+" : ""}${pm}`);
    }
  } else {
    if (player.saves !== null && player.saves !== undefined) parts.push(`SVS: ${player.saves}`);
    if (player.goals_against !== null && player.goals_against !== undefined) parts.push(`GA: ${player.goals_against}`);
    if (player.win !== null && player.win !== undefined) parts.push(player.win ? "W" : "L");
  }

  return (
    <div className="pl-10 pb-1 flex flex-wrap items-center gap-x-3 gap-y-0.5">
      {parts.length > 0 ? (
        parts.map((part, i) => (
          <span key={i} className="text-xs text-gray-400 font-mono">{part}</span>
        ))
      ) : (
        <span className="text-xs text-gray-500 italic">No notable stats</span>
      )}
      {player.is_captain && (
        <span className="text-xs text-gold italic">\u00d72 captain bonus</span>
      )}
    </div>
  );
}

export default function UserHistory() {
  const { userId } = useParams<{ userId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const username: string = location.state?.username ?? "Player";

  const [scores, setScores] = useState<UserDayScore[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const [expandedPlayers, setExpandedPlayers] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!userId) return;
    getUserScores(userId)
      .then((res) => setScores(res.data))
      .finally(() => setLoading(false));
  }, [userId]);

  const toggle = (day: number) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(day) ? next.delete(day) : next.add(day);
      return next;
    });
  };

  const togglePlayer = (day: number, playerId: number) => {
    const key = `${day}-${playerId}`;
    setExpandedPlayers((prev) => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  };

  return (
    <div>
      <button
        onClick={() => navigate("/standings")}
        className="text-gray-400 hover:text-white text-sm mb-4 flex items-center gap-1"
      >
        ← Back to Standings
      </button>
      <h1 className="text-xl font-bold mb-4">{username}'s History</h1>
      {loading ? (
        <div className="space-y-2">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-12 bg-navy-800 rounded animate-pulse" />
          ))}
        </div>
      ) : scores.length === 0 ? (
        <p className="text-gray-400 text-sm">No scores recorded yet.</p>
      ) : (
        <div className="space-y-2">
          {scores.map((ds) => (
            <div key={ds.day} className="bg-navy-800 rounded-xl overflow-hidden">
              <button
                onClick={() => toggle(ds.day)}
                className="w-full flex items-center justify-between px-4 py-3 hover:bg-navy-700 transition-colors"
              >
                <span className="font-medium">Day {ds.day}</span>
                <div className="flex items-center gap-3">
                  <span className="text-gold font-bold">{ds.total_points.toFixed(1)} pts</span>
                  <span className="text-gray-400 text-sm">{expanded.has(ds.day) ? "\u25b2" : "\u25bc"}</span>
                </div>
              </button>

              {expanded.has(ds.day) && (
                <div className="border-t border-navy-700 px-4 py-3 space-y-1">
                  {ds.players.map((p) => {
                    const playerKey = `${ds.day}-${p.player_id}`;
                    const isPlayerExpanded = expandedPlayers.has(playerKey);
                    return (
                      <div key={p.player_id}>
                        <div
                          className="flex items-center justify-between text-sm cursor-pointer hover:bg-navy-700 rounded px-1 -mx-1 py-0.5 transition-colors"
                          onClick={() => togglePlayer(ds.day, p.player_id)}
                        >
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-gray-400 font-mono w-8">{p.team_abbr}</span>
                            <span>{p.name}</span>
                            {p.is_captain && <span className="text-gold text-xs">\u2605 CAP</span>}
                            <span className="text-xs text-gray-500">{p.position}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-gold font-semibold">{p.fantasy_points.toFixed(1)}</span>
                            <span className="text-gray-500 text-xs">{isPlayerExpanded ? "\u25b2" : "\u25bc"}</span>
                          </div>
                        </div>
                        {isPlayerExpanded && <PlayerStatsRow player={p} />}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
