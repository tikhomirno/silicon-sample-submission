"""
Block 3 -- Persona generator.
=================================================================

PURPOSE
    Create the synthetic respondents: each gets demographics, a condition, and a
    unique profile_id. Writes pipeline/personas.csv -- the ASSIGNED half of the
    Tier-1 raw export (design + demographics). Block 4 takes each persona, runs
    the model to fill the 44 elicited items, and assembles the full 52-column
    raw export that `make clean` consumes.

WHAT WE CONTROL HERE (and disclose in registration.md, item C.4)
    The study population is US adults (the survey is US-framed; the real study
    quota-samples on race). The benchmark ships NO participant pool, so we build
    one. FIRST PASS = independent draws from CITABLE US-adult MARGINALS (Census
    ACS 2023 1-year, Gallup 2024, Pew 2022 -- see pipeline/demographics_sources.md).
    This ignores real-world CORRELATIONS
    (e.g. age x education x income); a later refinement could draw joint profiles
    from public microdata (ACS PUMS). Demographics are written as Qualtrics
    numeric CODES (the faithful export format); `clean.R` maps codes -> labels.

    Conditions are assigned BALANCED: exactly N_PER_CONDITION respondents per
    condition (control + 16 interventions), so every cell has equal n.

RUN
    python pipeline/make_personas.py [N_PER_CONDITION]      # default 50
OUTPUT
    pipeline/personas.csv   (+ a printed summary)
"""

from __future__ import annotations

import csv
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = Path(__file__).resolve().parent / "schema.json"
OUT = Path(__file__).resolve().parent / "personas.csv"

N_PER_CONDITION_DEFAULT = 50
SEED = 42

# --------------------------------------------------------------------------- #
# US-adult marginal distributions (code -> probability). CITABLE sources -- see #
# pipeline/demographics_sources.md for full provenance (table, year, URL,      #
# access date) and the income-bracket interpolation method. Summary:           #
#   age / sex / race / education / income .. U.S. Census Bureau, ACS 2023       #
#       1-year estimates (tables B01001, B03002, B15003, B19001), via the       #
#       Census API, accessed 2026-06-29.                                        #
#   party .............. Gallup, 2024 annual party affiliation (initial ID).    #
#   gender "Other" ...... Pew Research Center, 2022 (nonbinary adults).         #
# Independent draws -- this IGNORES real-world correlations (age x education x   #
# income x party); refine later with joint ACS PUMS microdata. Keys MUST match  #
# schema.json codes (build_personas() asserts this). Weights are normalized so  #
# they need not sum to exactly 1.                                               #
# --------------------------------------------------------------------------- #
MARGINALS = {
    # gender: ACS 2023 adult M/F ratio scaled to 99%; 1% "Other" (Pew 2022 nonbinary)
    "gender": {"1": 0.485, "2": 0.505, "3": 0.010},
    # race/ethnicity: ACS 2023 B03002 (NH White / NH Black / Hispanic / NH Asian / Other)
    "race": {"1": 0.571, "2": 0.118, "3": 0.194, "4": 0.059, "5": 0.057},
    # education 25+: ACS 2023 B15003 (<HS / HS-GED / some-college-or-assoc / BA / MA-or-prof / doctorate)
    "education": {"1": 0.102, "2": 0.259, "3": 0.277, "4": 0.218, "5": 0.126, "6": 0.017},
    # household income: ACS 2023 B19001, interpolated to the survey's brackets
    "income": {"1": 0.184, "2": 0.179, "3": 0.248, "4": 0.207, "5": 0.182},
    # party (initial self-ID, before leaners): Gallup 2024 annual; ~1% residual -> Other
    "party": {"1": 0.28, "2": 0.28, "3": 0.43, "4": 0.01},
}
# age bands among adults 18+: ACS 2023 B01001 (clean.R cuts age_band from year_birth)
AGE_BAND_MARGINALS = {"18-29": 0.200, "30-44": 0.260, "45-59": 0.232, "60+": 0.309}
AGE_BAND_RANGES = {"18-29": (18, 29), "30-44": (30, 44), "45-59": (45, 59), "60+": (60, 90)}
CURRENT_YEAR = 2026   # clean.R derives age = 2026 - year_birth

PERSONA_COLUMNS = ["profile_id", "condition", "gender", "year_birth",
                   "race", "education", "income", "party"]


def _load_schema() -> dict:
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


def _validate_against_schema(schema: dict) -> None:
    """Fail loudly if our marginal codes drift from the schema's demographic codes."""
    demo_codes = {d["qualtrics_label"]: set(d["scale"]["codes"])
                  for d in schema["demographics"] if d["scale"]["kind"] == "categorical"}
    for name, dist in MARGINALS.items():
        assert name in demo_codes, f"{name} not a schema demographic"
        assert set(dist) == demo_codes[name], (
            f"{name} codes {set(dist)} != schema codes {demo_codes[name]}")
    assert set(AGE_BAND_MARGINALS) == set(AGE_BAND_RANGES), "age_band marginal/range mismatch"


def _weighted(rng: random.Random, dist: dict[str, float]) -> str:
    return rng.choices(list(dist), weights=list(dist.values()), k=1)[0]


def build_personas(n_per_condition: int = N_PER_CONDITION_DEFAULT,
                   seed: int = SEED) -> list[dict]:
    schema = _load_schema()
    _validate_against_schema(schema)
    conditions = schema["conditions"]["all"]            # 17 canonical labels
    rng = random.Random(seed)

    rows: list[dict] = []
    pid = 0
    for cond in conditions:
        for _ in range(n_per_condition):
            pid += 1
            band = _weighted(rng, AGE_BAND_MARGINALS)
            age = rng.randint(*AGE_BAND_RANGES[band])
            rows.append({
                "profile_id": f"p{pid:05d}",
                "condition": cond,
                "gender": _weighted(rng, MARGINALS["gender"]),
                "year_birth": str(CURRENT_YEAR - age),
                "race": _weighted(rng, MARGINALS["race"]),
                "education": _weighted(rng, MARGINALS["education"]),
                "income": _weighted(rng, MARGINALS["income"]),
                "party": _weighted(rng, MARGINALS["party"]),
            })
    return rows


def main() -> list[dict]:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else N_PER_CONDITION_DEFAULT
    rows = build_personas(n)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=PERSONA_COLUMNS)
        w.writeheader()
        w.writerows(rows)

    schema = _load_schema()
    n_cond = len(schema["conditions"]["all"])
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"  {len(rows)} personas = {n} per condition x {n_cond} conditions  (seed={SEED})")
    # quick marginal tallies (decoded to labels for readability)
    code2lab = {d["qualtrics_label"]: d["scale"]["codes"]
                for d in schema["demographics"] if d["scale"]["kind"] == "categorical"}
    for name in ("gender", "race", "education", "income", "party"):
        tally: dict[str, int] = {}
        for r in rows:
            lab = code2lab[name][r[name]]
            tally[lab] = tally.get(lab, 0) + 1
        pretty = ", ".join(f"{lab.split(' /')[0].split(' (')[0]}={c/len(rows):.0%}"
                           for lab, c in tally.items())
        print(f"  {name:9}: {pretty}")
    return rows


if __name__ == "__main__":
    main()
