"""
DraftKings MLB Lineup Optimizer
- Salary cap enforcement ($50,000)
- Position requirements: 2 SP, 1 C, 1 1B, 1 2B, 1 3B, 1 SS, 3 OF
- Stacking: primary stack (4-5), mini-stack (2-3), bring-back (1-2)
- Exposure limits across N lineups
- Contrarian pitcher option for GPPs
- Uses PuLP for integer linear programming
"""

import pulp
import pandas as pd
import random
from collections import defaultdict
from copy import deepcopy

# ---------------------------------------------------------------------------
# Sample player pool — replace with real DK salaries/projections
# Format: name, team, opponent, position, salary, projection, ownership%
# ---------------------------------------------------------------------------
SAMPLE_PLAYERS = [
    # Pitchers
    ("Gerrit Cole",      "NYY", "BOS", "SP", 10500, 45.0, 22),
    ("Spencer Strider",  "ATL", "MIA", "SP",  9800, 43.0, 18),
    ("Dylan Cease",      "SD",  "COL", "SP",  9200, 40.0, 12),
    ("Corbin Burnes",    "BAL", "TB",  "SP",  9000, 38.0, 10),
    ("Zack Wheeler",     "PHI", "WSH", "SP",  9600, 42.0, 20),
    ("Kyle Hendricks",   "CHC", "STL", "SP",  6500, 24.0,  5),
    ("JP Sears",         "OAK", "LAA", "SP",  6200, 22.0,  4),
    ("Michael Lorenzen", "DET", "CLE", "SP",  6800, 25.0,  6),

    # Catchers
    ("Will Smith",       "LAD", "SF",  "C",   5200, 10.5, 14),
    ("Adley Rutschman",  "BAL", "TB",  "C",   5500, 11.0, 16),
    ("Sean Murphy",      "ATL", "MIA", "C",   4800,  9.5, 10),
    ("Jonah Heim",       "TEX", "HOU", "C",   3900,  7.5,  6),

    # First Base
    ("Freddie Freeman",  "LAD", "SF",  "1B",  5800, 12.0, 20),
    ("Pete Alonso",      "NYM", "PIT", "1B",  5500, 11.5, 18),
    ("Matt Olson",       "ATL", "MIA", "1B",  5200, 11.0, 15),
    ("Rhys Hoskins",     "MIL", "CIN", "1B",  4500,  9.0,  8),

    # Second Base
    ("Jose Altuve",      "HOU", "TEX", "2B",  5400, 11.5, 19),
    ("Marcus Semien",    "TEX", "HOU", "2B",  5100, 10.5, 14),
    ("Ozzie Albies",     "ATL", "MIA", "2B",  4900, 10.0, 12),
    ("Whit Merrifield",  "PHI", "WSH", "2B",  3800,  7.5,  5),

    # Third Base
    ("Austin Riley",     "ATL", "MIA", "3B",  5600, 12.0, 22),
    ("Rafael Devers",    "BOS", "NYY", "3B",  5400, 11.5, 17),
    ("Jose Ramirez",     "CLE", "DET", "3B",  5800, 12.5, 25),
    ("Gunnar Henderson", "BAL", "TB",  "3B",  5000, 10.5, 13),

    # Shortstop
    ("Trea Turner",      "PHI", "WSH", "SS",  5500, 11.5, 20),
    ("Corey Seager",     "TEX", "HOU", "SS",  5700, 12.0, 21),
    ("Bo Bichette",      "TOR", "MIN", "SS",  5200, 10.5, 15),
    ("Xander Bogaerts",  "SD",  "COL", "SS",  4800,  9.5, 10),

    # Outfield
    ("Ronald Acuna Jr.", "ATL", "MIA", "OF",  6200, 14.0, 28),
    ("Mookie Betts",     "LAD", "SF",  "OF",  5900, 13.0, 24),
    ("Mike Trout",       "LAA", "OAK", "OF",  5700, 12.5, 20),
    ("Juan Soto",        "SD",  "COL", "OF",  5800, 13.0, 22),
    ("Yordan Alvarez",   "HOU", "TEX", "OF",  5600, 12.5, 21),
    ("Kyle Tucker",      "HOU", "TEX", "OF",  5200, 11.0, 16),
    ("Christian Yelich", "MIL", "CIN", "OF",  4800,  9.5, 11),
    ("Cedric Mullins",   "BAL", "TB",  "OF",  4200,  8.5,  7),
    ("Michael Brantley", "HOU", "TEX", "OF",  3800,  7.0,  4),
    ("Jorge Soler",      "MIA", "ATL", "OF",  4000,  7.5,  5),
]

