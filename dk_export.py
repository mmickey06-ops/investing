"""
DraftKings MLB Export — June 21 2026, 1:35 PM Slate
Generates optimized GPP lineups and writes a DK-ready upload CSV.

DraftKings upload CSV format:
  Entry ID, Contest Name, Contest ID, Entry Fee,
  SP, SP, C, 1B, 2B, 3B, SS, OF, OF, OF

Run:
  python dk_export.py                    # 20 GPP lineups
  python dk_export.py --lineups 5 --cash # cash game
  python dk_export.py --lineups 20 --max-exposure 25
"""

import argparse
import csv
import os
import pandas as pd
import pulp
import numpy as np
from collections import defaultdict
from simulate import run_all_simulations
from slate_data import GAMES, IMPLIED_TOTALS

SALARY_CAP   = 50_000
ROSTER_SIZE  = 10
POSITION_SLOTS = {"SP": 2, "C": 1, "1B": 1, "2B": 1, "3B": 1, "SS": 1, "OF": 3}
HITTER_POS   = {"C", "1B", "2B", "3B", "SS", "OF"}
OUTPUT_FILE  = "dk_lineups_06212026.csv"


# ── Stack configs for a 10-game slate ──────────────────────────────────────
# Each config drives one rotation of lineup builds.
# We cycle through these so lineups attack different games/correlations.
STACK_CONFIGS = [
    # ATL primary (high implied 5.5), HOU mini, MIA bring-back off Strider
    {"primary": "ATL", "ps": 4, "mini": "HOU", "ms": 2, "bb": "MIA", "bbs": 1},
    # HOU primary, TEX bring-back off Valdez
    {"primary": "HOU", "ps": 4, "mini": "NYY", "ms": 2, "bb": "TEX", "bbs": 1},
    # LAD primary, SF bring-back off Kershaw
    {"primary": "LAD", "ps": 4, "mini": "PHI", "ms": 2, "bb": "SF",  "bbs": 1},
    # SD primary (Soto stack + park boost COL), COL bring-back
    {"primary": "SD",  "ps": 4, "mini": "ATL", "ms": 2, "bb": "COL", "bbs": 1},
    # PHI primary, WSH bring-back off Wheeler
    {"primary": "PHI", "ps": 4, "mini": "CLE", "ms": 2, "bb": "WSH", "bbs": 1},
    # CHC primary, STL bring-back off Hendricks
    {"primary": "CHC", "ps": 4, "mini": "HOU", "ms": 2, "bb": "STL", "bbs": 1},
    # MIL primary, CIN bring-back off Burnes
    {"primary": "MIL", "ps": 4, "mini": "SD",  "ms": 2, "bb": "CIN", "bbs": 1},
    # NYY primary, BOS bring-back off Cole
    {"primary": "NYY", "ps": 4, "mini": "ATL", "ms": 2, "bb": "BOS", "bbs": 1},
    # TOR primary, MIN bring-back off Gausman
    {"primary": "TOR", "ps": 4, "mini": "LAD", "ms": 2, "bb": "MIN", "bbs": 1},
    # CLE primary, DET bring-back off Boyd
    {"primary": "CLE", "ps": 4, "mini": "PHI", "ms": 2, "bb": "DET", "bbs": 1},
]


def build_lineup(
    df: pd.DataFrame,
    cfg: dict,
    gpp_mode: bool,
    locked: list[str],
    excluded: list[str],
    prev_lineups: list[list[str]],
    min_unique: int = 3,
) -> tuple[list | None, dict | None]:

    players = df.reset_index(drop=True).copy()

    # GPP score = projection + contrarian bonus (low ownership = higher upside)
    if gpp_mode:
        players["score"] = (
            players["projection"]
            + (1.0 / players["ownership"].clip(lower=1.0)) * 3.0
        )
    else:
        players["score"] = players["projection"]

    n  = len(players)
    x  = [pulp.LpVariable(f"x{i}", cat="Binary") for i in range(n)]
    lp = pulp.LpProblem("DK", pulp.LpMaximize)

    lp += pulp.lpSum(players.iloc[i]["score"] * x[i] for i in range(n))
    lp += pulp.lpSum(players.iloc[i]["salary"] * x[i] for i in range(n)) <= SALARY_CAP
    lp += pulp.lpSum(x) == ROSTER_SIZE

    for pos, cnt in POSITION_SLOTS.items():
        idx = players.index[players["position"] == pos].tolist()
        lp += pulp.lpSum(x[i] for i in idx) == cnt

    # No pitcher–own-team stack
    for i in players.index[players["position"] == "SP"]:
        tm = players.iloc[i]["team"]
        mates = players.index[
            (players["team"] == tm) & (players["position"].isin(HITTER_POS))
        ].tolist()
        if mates:
            lp += pulp.lpSum(x[j] for j in mates) <= (1 - x[i]) * len(mates)

    # Primary stack
    if cfg.get("primary"):
        pidx = players.index[
            (players["team"] == cfg["primary"]) & (players["position"].isin(HITTER_POS))
        ].tolist()
        if pidx:
            lp += pulp.lpSum(x[i] for i in pidx) >= cfg.get("ps", 3)

    # Mini-stack
    if cfg.get("mini"):
        midx = players.index[
            (players["team"] == cfg["mini"]) & (players["position"].isin(HITTER_POS))
        ].tolist()
        if midx:
            lp += pulp.lpSum(x[i] for i in midx) >= cfg["ms"]

    # Bring-back
    if cfg.get("bb"):
        bbidx = players.index[
            (players["team"] == cfg["bb"]) & (players["position"].isin(HITTER_POS))
        ].tolist()
        if bbidx:
            lp += pulp.lpSum(x[i] for i in bbidx) >= cfg["bbs"]

    # Locked
    for name in locked:
        idx = players.index[players["name"] == name].tolist()
        if idx:
            lp += x[idx[0]] == 1

    # Excluded
    for name in excluded:
        idx = players.index[players["name"] == name].tolist()
        if idx:
            lp += x[idx[0]] == 0

    # Uniqueness
    for prev in prev_lineups:
        pidx2 = players.index[players["name"].isin(prev)].tolist()
        lp += pulp.lpSum(x[i] for i in pidx2) <= ROSTER_SIZE - min_unique

    lp.solve(pulp.PULP_CBC_CMD(msg=0))

    if pulp.LpStatus[lp.status] != "Optimal":
        return None, None

    sel = [players.iloc[i].to_dict() for i in range(n) if pulp.value(x[i]) == 1]
    return sel, {
        "salary": sum(p["salary"] for p in sel),
        "projection": round(sum(p["projection"] for p in sel), 2),
        "avg_own": round(sum(p["ownership"] for p in sel) / len(sel), 1),
    }


