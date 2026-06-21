"""
Monte Carlo simulation engine for MLB DFS projections.
Models each plate appearance using player stats vs. pitcher quality,
park factors, and handedness splits. Runs N simulations per player
to generate a mean DK points projection and variance.

DraftKings MLB Scoring:
  Single: 3pts  Double: 5pts  Triple: 8pts  HR: 10pts
  RBI: 2pts     Run: 2pts     BB: 2pts      SB: 5pts
  HBP: 2pts     K (batter): -0.5pts
"""

import numpy as np
from slate_data import PITCHERS, HITTERS, PARK_FACTORS, IMPLIED_TOTALS, GAMES

RNG = np.random.default_rng(42)

# DK scoring weights
DK = {
    "1B": 3.0, "2B": 5.0, "3B": 8.0, "HR": 10.0,
    "RBI": 2.0, "R": 2.0, "BB": 2.0, "SB": 5.0,
    "HBP": 2.0, "K": -0.5,
}

# Average PA per game for hitters in different lineup spots
AVG_PA = 4.1  # lineup-spot-adjusted mean


def pitcher_quality_factor(era: float, k9: float, bb9: float) -> float:
    """Convert SP stats to a multiplier on batter outcomes (lower = harder)."""
    era_factor  = np.clip(era  / 4.00, 0.65, 1.40)
    k9_factor   = np.clip(k9   / 8.50, 0.85, 1.25)
    bb9_factor  = np.clip(bb9  / 3.00, 0.85, 1.15)
    return era_factor / k9_factor * bb9_factor


def handedness_split(batter_hand: str, pitcher_hand: str) -> float:
    """Return a wOBA multiplier for platoon advantage."""
    if batter_hand == "S":
        return 1.03  # switch hitters slight boost
    if batter_hand != pitcher_hand:
        return 1.06  # platoon advantage
    return 0.96      # same hand disadvantage


def sim_plate_appearance(
    avg: float, obp: float, slg: float, hr_rate: float, k_pct: float,
    pf_run: float, pf_hr: float, pqf: float, plat: float,
) -> dict:
    """Simulate one plate appearance. Returns hit type string."""
    adj_obp    = np.clip(obp * pqf * plat, 0.10, 0.60)
    adj_slg    = np.clip(slg * pqf * plat * pf_run, 0.15, 0.90)
    adj_hr     = np.clip(hr_rate * pqf * plat * pf_hr, 0.001, 0.18)
    adj_k      = np.clip(k_pct / pqf, 0.05, 0.45)
    adj_bb     = np.clip((obp - avg) * pqf, 0.03, 0.20)

    r = RNG.random()

    if r < adj_k:
        return "K"
    if r < adj_k + adj_bb:
        return "BB"
    if r < adj_k + adj_bb + adj_hr * pf_hr:
        return "HR"

    on_base_p = adj_obp - adj_bb - adj_hr
    if r < adj_k + adj_bb + adj_hr + max(on_base_p, 0):
        # Hit — distribute between 1B, 2B, 3B based on SLG ratio
        iso = adj_slg - avg
        xbh_rate = np.clip(iso / 1.8, 0.01, 0.25)
        triple_p = 0.02
        double_p = np.clip(xbh_rate - triple_p, 0.01, 0.22)
        r2 = RNG.random()
        if r2 < triple_p:
            return "3B"
        if r2 < triple_p + double_p:
            return "2B"
        return "1B"

    return "OUT"


def simulate_player(
    player: dict,
    pitcher: dict,
    n_sims: int = 5000,
) -> dict:
    """
    Run n_sims plate appearance sequences for one hitter.
    Returns mean DK points projection, std dev, and percentile breakdown.
    """
    pqf  = pitcher_quality_factor(pitcher["era"], pitcher["k9"], pitcher["bb9"])
    plat = handedness_split(player["hand"], pitcher["hand"])
    home = pitcher["team"] == player["opp"]  # player is away if pitcher is home
    park = player["opp"] if not home else pitcher["team"]
    pf_run, pf_hr = PARK_FACTORS.get(park, (1.0, 1.0))

    # Stolen base expectation (simple proxy: fast players steal more)
    sb_per_game = 0.08 if player["slg"] < 0.430 and player["obp"] > 0.330 else 0.04

    scores = []
    for _ in range(n_sims):
        pa   = int(RNG.normal(AVG_PA, 0.5))
        pa   = max(2, min(pa, 6))
        pts  = 0.0
        hits = 0
        for _ in range(pa):
            result = sim_plate_appearance(
                player["avg"], player["obp"], player["slg"],
                player["hr_rate"], player["k_pct"],
                pf_run, pf_hr, pqf, plat,
            )
            pts += DK.get(result, 0.0)
            if result in ("1B", "2B", "3B", "HR"):
                hits += 1
                # RBI/Run simulation (simplified: 25% run, 20% rbi per hit)
                pts += DK["R"]   * (1 if RNG.random() < 0.25 else 0)
                pts += DK["RBI"] * (1 if RNG.random() < 0.20 else 0)
                if result == "HR":
                    pts += DK["RBI"]  # solo HR minimum
                    pts += DK["R"]
        # Stolen base
        if RNG.random() < sb_per_game:
            pts += DK["SB"]
        scores.append(pts)

    arr = np.array(scores)
    return {
        "projection": round(float(arr.mean()), 2),
        "std":        round(float(arr.std()),  2),
        "p25":        round(float(np.percentile(arr, 25)), 2),
        "p75":        round(float(np.percentile(arr, 75)), 2),
        "p90":        round(float(np.percentile(arr, 90)), 2),
        "ceil":       round(float(arr.max()), 2),
    }