COLUMNS = ["name", "team", "opponent", "position", "salary", "projection", "ownership"]

# DraftKings constraints
SALARY_CAP = 50_000
ROSTER_SIZE = 10
POSITION_SLOTS = {"SP": 2, "C": 1, "1B": 1, "2B": 1, "3B": 1, "SS": 1, "OF": 3}


def load_players(csv_path=None):
    """Load player pool from CSV or fall back to sample data."""
    if csv_path:
        df = pd.read_csv(csv_path)
        df.columns = [c.lower().strip() for c in df.columns]
    else:
        df = pd.DataFrame(SAMPLE_PLAYERS, columns=COLUMNS)
    return df


def build_lineup(
    df: pd.DataFrame,
    locked: list[str] = None,
    excluded: list[str] = None,
    primary_stack_team: str = None,
    primary_stack_size: int = 4,
    mini_stack_team: str = None,
    mini_stack_size: int = 2,
    bring_back_team: str = None,
    bring_back_size: int = 1,
    prev_lineups: list[list[str]] = None,
    min_unique: int = 3,
    gpp_mode: bool = True,
):
    """
    Solve one DraftKings MLB lineup using integer linear programming.

    Parameters
    ----------
    locked          : player names that MUST appear
    excluded        : player names that cannot appear
    primary_stack_team  : team to stack 4-5 hitters from
    mini_stack_team     : team to add 2-3 hitters from
    bring_back_team     : team to pull 1-2 hitters from (off your pitcher's opponent)
    prev_lineups    : list of previous lineup name-lists (for uniqueness)
    min_unique      : minimum players that must differ from each previous lineup
    gpp_mode        : if True, weight by 1/ownership to boost contrarian value
    """
    locked = locked or []
    excluded = excluded or []
    prev_lineups = prev_lineups or []

    players = df.copy()

    # Objective: maximize projection (GPP adds contrarian bonus)
    if gpp_mode:
        players["score"] = players["projection"] + (1 / players["ownership"].clip(lower=1)) * 2
    else:
        players["score"] = players["projection"]

    prob = pulp.LpProblem("DK_MLB", pulp.LpMaximize)
    n = len(players)
    x = [pulp.LpVariable(f"x_{i}", cat="Binary") for i in range(n)]

    # Objective
    prob += pulp.lpSum(players.iloc[i]["score"] * x[i] for i in range(n))

    # Salary cap
    prob += pulp.lpSum(players.iloc[i]["salary"] * x[i] for i in range(n)) <= SALARY_CAP

    # Roster size
    prob += pulp.lpSum(x) == ROSTER_SIZE

    # Position requirements
    for pos, count in POSITION_SLOTS.items():
        idx = players.index[players["position"] == pos].tolist()
        prob += pulp.lpSum(x[i] for i in idx) == count

    # Locked players
    for name in locked:
        idx = players.index[players["name"] == name].tolist()
        if idx:
            prob += x[idx[0]] == 1

    # Excluded players
    for name in excluded:
        idx = players.index[players["name"] == name].tolist()
        if idx:
            prob += x[idx[0]] == 0

    # No stacking your pitcher's own team (pitchers can't share team with hitters they pitch for)
    sp_idx = players.index[players["position"] == "SP"].tolist()
    hitter_positions = ["C", "1B", "2B", "3B", "SS", "OF"]
    for i in sp_idx:
        team = players.iloc[i]["team"]
        teammate_idx = players.index[
            (players["team"] == team) & (players["position"].isin(hitter_positions))
        ].tolist()
        if teammate_idx:
            # If this SP is selected, none of his teammates can be selected
            prob += pulp.lpSum(x[j] for j in teammate_idx) <= (1 - x[i]) * len(teammate_idx)

    # Primary stack
    if primary_stack_team:
        hitter_idx = players.index[
            (players["team"] == primary_stack_team) &
            (players["position"].isin(hitter_positions))
        ].tolist()
        if hitter_idx:
            prob += pulp.lpSum(x[i] for i in hitter_idx) >= primary_stack_size

    # Mini-stack
    if mini_stack_team:
        hitter_idx = players.index[
            (players["team"] == mini_stack_team) &
            (players["position"].isin(hitter_positions))
        ].tolist()
        if hitter_idx:
            prob += pulp.lpSum(x[i] for i in hitter_idx) >= mini_stack_size

    # Bring-back
    if bring_back_team:
        hitter_idx = players.index[
            (players["team"] == bring_back_team) &
            (players["position"].isin(hitter_positions))
        ].tolist()
        if hitter_idx:
            prob += pulp.lpSum(x[i] for i in hitter_idx) >= bring_back_size

    # Uniqueness vs previous lineups
    for prev in prev_lineups:
        prev_idx = players.index[players["name"].isin(prev)].tolist()
        prob += pulp.lpSum(x[i] for i in prev_idx) <= ROSTER_SIZE - min_unique

    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    if pulp.LpStatus[prob.status] != "Optimal":
        return None, None

    selected = [players.iloc[i] for i in range(n) if pulp.value(x[i]) == 1]
    total_salary = sum(p["salary"] for p in selected)
    total_proj = sum(p["projection"] for p in selected)
    return selected, {"salary": total_salary, "projection": total_proj}


