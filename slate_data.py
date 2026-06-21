"""
June 21, 2026 — 1:35 PM ET DraftKings Slate
10-game Sunday afternoon slate with realistic 2026 player data.
Stats modeled on 2024-2025 actuals with 2026 projections.
"""

# Game environment factors
PARK_FACTORS = {
    # (run_factor, hr_factor)  1.0 = neutral
    "COL": (1.38, 1.45), "CIN": (1.12, 1.18), "TEX": (1.08, 1.10),
    "BOS": (1.06, 1.05), "MIL": (1.04, 1.06), "HOU": (1.03, 1.05),
    "NYY": (1.02, 1.03), "LAD": (1.00, 1.00), "ATL": (0.99, 0.98),
    "PHI": (1.01, 1.02), "MIN": (1.03, 1.04), "SD":  (0.94, 0.93),
    "SEA": (0.93, 0.91), "OAK": (0.96, 0.95), "MIA": (0.91, 0.90),
    "WSH": (1.00, 1.00), "STL": (0.97, 0.96), "PIT": (0.98, 0.97),
    "DET": (0.96, 0.95), "CLE": (0.97, 0.96), "TB":  (0.95, 0.94),
    "BAL": (1.01, 1.02), "TOR": (1.00, 1.00), "CWS": (1.05, 1.07),
    "NYM": (0.98, 0.97), "SF":  (0.92, 0.90), "LAA": (0.97, 0.96),
    "KC":  (0.99, 0.98), "ARI": (1.05, 1.08), "CHC": (1.02, 1.03),
}

# 10-game 1:35 PM slate — June 21 2026
GAMES = [
    {"home": "NYY", "away": "BOS", "time": "1:05", "stadium": "NYY"},
    {"home": "ATL", "away": "MIA", "time": "1:20", "stadium": "ATL"},
    {"home": "PHI", "away": "WSH", "time": "1:05", "stadium": "PHI"},
    {"home": "STL", "away": "CHC", "time": "1:15", "stadium": "STL"},
    {"home": "CLE", "away": "DET", "time": "1:10", "stadium": "CLE"},
    {"home": "MIL", "away": "CIN", "time": "1:10", "stadium": "MIL"},
    {"home": "MIN", "away": "TOR", "time": "1:10", "stadium": "MIN"},
    {"home": "HOU", "away": "TEX", "time": "1:10", "stadium": "HOU"},
    {"home": "LAD", "away": "SF",  "time": "4:05", "stadium": "LAD"},
    {"home": "SD",  "away": "COL", "time": "4:10", "stadium": "SD"},
]

# implied totals (runs expected per team)
IMPLIED_TOTALS = {
    "NYY": 5.0, "BOS": 4.5,
    "ATL": 5.5, "MIA": 3.5,
    "PHI": 5.0, "WSH": 3.8,
    "STL": 4.2, "CHC": 4.8,
    "CLE": 4.5, "DET": 4.2,
    "MIL": 4.8, "CIN": 4.6,
    "MIN": 4.5, "TOR": 4.8,
    "HOU": 5.2, "TEX": 4.8,
    "LAD": 5.5, "SF":  4.0,
    "SD":  5.0, "COL": 5.2,
}

