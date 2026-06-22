# Silicon Sample Benchmark — submission template

This repository **is** a submission to the [Silicon Sample Benchmark](https://janpfander.github.io/llm_predictions_megastudy/):
a multi-team benchmark of AI approaches for predicting the results of a behavioral megastudy on
trust in climate scientists, *before* the human data are revealed.

Clone it (or click **“Use this template”** on GitHub), drop in your predictions, edit two files, run
one check, and release it to Zenodo. The repo ships with a **random example submission** so a fresh
clone is already valid — run `make check` to see the green target state, then replace it with your own.

> The numbers in the example are random placeholders with **no real effects** — for format only.

## Quickstart

1. **Get your own copy** — “Use this template” on GitHub, or `git clone` and re-init.
2. **Build predictions** with any AI-based approach (never any human outcome data). See the survey in
   `survey/` and the variable dictionary in `codebook.csv`.
3. **Produce your file(s):**
   - **Tier 1** (individual-level): run the survey, then clean your raw export →
     `make clean INPUT=your_raw_export.csv` (writes `predictions/<team_id>_T1_primary_v1.csv`).
   - **Tier 2 / 3**: write the cell- or effect-level CSV(s) directly (see the matching `example_*`
     file already in `predictions/`).
4. **Edit `metadata.json`** (team, tier, models, disclosure class, …) and fill **`registration.md`**
   (the reporting checklist; ★ items must be public).
5. **Delete the examples:** `predictions/` ships with one `example_*` file per tier so you can see
   each format. Before depositing, **remove every `example_*` file** and leave only your own.
6. **Check it:** `make check` — fix anything it flags until it passes.
7. **Deposit:** release this repo to Zenodo and email the DOIs + SHA-256 hashes to the core team
   **before the prediction lock (August 30, 2026)**.

No `make`? Use `Rscript scripts/check.R` and `Rscript scripts/clean.R your_raw_export.csv`.
Requires R with `tidyverse`, `jsonlite`, `digest`.

## What you edit vs. what ships

| Path | Role |
|---|---|
| `metadata.json` | **edit** — machine-readable submission metadata; include `code_repository` (and optional `code_doi`) linking the code that generated your predictions |
| `registration.md` | **edit** — GUIDE-LLM-extended reporting checklist |
| `predictions/` | **edit** — your prediction file(s); ships with one `example_*` per tier (delete them before depositing) |
| `profiles/` | optional — drop your own `profiles.csv` here if you used custom profiles |
| `survey/` | reference — `survey.qsf` (Qualtrics import) and `survey.json` (same instrument, readable without Qualtrics) are the full instrument; `questionnaire.txt` is a plain-text rendering; `example_raw_export.csv` is a sample export to test `make clean` |
| `codebook.csv` | reference — every variable: Qualtrics label → target label, wording, outcome |
| `scripts/` | the engine you run — `check.R`, `clean.R`, and `lib/` internals; do not edit |

## Commands

| Command | What it does |
|---|---|
| `make check` | Verifies the required files exist; validates `metadata.json`, the file name, the SHA-256, the per-tier data structure, coverage, and value ranges. Prints **PASS / PASS-WITH-WARNINGS / FAIL**. |
| `make clean INPUT=raw.csv` | Tier-1 only: renames a raw survey export to the target schema and builds the constructed scale variables (`trust_multidimensional`, the `*_mean` composites, reverse-coded funding, `age_band`). |

## Prediction file naming

```
<team_id>_T<tier>_<primary|secondary-k>_v<n>.csv          # Tier 1 and Tier 3
<team_id>_T2_<primary|secondary-k>_v<n>_cells_main.csv    # Tier 2
<team_id>_T2_<primary|secondary-k>_v<n>_cells_moderator.csv
```

`team_id` must match `metadata.json`. Coverage: 16 interventions + control, 13 outcomes. The exact
column schema for each tier is enforced by `make check` (see the `example_*` files in `predictions/`
and `scripts/lib/submission_spec.R`).

## The survey

The full instrument is provided as two files. **Both encode the same survey**; they differ only in
format and intended use:

| | `survey/survey.qsf` | `survey/survey.json` |
|---|---|---|
| **What it is** | Qualtrics' proprietary survey-export file | Qualtrics' documented Survey-Definitions API output |
| **Format** | JSON, but an undocumented proprietary structure | JSON with a documented schema (`result.Questions`, `result.Blocks`, `result.SurveyFlow`, …) |
| **Best for** | re-importing into Qualtrics to **run** the survey yourself | **reading / parsing** the instrument programmatically — e.g. individual participant simulations that need the items, response scales, block/flow order, branching and randomization a respondent actually saw |
| **Qualtrics license** | required (to import and run) | not required (it is plain JSON anyone can read) |

In short: use `survey.qsf` if you want to *run* the survey in Qualtrics; use `survey.json`
if you want to *read* it without a Qualtrics account.

> **Scope note.** These files are the reduced *LLM-simulation* instrument: respondents are routed
> through the non-interactive conditions only (assigned by a block randomizer); the interactive chatbot
> arms have been removed. The conditions and outcomes you are scored on are defined in `codebook.csv`
> and `scripts/lib/submission_spec.R`; treat those as authoritative for scope, and the two survey files as
> the faithful record of the instrument.

A human-readable rendering is also provided as `survey/questionnaire.txt` (every item as
`[label] question` + response values, plus the condition labels and intervention stimulus texts).

Tier-1 runs export raw Qualtrics column names; `make clean` maps them to the analysis schema
documented in `codebook.csv`.

## More

Tiers, scoring, disclosure classes, and the full timeline are described in the
[call for participation](https://janpfander.github.io/llm_predictions_megastudy/). Questions:
see the call's Contact page.