def simulate_pitcher(p: dict, opp_team: str, n_sims: int = 5000) -> dict:
    """
    Simulate SP DK points.
    DK SP scoring: IP*2.25 + K*2 + W*4 - ER*2 - H*0.6 - BB*0.6
    Bonus: 1–9K = +0.5/K, ≥10K = +1/K (simplified as flat bonus)
    """
    opp_total = IMPLIED_TOTALS.get(opp_team, 4.5)
    scores = []
    for _ in range(n_sims):
        ip  = np.clip(RNG.normal(p["ip_proj"], 0.8), 1.0, 9.0)
        k   = np.clip(RNG.poisson(p["k9"] * ip / 9.0), 0, 16)
        bb  = np.clip(RNG.poisson(p["bb9"] * ip / 9.0), 0, 8)
        h   = np.clip(RNG.poisson(opp_total * 0.9 * (9.0 / max(ip, 1))), 0, 15)
        er  = np.clip(RNG.poisson(p["era"] * ip / 9.0), 0, 10)
        win = 1 if ip >= 5.0 and RNG.random() < 0.50 else 0

        pts = (ip * 2.25) + (k * 2.0) + (win * 4.0) - (er * 2.0) - (h * 0.6) - (bb * 0.6)
        # K bonus
        if k >= 10:
            pts += k * 1.0
        elif k >= 1:
            pts += k * 0.5
        scores.append(max(pts, -5.0))

    arr = np.array(scores)
    return {
        "projection": round(float(arr.mean()), 2),
        "std":        round(float(arr.std()),  2),
        "p25":        round(float(np.percentile(arr, 25)), 2),
        "p75":        round(float(np.percentile(arr, 75)), 2),
        "p90":        round(float(np.percentile(arr, 90)), 2),
        "ceil":       round(float(arr.max()), 2),
    }


def build_pitcher_lookup() -> dict:
    """Index pitchers by team for quick opponent lookup."""
    lookup = {}
    for row in PITCHERS:
        name, team, opp, sal, era, k9, bb9, ip_proj, hand = row
        lookup[team] = {
            "name": name, "team": team, "opp": opp,
            "salary": sal, "era": era, "k9": k9, "bb9": bb9,
            "ip_proj": ip_proj, "hand": hand, "position": "SP",
        }
    return lookup


def run_all_simulations(n_sims: int = 10000) -> list[dict]:
    """
    Simulate every player on the slate. Returns a list of player dicts
    enriched with projection stats, ready for the optimizer.
    """
    pitcher_lookup = build_pitcher_lookup()
    results = []

    print(f"Running {n_sims:,} simulations per player...")

    # Pitchers
    for row in PITCHERS:
        name, team, opp, sal, era, k9, bb9, ip_proj, hand = row
        p = {"name": name, "team": team, "opp": opp, "salary": sal,
             "era": era, "k9": k9, "bb9": bb9, "ip_proj": ip_proj,
             "hand": hand, "position": "SP"}
        stats = simulate_pitcher(p, opp, n_sims)
        # Estimated ownership: higher-proj pitchers get chalk ownership
        raw_own = max(2.0, (stats["projection"] - 15) * 1.2)
        results.append({**p, **stats, "ownership": round(raw_own, 1)})

    # Hitters
    for row in HITTERS:
        name, team, opp, pos, sal, avg, obp, slg, hr_rate, k_pct, hand = row
        opp_pitcher = pitcher_lookup.get(opp, {
            "team": opp, "era": 4.20, "k9": 8.5, "bb9": 3.0, "hand": "R"
        })
        h = {"name": name, "team": team, "opp": opp, "position": pos,
             "salary": sal, "avg": avg, "obp": obp, "slg": slg,
             "hr_rate": hr_rate, "k_pct": k_pct, "hand": hand}
        stats = simulate_player(h, opp_pitcher, n_sims)
        raw_own = max(1.5, (stats["projection"] - 3) * 3.5)
        results.append({**h, **stats, "ownership": round(min(raw_own, 45.0), 1)})

    print(f"  Done. {len(results)} players projected.")
    return results