# ------------------------------------------------------------------
# PITCHERS  (name, team, opponent, salary, era, k9, bb9, ip_proj, hand)
# ------------------------------------------------------------------
PITCHERS = [
    # Studs
    ("Gerrit Cole",     "NYY", "BOS", 10500, 2.85, 10.8, 2.1, 6.2, "R"),
    ("Spencer Strider", "ATL", "MIA",  9800, 2.95, 13.2, 2.8, 6.0, "R"),
    ("Zack Wheeler",    "PHI", "WSH",  9600, 2.90, 10.2, 1.9, 6.5, "R"),
    ("Corbin Burnes",   "MIL", "CIN",  9200, 2.80,  9.8, 2.2, 6.5, "R"),
    # Mid-tier
    ("Pablo Lopez",     "MIN", "TOR",  8500, 3.35,  9.5, 2.5, 6.0, "R"),
    ("Framber Valdez",  "HOU", "TEX",  8800, 3.10,  8.5, 3.0, 6.5, "L"),
    ("Yu Darvish",      "SD",  "COL",  8400, 3.45, 10.2, 2.6, 6.0, "R"),
    ("Clayton Kershaw", "LAD", "SF",   7800, 3.60,  9.0, 2.2, 5.5, "L"),
    # Value
    ("Kyle Hendricks",  "STL", "CHC",  6500, 4.20,  6.5, 2.1, 5.5, "R"),
    ("Matthew Boyd",    "CLE", "DET",  6800, 4.10,  8.8, 3.1, 5.0, "L"),
    ("JP Sears",        "DET", "CLE",  6200, 4.45,  8.2, 2.9, 5.0, "L"),
    ("Patrick Corbin",  "WSH", "PHI",  5800, 5.20,  7.2, 3.5, 4.5, "L"),
    ("Trevor Rogers",   "MIA", "ATL",  6000, 4.80,  9.1, 4.0, 4.5, "L"),
    ("Kevin Gausman",   "TOR", "MIN",  8200, 3.50, 10.5, 2.4, 6.0, "R"),
    ("Anthony DeSclafani","SF","LAD",  6800, 4.30,  8.5, 2.8, 5.5, "R"),
    ("Hunter Greene",   "CIN", "MIL",  8000, 3.80, 11.5, 3.5, 5.5, "R"),
    ("Tarik Skubal",    "DET", "CLE",  8600, 3.20, 10.8, 2.3, 6.0, "L"),
    ("Sonny Gray",      "STL", "CHC",  7500, 3.70,  9.5, 2.7, 5.5, "R"),
    ("Chris Sale",      "ATL", "MIA",  7200, 3.90, 10.0, 2.9, 5.0, "L"),
    ("Nathan Eovaldi",  "TEX", "HOU",  7600, 3.95,  8.8, 2.4, 5.5, "R"),
]