def exposure_report(lineups: list[list[dict]]) -> dict[str, float]:
    counts: dict[str, int] = defaultdict(int)
    total = len(lineups)
    for lu in lineups:
        for p in lu:
            counts[p["name"]] += 1
    return {n: round(c / total * 100, 1) for n, c in sorted(counts.items(), key=lambda x: -x[1])}


def print_lineup(players: list[dict], meta: dict, num: int):
    ORDER = ["SP", "C", "1B", "2B", "3B", "SS", "OF"]
    sorted_p = sorted(players, key=lambda p: (
        ORDER.index(p["position"]) if p["position"] in ORDER else 99, p["name"]
    ))
    print(f"\n{'─'*72}")
    print(f" #{num:>2}  Salary ${meta['salary']:,}  |  Proj {meta['projection']:.1f} pts  |  Avg Own {meta['avg_own']}%")
    print(f"{'─'*72}")
    print(f"{'POS':<5}{'NAME':<24}{'TEAM':<6}{'OPP':<6}{'SAL':>7}{'PROJ':>7}{'CEIL':>7}{'OWN':>6}")
    print(f"{'─'*72}")
    for p in sorted_p:
        print(f"{p['position']:<5}{p['name']:<24}{p['team']:<6}{p['opp']:<6}"
              f"${p['salary']:>6,}{p['projection']:>7.1f}{p['p90']:>7.1f}{p['ownership']:>5.1f}%")


def write_dk_csv(lineups: list[list[dict]], path: str):
    """
    Write DraftKings upload CSV.
    Format: Entry ID, Contest Name, Contest ID, Entry Fee,
            SP, SP, C, 1B, 2B, 3B, SS, OF, OF, OF
    """
    POS_ORDER = ["SP", "SP", "C", "1B", "2B", "3B", "SS", "OF", "OF", "OF"]
    rows = []
    for lu in lineups:
        by_pos: dict[str, list] = defaultdict(list)
        for p in lu:
            by_pos[p["position"]].append(p["name"])
        row = ["", "", "", ""]  # Entry ID, Contest Name, Contest ID, Entry Fee — fill in DK
        sp_list = by_pos.get("SP", [])
        row.append(sp_list[0] if len(sp_list) > 0 else "")
        row.append(sp_list[1] if len(sp_list) > 1 else "")
        for pos in ["C", "1B", "2B", "3B", "SS"]:
            vals = by_pos.get(pos, [""])
            row.append(vals[0])
        of_list = by_pos.get("OF", [])
        row.append(of_list[0] if len(of_list) > 0 else "")
        row.append(of_list[1] if len(of_list) > 1 else "")
        row.append(of_list[2] if len(of_list) > 2 else "")
        rows.append(row)

    header = ["Entry ID", "Contest Name", "Contest ID", "Entry Fee",
              "SP", "SP", "C", "1B", "2B", "3B", "SS", "OF", "OF", "OF"]
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"\n  Saved → {path}  ({len(rows)} lineups)")


