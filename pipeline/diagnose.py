"""
Block 4 -- Simulation diagnostics (spread & skew).
=================================================================

Cleans a sim run's raw_export.csv into the 13 scored outcomes (via the real
scripts/clean.R) and reports:
  * parse-failure rate (from logs.jsonl)
  * overall per-outcome distribution (mean / sd / min / max / n-distinct)
  * WITHIN-CONDITION spread (mean SD across cells) -- needs >1 respondent/condition
  * by-PARTY means of headline outcomes  -- the realism/skew check
  * newsletter sign-up rate, mean donation

Use it to judge whether temperature gives plausible spread and whether the model
differentiates personas (e.g. do Republicans show lower trust?) before scaling.

RUN
    python pipeline/diagnose.py                 # uses pipeline/sim_out
    python pipeline/diagnose.py --in pipeline/sim_out
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PIPE = Path(__file__).resolve().parent

OUTCOMES = ["trust_multidimensional", "trust_post", "distrust_post",
            "funding_perceptions", "policy_role_mean", "inst_trust_mean",
            "belief_post", "concern_mean", "policy_general",
            "policy_specific_mean", "behavior_mean", "donation_ams",
            "newsletter_signup"]
HEADLINE = ["trust_multidimensional", "distrust_post", "belief_post",
            "policy_general", "donation_ams", "newsletter_signup"]


def clean_to_df(raw_csv: Path) -> pd.DataFrame:
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "clean.csv"
        r = subprocess.run(["Rscript", "scripts/clean.R", str(raw_csv), str(out)],
                           cwd=ROOT, capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit("clean.R failed:\n" + r.stderr[-1000:])
        return pd.read_csv(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="indir", default=str(PIPE / "sim_out"))
    args = ap.parse_args()
    indir = Path(args.indir)
    raw_csv, log_path = indir / "raw_export.csv", indir / "logs.jsonl"

    # parse-failure rate
    if log_path.exists():
        logs = [json.loads(l) for l in log_path.open(encoding="utf-8")]
        n_fail = sum(1 for l in logs if l["parse_issues"])
        print(f"respondents: {len(logs)} | with any parse issue: {n_fail} "
              f"({n_fail/len(logs):.1%})")

    df = clean_to_df(raw_csv)
    n_per_cond = df.groupby("condition").size()
    print(f"cleaned rows: {len(df)} | conditions: {df['condition'].nunique()}/17 "
          f"| respondents per condition: min={n_per_cond.min()} max={n_per_cond.max()}")

    print("\n== OVERALL distribution per outcome ==")
    desc = df[OUTCOMES].agg(["mean", "std", "min", "max"]).T
    desc["n_distinct"] = [df[c].nunique() for c in OUTCOMES]
    print(desc.round(1).to_string())

    print("\n== WITHIN-CONDITION spread (avg SD across the 17 cells) ==")
    if n_per_cond.max() > 1:
        within = df.groupby("condition")[OUTCOMES].std().mean()
        print(within.round(1).to_string())
        print("  (near 0 = respondents in a cell answer identically -> raise temperature)")
    else:
        print("  N/A -- only 1 respondent per condition. Run a spread probe "
              "(many respondents in one condition) to measure this.")

    if "party" in df.columns:
        print("\n== by PARTY: mean of headline outcomes (skew check) ==")
        by = df.groupby("party")[HEADLINE].mean()
        by.insert(0, "n", df.groupby("party").size())
        print(by.round(1).to_string())
        print("  (expect Republicans notably lower on trust/belief/policy if persona "
              "steering works; flat rows = weak differentiation)")

    print("\n== behavioral ==")
    print(f"  newsletter sign-up rate: {df['newsletter_signup'].mean():.1%}")
    print(f"  mean donation (0-10):    {df['donation_ams'].mean():.2f}")


if __name__ == "__main__":
    main()
