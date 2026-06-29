"""
Block 2 -- Map the raw schema.
=================================================================

PURPOSE
    Produce ONE machine-readable, human-auditable description of *exactly* what a
    Tier-1 raw Qualtrics export must contain, so the later simulation step
    (Block 4) knows precisely which questions to ask the model and on what
    response scale -- and so `make clean` will accept the result without error.

WHY THIS EXISTS
    A Tier-1 submission is built by:
        simulate respondents  ->  raw_data_deposit/<file>.csv  ->  `make clean`
    `make clean` (scripts/lib/clean_lib.R) expects a file that carries the survey's
    *Qualtrics* column names (e.g. `trust_competent_1`, `policy_1_1`, `funding_5`,
    `donation`, `newsletter`). It then renames them to analysis labels and builds
    the constructed/scored variables (`trust_multidimensional`, the `*_mean`
    composites, reverse-coded `funding_perceptions`, `age_band`, ...).

    So our job in Block 2 is only to nail down the INPUT contract: the set of raw
    columns + each item's response scale. Everything downstream reads schema.json.

SOURCES OF TRUTH (read, never guessed)
    * codebook.csv ............ every variable: qualtrics_label, target_label,
                                question_text, response_options, section.
    * raw_data_deposit/example_raw_export.csv .. canonical COLUMN ORDER + which
                                columns are Qualtrics "system" columns (optional).
    * scripts/lib/clean_lib.R . the demographic numeric-code -> label maps and the
                                composite definitions, transcribed below and
                                CROSS-CHECKED by notebooks/block2_schema_checks.ipynb.

RUN
    python pipeline/build_schema.py
OUTPUT
    pipeline/schema.json   (+ a printed summary)
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path


# --------------------------------------------------------------------------- #
# Paths                                                                        #
# --------------------------------------------------------------------------- #
ROOT = Path(__file__).resolve().parent.parent          # repo root (parent of pipeline/)
CODEBOOK = ROOT / "codebook.csv"
EXAMPLE_RAW = ROOT / "raw_data_deposit" / "example_raw_export.csv"
OUT = Path(__file__).resolve().parent / "schema.json"


# --------------------------------------------------------------------------- #
# Constants transcribed from scripts/lib/clean_lib.R                           #
# (kept here so Block 4 needs no R; the checks notebook re-extracts these from  #
#  R and asserts they still match, so drift is caught automatically.)          #
# --------------------------------------------------------------------------- #

# clean_lib.R lines 76-90 -- numeric Qualtrics code -> label.
DEMOGRAPHIC_MAPS = {
    "gender": {"1": "Male", "2": "Female", "3": "Other"},
    "race": {
        "1": "White / Caucasian",
        "2": "Black / African American",
        "3": "Hispanic / Latino",
        "4": "Asian / Asian American",
        "5": "Other",
    },
    "education": {
        "1": "Less than high school",
        "2": "High school diploma / GED",
        "3": "Some college or Associate's degree",
        "4": "Bachelor's degree",
        "5": "Master's degree / Professional degree",
        "6": "Doctorate degree / Ph.D.",
    },
    "income": {
        "1": "Less than $30,000",
        "2": "$30,000 to $55,999",
        "3": "$56,000 to $99,999",
        "4": "$100,000 to $167,999",
        "5": "$168,000 or more",
    },
    "party": {"1": "Republican", "2": "Democrat", "3": "Independent", "4": "Other"},
}

# Columns we ASSIGN ourselves (not asked of the model, not in the codebook).
# `condition` + `profile_id` are Qualtrics "embedded data" in the real instrument.
DESIGN_COLUMNS = {
    "profile_id": "Unique respondent id you assign (unique within the submission).",
    "condition": "One of the 17 canonical condition titles (control + 16 interventions).",
}

# The exact, allowed values of the `condition` column -- the domain of that part
# of the raw contract. Transcribed verbatim from scripts/lib/submission_spec.R
# (the 16 text-intervention titles + "control"); the checks notebook re-extracts
# sst$conditions from R and asserts these still match, so drift is caught.
# Block 3 assigns each respondent one of these; Block 4 injects the matching
# intervention's stimulus text (control gets none). check.R/clean.R require an
# EXACT string match, so do not edit these casually.
CONTROL = "control"
INTERVENTIONS = [
    "Corporate reliance",
    "Social justice",
    "Interview Prof. Maraun",
    "Funding",
    "Oil industry misinformation",
    "Measurement & modeling (1)",
    "Former skeptics",
    "High public trust",
    "Measurement & modeling (2)",
    "Peer-review",
    "Scientist community helpers",
    "Consensus",
    "Portrait Prof. Cherry",
    "Model accuracy",
    "Interview Prof. Sebille",
    "Extreme weather predictions",
]
CONDITIONS = [CONTROL] + INTERVENTIONS

# Demographics live in codebook section A but are ASSIGNED from each synthetic
# persona rather than elicited from the model.
DEMOGRAPHIC_LABELS = set(DEMOGRAPHIC_MAPS) | {"year_birth"}

# The 13 preregistered, scored outcomes and how `make clean` produces each, in
# terms of the RAW qualtrics_labels they depend on (transcribed from clean_lib.R
# lines 167-194 and submission_spec.R). `components` are raw columns that must be
# present in the export for the outcome to be computable.
SCORED_OUTCOMES = {
    "trust_multidimensional": {
        "kind": "composite",
        "note": "PRIMARY. mean of 4 subscales (competence/integrity/benevolence/"
                "openness); each subscale = mean of its 3 items.",
        "components": [
            "trust_competent_1", "trust_intelligent_1", "trust_qualified_1",
            "trust_honest_1", "trust_ethical_1", "trust_sincere_1",
            "trust_concerned_1", "trust_improve_1", "trust_considerate_1",
            "trust_feedback_1", "trust_transparent_1", "trust_attention_1",
        ],
    },
    "trust_post": {"kind": "single", "components": ["trust_post_1"]},
    "distrust_post": {"kind": "single", "components": ["distrust_1"]},
    "funding_perceptions": {
        "kind": "recode", "note": "funding_perceptions = 100 - funding_5",
        "components": ["funding_5"],
    },
    "policy_role_mean": {
        "kind": "composite",
        "components": ["policy_1_1", "policy_2_1", "policy_3_1", "policy_4_1"],
    },
    "inst_trust_mean": {
        "kind": "composite",
        "components": ["inst_trust_epa_1", "inst_trust_nasa_1", "inst_trust_noaa_1",
                       "inst_trust_uni_1", "inst_trust_gov_1"],
    },
    "belief_post": {"kind": "single", "components": ["belief_post_1"]},
    "concern_mean": {
        "kind": "composite",
        "components": ["concern_1_1", "concern_2_1", "concern_3_1"],
    },
    "policy_general": {"kind": "single", "components": ["policy_general_1"]},
    "policy_specific_mean": {
        "kind": "composite",
        "components": [f"policy_specific_{i}_1" for i in range(1, 8)],
    },
    "behavior_mean": {
        "kind": "composite",
        "components": ["individual_meat_1", "individual_transport_1",
                       "individual_solar_1", "individual_fly_1",
                       "individual_talk_1", "individual_donate_1"],
    },
    "donation_ams": {"kind": "single", "components": ["donation"]},
    "newsletter_signup": {
        "kind": "recode", "note": "Yes -> 1, No -> 0",
        "components": ["newsletter"],
    },
}


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #
def load_codebook() -> list[dict]:
    with CODEBOOK.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def parse_anchors(response_options: str) -> list[dict]:
    """Pull '<number> = <label>' anchors out of a slider's response_options text.

    e.g. '0 = Very incompetent ... 100 = Very competent'
         -> [{'value': 0, 'label': 'Very incompetent'},
             {'value': 100, 'label': 'Very competent'}]
    """
    pairs = re.findall(r"(\d+)\s*=\s*([^,…]+?)(?=\s*(?:,|…|$))", response_options)
    return [{"value": int(v), "label": t.strip()} for v, t in pairs]


def group_of(target_label: str) -> str:
    """A human-friendly grouping for an elicited item (block on the survey)."""
    for prefix in ("trust_competence", "trust_integrity", "trust_benevolence",
                   "trust_openness", "policy_role", "policy_specific",
                   "inst_trust", "concern", "behavior"):
        if target_label.startswith(prefix):
            return prefix
    return {
        "trust_post": "trust", "distrust_post": "trust",
        "funding_perceptions": "funding", "belief_post": "belief",
        "policy_general": "policy_general",
        "donation_ams": "behavioral", "newsletter_signup": "behavioral",
    }.get(target_label, target_label)


def scale_for(qualtrics_label: str, response_options: str) -> dict:
    """Classify the response scale of an ELICITED item (asked of the model)."""
    if qualtrics_label == "donation":
        return {"kind": "integer", "min": 0, "max": 10, "unit": "USD",
                "raw_options": response_options}
    if qualtrics_label == "newsletter":
        return {"kind": "binary", "options": ["Yes", "No"],
                "recode": {"Yes": 1, "No": 0}, "raw_options": response_options}

    # Everything else in section A (besides demographics) is a 0-100 slider.
    scale = {"kind": "slider", "min": 0, "max": 100, "raw_options": response_options}
    anchors = parse_anchors(response_options)
    low = next((a["label"] for a in anchors if a["value"] == 0), None)
    high = next((a["label"] for a in anchors if a["value"] == 100), None)
    if low:
        scale["low_anchor"] = low
    if high:
        scale["high_anchor"] = high
    if len(anchors) > 2:                       # e.g. funding_5 has a midpoint
        scale["anchors"] = anchors
    if qualtrics_label == "funding_5":
        scale["reverse_coded_in_cleaning"] = "funding_perceptions = 100 - funding_5"
    return scale


# --------------------------------------------------------------------------- #
# Build                                                                        #
# --------------------------------------------------------------------------- #
def build_schema() -> dict:
    rows = load_codebook()
    measured = [r for r in rows if r["section"].startswith("A.")]   # raw items
    constructed = [r for r in rows if r["section"].startswith("B.")]  # built in clean

    demographics, elicited = [], []
    for r in measured:
        ql, tl = r["qualtrics_label"], r["target_label"]
        opts, q = r["response_options"], r["question_text"]
        if ql in DEMOGRAPHIC_LABELS:
            entry = {"qualtrics_label": ql, "target_label": tl, "role": "assigned",
                     "question_text": q, "raw_options": opts}
            if ql == "year_birth":
                # clean.R derives age = 2026 - year_birth, then age_band.
                # 18..100 year-olds in 2026 => birth years 1926..2008.
                entry["scale"] = {"kind": "year", "min": 1926, "max": 2008}
            else:
                entry["scale"] = {"kind": "categorical", "codes": DEMOGRAPHIC_MAPS[ql]}
            demographics.append(entry)
        else:
            elicited.append({
                "qualtrics_label": ql, "target_label": tl, "role": "elicited",
                "group": group_of(tl), "question_text": q,
                "scale": scale_for(ql, opts),
            })

    # ---- Canonical column ORDER + which columns are optional system columns. -- #
    raw_item_labels = {r["qualtrics_label"] for r in measured} | set(DESIGN_COLUMNS)
    raw_export_columns, system_columns = _column_order(raw_item_labels)

    schema = {
        "meta": {
            "tier": 1,
            "generated_by": "pipeline/build_schema.py",
            "generated_from": [
                "codebook.csv",
                "raw_data_deposit/example_raw_export.csv (column order only)",
                "scripts/lib/clean_lib.R (demographic maps + composites)",
            ],
            "n_raw_export_columns": len(raw_export_columns),
            "n_elicited_items": len(elicited),
            "n_demographics": len(demographics),
            "n_conditions": len(CONDITIONS),
            "n_interventions": len(INTERVENTIONS),
            "scored_outcomes": list(SCORED_OUTCOMES),
            "how_to_use": (
                "Write one CSV row per synthetic respondent containing exactly "
                "`raw_export_columns`. Assign `design_columns` + `demographics`; "
                "ask the model for `elicited_items` on the stated scale. Save into "
                "raw_data_deposit/ and run `make clean` -> it builds the scored "
                "outcomes and the analysis-ready predictions file."
            ),
        },
        "design_columns": [
            {"column": c, "role": "assigned", "description": d}
            for c, d in DESIGN_COLUMNS.items()
        ],
        "conditions": {
            "all": CONDITIONS,                 # the 17 allowed values of `condition`
            "control": CONTROL,
            "interventions": INTERVENTIONS,    # the 16 scored interventions
            "note": "Exact strings required by clean.R/check.R. Block 4 injects "
                    "the matching intervention stimulus text; control gets none.",
        },
        "demographics": demographics,
        "elicited_items": elicited,
        "raw_export_columns": raw_export_columns,
        "system_columns_optional": system_columns,
        "constructed": {
            "scored_outcomes": SCORED_OUTCOMES,
            "all_constructed_in_cleaning": [
                {"target_label": r["target_label"],
                 "definition": r["question_text"]} for r in constructed
            ],
        },
    }
    return schema


def _column_order(raw_item_labels: set[str]) -> tuple[list[str], list[str]]:
    """Use the example export's header for column order if available; classify
    columns not in the codebook (+ design columns) as optional system columns.
    Fall back to a sensible fixed order if the example file is absent."""
    if EXAMPLE_RAW.exists():
        with EXAMPLE_RAW.open(newline="", encoding="utf-8") as f:
            header = next(csv.reader(f))
        required = [c for c in header if c in raw_item_labels]
        system = [c for c in header if c not in raw_item_labels]
        return required, system

    # Fallback: example deleted (e.g. after Block 6). Reconstruct from codebook.
    fixed_front = ["condition", "profile_id", "gender", "year_birth", "race",
                   "education", "income", "party", "donation", "newsletter"]
    rest = [r["qualtrics_label"] for r in load_codebook()
            if r["section"].startswith("A.") and r["qualtrics_label"] not in fixed_front]
    return fixed_front + rest, []


def main() -> dict:
    schema = build_schema()
    OUT.write_text(json.dumps(schema, indent=2, ensure_ascii=False), encoding="utf-8")

    m = schema["meta"]
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"  raw export columns : {m['n_raw_export_columns']}  "
          f"(= {len(schema['design_columns'])} design + {m['n_demographics']} "
          f"demographic + {m['n_elicited_items']} elicited)")
    print(f"  elicited items     : {m['n_elicited_items']} asked of the model")
    print(f"  conditions         : {m['n_conditions']} "
          f"(control + {m['n_interventions']} interventions)")
    print(f"  scored outcomes    : {len(m['scored_outcomes'])}")
    print(f"  optional system cols: {len(schema['system_columns_optional'])} "
          "(Qualtrics metadata; clean.R strips these)")
    # quick scale tally
    kinds: dict[str, int] = {}
    for it in schema["elicited_items"]:
        kinds[it["scale"]["kind"]] = kinds.get(it["scale"]["kind"], 0) + 1
    print(f"  elicited scales    : {kinds}")
    return schema


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