# ------------------------------------------------------------------
# HITTERS  (name, team, opp, pos, salary, avg, obp, slg, hr_rate, k_pct, hand)
# hr_rate = HR per plate appearance
# ------------------------------------------------------------------
HITTERS = [
    # ---- CATCHERS ----
    ("Will Smith",       "LAD", "SF",  "C",  5200, .272, .358, .472, .045, .215, "R"),
    ("Adley Rutschman",  "BAL", "TB",  "C",  5500, .280, .380, .465, .042, .190, "S"),
    ("Sean Murphy",      "ATL", "MIA", "C",  4800, .255, .345, .450, .048, .225, "R"),
    ("Jonah Heim",       "TEX", "HOU", "C",  3900, .240, .305, .395, .035, .235, "S"),
    ("Cal Raleigh",      "SEA", "OAK", "C",  4600, .235, .310, .460, .058, .265, "R"),
    ("Gabriel Moreno",   "ARI", "KC",  "C",  4200, .268, .335, .420, .030, .185, "R"),
    ("Francisco Alvarez","NYM", "PIT", "C",  4800, .252, .330, .455, .052, .240, "R"),
    ("Tyler Stephenson", "CIN", "MIL", "C",  4000, .265, .350, .420, .035, .195, "R"),
    ("Willson Contreras","STL", "CHC", "C",  4500, .258, .340, .435, .040, .215, "R"),
    ("Bo Naylor",        "CLE", "DET", "C",  3800, .240, .325, .415, .038, .245, "L"),

    # ---- FIRST BASE ----
    ("Freddie Freeman",  "LAD", "SF",  "1B", 5800, .310, .405, .540, .048, .175, "L"),
    ("Pete Alonso",      "NYM", "PIT", "1B", 5500, .255, .355, .520, .068, .240, "R"),
    ("Matt Olson",       "ATL", "MIA", "1B", 5200, .262, .360, .520, .065, .245, "L"),
    ("Rhys Hoskins",     "MIL", "CIN", "1B", 4500, .248, .345, .488, .058, .235, "R"),
    ("Josh Bell",        "HOU", "TEX", "1B", 4000, .258, .355, .445, .040, .210, "S"),
    ("Vinnie Pasquantino","KC", "ARI", "1B", 4800, .275, .360, .460, .038, .195, "L"),
    ("Christian Walker", "ARI", "KC",  "1B", 4600, .248, .325, .475, .055, .265, "R"),
    ("Spencer Torkelson","DET", "CLE", "1B", 4700, .242, .330, .460, .052, .255, "R"),
    ("Luke Voit",        "MIN", "TOR", "1B", 3800, .235, .310, .430, .045, .265, "R"),
    ("Ty France",        "CIN", "MIL", "1B", 4200, .268, .340, .420, .028, .185, "R"),

    # ---- SECOND BASE ----
    ("Jose Altuve",      "HOU", "TEX", "2B", 5400, .302, .375, .510, .042, .145, "R"),
    ("Marcus Semien",    "TEX", "HOU", "2B", 5100, .275, .345, .490, .045, .180, "R"),
    ("Ozzie Albies",     "ATL", "MIA", "2B", 4900, .270, .330, .465, .040, .185, "R"),
    ("Whit Merrifield",  "PHI", "WSH", "2B", 3800, .265, .320, .395, .018, .155, "R"),
    ("Gleyber Torres",   "NYY", "BOS", "2B", 4800, .268, .345, .445, .040, .185, "R"),
    ("Jeff McNeil",      "NYM", "PIT", "2B", 4200, .285, .345, .420, .020, .125, "L"),
    ("Andres Gimenez",   "CLE", "DET", "2B", 4400, .262, .330, .415, .028, .175, "L"),
    ("Brendan Donovan",  "STL", "CHC", "2B", 4000, .278, .368, .415, .022, .140, "L"),
    ("DJ LeMahieu",      "NYY", "BOS", "2B", 3900, .258, .330, .390, .018, .145, "R"),
    ("Kolten Wong",      "MIL", "CIN", "2B", 3700, .252, .330, .385, .020, .165, "L"),

    # ---- THIRD BASE ----
    ("Austin Riley",     "ATL", "MIA", "3B", 5600, .278, .352, .520, .062, .225, "R"),
    ("Rafael Devers",    "BOS", "NYY", "3B", 5400, .280, .355, .530, .065, .225, "L"),
    ("Jose Ramirez",     "CLE", "DET", "3B", 5800, .285, .370, .535, .058, .135, "S"),
    ("Gunnar Henderson", "BAL", "TB",  "3B", 5000, .275, .355, .505, .055, .220, "L"),
    ("Alex Bregman",     "BOS", "NYY", "3B", 5200, .270, .368, .480, .045, .155, "R"),
    ("Manny Machado",    "SD",  "COL", "3B", 5300, .268, .352, .478, .042, .165, "R"),
    ("Nolan Arenado",    "STL", "CHC", "3B", 5100, .272, .340, .500, .055, .175, "R"),
    ("Jordan Walker",    "STL", "CHC", "3B", 4600, .268, .330, .448, .038, .220, "R"),
    ("Josh Jung",        "TEX", "HOU", "3B", 4700, .260, .330, .462, .048, .235, "R"),
    ("Jeimer Candelario","CIN", "MIL", "3B", 4200, .262, .348, .435, .035, .200, "S"),

    # ---- SHORTSTOP ----
    ("Trea Turner",      "PHI", "WSH", "SS", 5500, .285, .340, .490, .035, .185, "R"),
    ("Corey Seager",     "TEX", "HOU", "SS", 5700, .280, .355, .520, .052, .200, "L"),
    ("Bo Bichette",      "TOR", "MIN", "SS", 5200, .278, .330, .468, .032, .195, "R"),
    ("Xander Bogaerts",  "SD",  "COL", "SS", 4800, .265, .345, .450, .038, .185, "R"),
    ("Francisco Lindor", "NYM", "PIT", "SS", 5600, .272, .350, .490, .048, .205, "S"),
    ("Carlos Correa",    "MIN", "TOR", "SS", 5400, .268, .355, .480, .045, .185, "R"),
    ("CJ Abrams",        "WSH", "PHI", "SS", 4500, .268, .335, .435, .028, .215, "L"),
    ("Paul DeJong",      "CHC", "STL", "SS", 3800, .225, .300, .415, .042, .270, "R"),
    ("Amed Rosario",     "MIL", "CIN", "SS", 3900, .258, .305, .385, .018, .195, "R"),
    ("Anthony Volpe",    "NYY", "BOS", "SS", 4800, .248, .320, .430, .035, .225, "R"),

    # ---- OUTFIELD ----
    ("Ronald Acuna Jr.", "ATL", "MIA", "OF", 6200, .308, .408, .570, .055, .185, "R"),
    ("Mookie Betts",     "LAD", "SF",  "OF", 5900, .295, .395, .550, .055, .140, "R"),
    ("Yordan Alvarez",   "HOU", "TEX", "OF", 5600, .290, .400, .580, .068, .205, "L"),
    ("Juan Soto",        "SD",  "COL", "OF", 5800, .285, .420, .530, .052, .175, "L"),
    ("Kyle Tucker",      "HOU", "TEX", "OF", 5200, .278, .370, .520, .055, .200, "L"),
    ("Mike Trout",       "LAA", "OAK", "OF", 5700, .272, .380, .535, .065, .245, "R"),
    ("Christian Yelich", "MIL", "CIN", "OF", 4800, .278, .380, .490, .042, .185, "L"),
    ("Julio Rodriguez",  "SEA", "OAK", "OF", 5400, .275, .340, .490, .040, .225, "R"),
    ("Cedric Mullins",   "BAL", "TB",  "OF", 4200, .258, .325, .420, .025, .195, "L"),
    ("Jorge Soler",      "MIA", "ATL", "OF", 4000, .240, .325, .445, .052, .285, "R"),
    ("Ian Happ",         "CHC", "STL", "OF", 4600, .258, .360, .450, .038, .210, "S"),
    ("Cody Bellinger",   "CHC", "STL", "OF", 5000, .268, .345, .468, .040, .215, "L"),
    ("Tyler O'Neill",    "BOS", "NYY", "OF", 4900, .260, .330, .500, .060, .260, "R"),
    ("Teoscar Hernandez","LAD", "SF",  "OF", 5100, .268, .328, .508, .055, .230, "R"),
    ("Daulton Varsho",   "TOR", "MIN", "OF", 4700, .245, .325, .440, .042, .250, "L"),
    ("Byron Buxton",     "MIN", "TOR", "OF", 5300, .262, .330, .520, .062, .265, "R"),
    ("Lourdes Gurriel",  "ARI", "KC",  "OF", 4400, .278, .330, .450, .032, .180, "R"),
    ("Randy Arozarena",  "TB",  "BAL", "OF", 4800, .252, .340, .445, .038, .220, "R"),
    ("Seiya Suzuki",     "CHC", "STL", "OF", 4700, .272, .365, .460, .038, .215, "R"),
    ("Steven Kwan",      "CLE", "DET", "OF", 4500, .288, .365, .418, .018, .115, "L"),
    ("Michael Brantley", "HOU", "TEX", "OF", 3800, .278, .345, .420, .022, .135, "L"),
    ("Jake McCarthy",    "ARI", "KC",  "OF", 3700, .262, .322, .405, .022, .220, "L"),
    ("Jesse Winker",     "WSH", "PHI", "OF", 3900, .248, .355, .420, .030, .205, "L"),
    ("Carlos Santana",   "MIN", "TOR", "OF", 3700, .238, .340, .390, .028, .200, "S"),
]