def print_lineup(players, meta, lineup_num=1):
    print(f"\n{'='*60}")
    print(f"  LINEUP #{lineup_num}   Salary: ${meta['salary']:,}   Proj: {meta['projection']:.1f} pts")
    print(f"{'='*60}")
    print(f"{'POS':<5} {'NAME':<22} {'TEAM':<6} {'OPP':<6} {'SAL':>6} {'PROJ':>6} {'OWN':>5}")
    print(f"{'-'*60}")
    order = ["SP", "C", "1B", "2B", "3B", "SS", "OF"]
    sorted_players = sorted(players, key=lambda p: (order.index(p["position"]) if p["position"] in order else 99, p["name"]))
    for p in sorted_players:
        print(f"{p['position']:<5} {p['name']:<22} {p['team']:<6} {p['opponent']:<6} ${p['salary']:>5,} {p['projection']:>6.1f} {p['ownership']:>4}%")


def calc_exposure(all_lineups):
    counts = defaultdict(int)
    total = len(all_lineups)
    for lineup in all_lineups:
        for p in lineup:
            counts[p["name"]] += 1
    return {name: round(cnt / total * 100, 1) for name, cnt in sorted(counts.items(), key=lambda x: -x[1])}


def run_optimizer(
    n_lineups: int = 5,
    gpp_mode: bool = True,
    stack_configs: list[dict] = None,
    locked: list[str] = None,
    excluded: list[str] = None,
    max_exposure: float = 40.0,
    csv_path: str = None,
):
    """
    Generate N optimized DraftKings lineups.

    stack_configs: list of dicts with keys:
        primary_team, primary_size, mini_team, mini_size, bring_back_team, bring_back_size
    """
    df = load_players(csv_path)
    all_lineups = []
    all_meta = []
    names_per_lineup = []

    # Default stack configs if none provided
    if not stack_configs:
        # Auto-detect top implied total teams (here we just pick ATL and HOU as examples)
        stack_configs = [
            {"primary_team": "ATL", "primary_size": 4, "mini_team": "HOU", "mini_size": 2, "bring_back_team": "MIA", "bring_back_size": 1},
            {"primary_team": "HOU", "primary_size": 4, "mini_team": "ATL", "mini_size": 2, "bring_back_team": "TEX", "bring_back_size": 1},
            {"primary_team": "LAD", "primary_size": 4, "mini_team": "BAL", "mini_size": 2, "bring_back_team": "SF",  "bring_back_size": 1},
        ]

    for i in range(n_lineups):
        cfg = stack_configs[i % len(stack_configs)]

        # Enforce exposure: exclude over-exposed players
        over_exposed = []
        if all_lineups:
            exposure = calc_exposure(all_lineups)
            over_exposed = [name for name, pct in exposure.items() if pct >= max_exposure]

        effective_excluded = list(set((excluded or []) + over_exposed))

        lineup, meta = build_lineup(
            df,
            locked=locked,
            excluded=effective_excluded,
            primary_stack_team=cfg.get("primary_team"),
            primary_stack_size=cfg.get("primary_size", 4),
            mini_stack_team=cfg.get("mini_team"),
            mini_stack_size=cfg.get("mini_size", 2),
            bring_back_team=cfg.get("bring_back_team"),
            bring_back_size=cfg.get("bring_back_size", 1),
            prev_lineups=names_per_lineup,
            min_unique=3,
            gpp_mode=gpp_mode,
        )

        if lineup is None:
            print(f"  [!] Could not generate lineup #{i+1} — relaxing constraints")
            lineup, meta = build_lineup(df, locked=locked, excluded=excluded, gpp_mode=gpp_mode, prev_lineups=names_per_lineup)

        if lineup:
            all_lineups.append(lineup)
            all_meta.append(meta)
            names_per_lineup.append([p["name"] for p in lineup])
            print_lineup(lineup, meta, i + 1)

    # Exposure report
    print(f"\n{'='*60}")
    print("  EXPOSURE REPORT")
    print(f"{'='*60}")
    exposure = calc_exposure(all_lineups)
    print(f"{'PLAYER':<25} {'EXPOSURE':>10}")
    print(f"{'-'*37}")
    for name, pct in exposure.items():
        bar = "█" * int(pct / 5)
        flag = " ⚠" if pct > max_exposure else ""
        print(f"{name:<25} {pct:>6.1f}%  {bar}{flag}")

    return all_lineups


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="DraftKings MLB Lineup Optimizer")
    parser.add_argument("--lineups", type=int, default=5, help="Number of lineups to generate")
    parser.add_argument("--cash", action="store_true", help="Cash game mode (no contrarian boost)")
    parser.add_argument("--max-exposure", type=float, default=40.0, help="Max player exposure %% (default 40)")
    parser.add_argument("--lock", nargs="*", default=[], help="Player names to lock into every lineup")
    parser.add_argument("--exclude", nargs="*", default=[], help="Player names to exclude")
    parser.add_argument("--csv", type=str, default=None, help="Path to player pool CSV")
    args = parser.parse_args()

    print(f"\nDraftKings MLB Optimizer")
    print(f"Mode: {'CASH' if args.cash else 'GPP (Tournament)'}")
    print(f"Lineups: {args.lineups} | Max Exposure: {args.max_exposure}%")
    if args.lock:
        print(f"Locked: {', '.join(args.lock)}")
    if args.exclude:
        print(f"Excluded: {', '.join(args.exclude)}")

    run_optimizer(
        n_lineups=args.lineups,
        gpp_mode=not args.cash,
        locked=args.lock,
        excluded=args.exclude,
        max_exposure=args.max_exposure,
        csv_path=args.csv,
    )