def run(
    n_lineups: int = 20,
    gpp_mode: bool = True,
    max_exposure: float = 35.0,
    locked: list[str] = None,
    excluded: list[str] = None,
    n_sims: int = 10000,
):
    locked   = locked or []
    excluded = excluded or []

    # ── 1. Simulate projections ───────────────────────────────────────────
    print("\n" + "="*72)
    print("  DraftKings MLB  |  June 21 2026  |  1:35 PM Slate")
    print("="*72)
    print(f"  Mode: {'GPP (Tournament)' if gpp_mode else 'CASH'}  |  "
          f"Lineups: {n_lineups}  |  Max Exposure: {max_exposure}%  |  Sims: {n_sims:,}")

    # Top implied totals
    sorted_totals = sorted(IMPLIED_TOTALS.items(), key=lambda x: -x[1])
    print("\n  Top Implied Totals:")
    for team, total in sorted_totals[:8]:
        bar = "█" * int(total * 2)
        print(f"    {team:<5} {total:.1f}  {bar}")

    sim_results = run_all_simulations(n_sims)
    df = pd.DataFrame(sim_results)

    # ── 2. Projection board ───────────────────────────────────────────────
    print("\n  Top 20 Projected Hitters:")
    print(f"  {'NAME':<24}{'POS':<5}{'TEAM':<6}{'SAL':>7}{'PROJ':>7}{'CEIL':>7}{'OWN':>6}")
    print(f"  {'─'*60}")
    top_h = df[df["position"] != "SP"].nlargest(20, "projection")
    for _, r in top_h.iterrows():
        print(f"  {r['name']:<24}{r['position']:<5}{r['team']:<6}"
              f"${r['salary']:>6,}{r['projection']:>7.1f}{r['p90']:>7.1f}{r['ownership']:>5.1f}%")

    print("\n  Pitchers Ranked by Projection:")
    print(f"  {'NAME':<24}{'TEAM':<6}{'OPP':<6}{'SAL':>7}{'PROJ':>7}{'CEIL':>7}{'OWN':>6}")
    print(f"  {'─'*60}")
    sp = df[df["position"] == "SP"].nlargest(20, "projection")
    for _, r in sp.iterrows():
        print(f"  {r['name']:<24}{r['team']:<6}{r['opp']:<6}"
              f"${r['salary']:>6,}{r['projection']:>7.1f}{r['p90']:>7.1f}{r['ownership']:>5.1f}%")

    # ── 3. Optimize lineups ───────────────────────────────────────────────
    print(f"\n  Generating {n_lineups} lineups...\n")
    all_lineups: list[list[dict]] = []
    all_meta: list[dict] = []
    prev_names: list[list[str]] = []

    for i in range(n_lineups):
        cfg = STACK_CONFIGS[i % len(STACK_CONFIGS)]

        # Enforce exposure
        over = []
        if all_lineups:
            exp = exposure_report(all_lineups)
            over = [nm for nm, pct in exp.items() if pct >= max_exposure]

        eff_excl = list(set(excluded + over))

        lu, meta = build_lineup(
            df, cfg, gpp_mode, locked, eff_excl, prev_names
        )

        if lu is None:
            # Relax stack constraints
            lu, meta = build_lineup(
                df, {"primary": cfg["primary"], "ps": 3},
                gpp_mode, locked, excluded, prev_names
            )

        if lu is None:
            lu, meta = build_lineup(df, {}, gpp_mode, locked, excluded, prev_names)

        if lu:
            all_lineups.append(lu)
            all_meta.append(meta)
            prev_names.append([p["name"] for p in lu])
            print_lineup(lu, meta, i + 1)

    # ── 4. Exposure report ────────────────────────────────────────────────
    print(f"\n{'='*72}")
    print("  EXPOSURE REPORT")
    print(f"{'='*72}")
    exp = exposure_report(all_lineups)
    print(f"  {'PLAYER':<26}{'EXPOSURE':>10}  CHART")
    print(f"  {'─'*55}")
    for name, pct in exp.items():
        bar  = "█" * int(pct / 5)
        flag = " ⚠ OVER" if pct > max_exposure else ""
        print(f"  {name:<26}{pct:>6.1f}%  {bar}{flag}")

    # Summary stats
    proj_vals = [m["projection"] for m in all_meta]
    own_vals  = [m["avg_own"] for m in all_meta]
    sal_vals  = [m["salary"] for m in all_meta]
    print(f"\n  Lineup Summary:")
    print(f"    Avg Projection : {np.mean(proj_vals):.1f} pts")
    print(f"    Avg Salary Used: ${np.mean(sal_vals):,.0f}")
    print(f"    Avg Ownership  : {np.mean(own_vals):.1f}%")

    # ── 5. Export ─────────────────────────────────────────────────────────
    write_dk_csv(all_lineups, OUTPUT_FILE)
    return all_lineups


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DK MLB Export — June 21 2026")
    parser.add_argument("--lineups",      type=int,   default=20)
    parser.add_argument("--cash",         action="store_true")
    parser.add_argument("--max-exposure", type=float, default=35.0)
    parser.add_argument("--lock",         nargs="*",  default=[])
    parser.add_argument("--exclude",      nargs="*",  default=[])
    parser.add_argument("--sims",         type=int,   default=10000)
    args = parser.parse_args()

    run(
        n_lineups    = args.lineups,
        gpp_mode     = not args.cash,
        max_exposure = args.max_exposure,
        locked       = args.lock,
        excluded     = args.exclude,
        n_sims       = args.sims,
    )
