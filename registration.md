# Silicon Sample Benchmark — method registration form

Fill in every item before the prediction lock; this file ships inside your repo's Zenodo release
(see the README's *Deposit* step). This form covers **one entry** (one repo / one Zenodo release,
`primary` or `secondary-k` — see the README's *What counts as a submission*); if you submit several
entries, fill one form per entry. Items marked **★**
must be disclosed **fully publicly** (never escrowed or withheld). Items not applicable to your
approach: write `N/A`. When several models serve different pipeline stages, complete the model
sections (B) once per model. See the call's *Disclosure policy* for escrow rules.

---

## 0 · Approach identity and output
- **0.1 Team ★** — name, members, affiliations, corresponding contact: Taisiia Tikhomirova, Max Planck Institute for Human Development (MPIB), Berlin. Corresponding contact: tikhomirova@mpib-berlin.mpg.de (sole team member).
- **0.2 Plain-language summary ★** — one paragraph, what the approach does (not how): We build a synthetic sample of U.S. adults and have one open-weights language model answer the study's survey as each synthetic respondent, given a demographic profile and (in intervention conditions) the same stimulus a human would read. The individual responses are our Tier-1 predictions.
- **0.3 Submission tier & approach family ★** — Tier **1** (individual-level); per-respondent simulation; single model; zero-shot.
- **0.4 Pipeline diagram** — ordered steps from raw inputs to submitted file:
  1. `build_schema.py` — derive raw column/scale contract from `codebook.csv`.
  2. `extract_conditions.py` — extract 16 intervention stimulus texts from the survey.
  3. `make_personas.py` — sample personas from public demographic marginals; assign condition + id.
  4. `simulate.py` — per persona: prompt (persona + stimulus) → model → parse 44 items → raw export.
  5. `clean.R` (`make clean`) — build the 13 scored outcomes → `predictions/tikhomirno_T1_primary_v1.csv`.
  6. `check.R` (`make check`) → GitHub release → Zenodo.
- **0.5 Coverage ★** — 850 synthetic respondents, 50 per condition, all **17 conditions** (control + 16 interventions), all **13 outcomes**. One respondent = one experiment in one condition.

## A · Scope of LLM use
- **A.1 Purpose** — The model is used at one stage only: generating each synthetic respondent's survey answers. All other steps are deterministic non-LLM code.
- **A.2 Degree of automation ★** — Fully automated; no human in the loop at prediction time. No exceptions.

## B · Model / system details (once per model)
- **B.1 Model name(s)** — Meta **Llama-3.1-8B-Instruct** (8.0B), run locally via Ollama tag `llama3.1:8b` (digest `46e0c10c039e`). Source: https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct
- **B.2 Access & context mode** — Local; Ollama v0.30.11 `/api/chat`; stateless single-turn (one independent chat per respondent); call date 2026-06-29.
- **B.3 Configuration** — temperature 0.9; top-p/top-k = provider default; max tokens = default; no penalties/stop sequences; per-respondent integer seed derived from `profile_id`; 1 completion per respondent; JSON-constrained output (`format: json`).
- **B.4 Customization** — N/A (zero-shot; no fine-tuning, RAG, tools, or web search).
- **B.5 Persistent memory** — N/A; each respondent is independent.
- **B.6 Inference stack** — Ollama v0.30.11 (llama.cpp backend); quantization **Q4_K_M** (4-bit); hardware: Apple-silicon Mac.
- **B.7 Ensembles** — N/A (single model).

## C · Prompts
- **C.1 Exact prompts** — Built deterministically by `pipeline/simulate.py`; every prompt archived verbatim per respondent in `logs.jsonl`. Pre-specified; not refined against model outputs.
- **C.2 System-wide instructions** — System message casts the model as the persona ("answer as this person would, not as an AI"), states the response scales, and requires a JSON-only reply.
- **C.3 Prompt-design rationale** — Demographic conditioning (silicon sampling); structured JSON for reliable parsing; per-item scale anchors shown to keep answers in range.

## C · Persona / profile construction (Tiers 1–2)
- **C.4 Profile source** — Synthetic personas drawn from public aggregate marginals (independent draws): age/sex/race/education/income from U.S. Census ACS 2023 1-year; party from Gallup 2024; gender "Other" from Pew 2022. Full provenance in `pipeline/demographics_sources.md`. Conditions assigned balanced across all 17.
- **C.5 Profile verbalization** — The 6 scored demographics (gender, age, race, education, income, party) rendered via a fixed template (a bulleted "About you" list); not model-generated.
- **C.6 Assignment & weighting** — 850 personas, balanced 50 per condition across all 17, no reuse, no weighting.

## C · Stimulus and survey administration
- **C.7 Stimulus presentation** — Verbatim intervention text. Control: no climate stimulus. State-contingent "Extreme weather predictions": state-agnostic Case 4 passage for all respondents. Predict-then-reveal items (Funding/Consensus/High public trust): full text incl. feedback presented as read; embedded responses not elicited.
- **C.8 Survey walk-through** — Whole survey in one call; single turn (no carry-over); fixed canonical item order, no randomization; scales shown as 0–100 sliders / $0–10 / Yes-No; attention/comprehension items not modeled.
- **C.9 Response elicitation** — Constrained structured output (single JSON object keyed by item id); numeric for sliders/donation, "Yes"/"No" for newsletter; no log-probabilities.

## D · Stochasticity and aggregation
- **D.1 Runs & seeds** — 1 generation per respondent; per-respondent seed from `profile_id`; reproducible under identical model + settings + stack.
- **D.2 Aggregation rule** — N/A; one row per respondent is submitted (no aggregation by us).

## E · Validation & post-processing
- **E.1 Human validation** — N/A.
- **E.2 Post-processing** — Parsed from JSON; out-of-range values clamped to scale; missing/malformed left blank; up to 2 retries on malformed JSON; no respondents excluded. Effective N per condition = 50 (850 respondents, 0 parse issues, no missing values).
- **E.3 Calibration corrections** — N/A.

## F · Learning and conditioning components
- **F.1 Fine-tuning data** — N/A.
- **F.2 Context & retrieval corpora** — N/A (only the benchmark's own survey/stimulus text is in context).

## G · Data inputs, blinding, and competing interests
- **G.1 Competing interests ★** — None.
- **G.2 External human data** — Only public aggregate demographic statistics (Census ACS 2023; Gallup 2024; Pew 2022) used to build personas; no individual-level or study outcome data. Survey materials are the benchmark's own.
- **G.3 Blinding attestation ★** — "No team member accessed, solicited, or was shown any human outcome data from this study (including pilots) before the prediction lock." Signed: **Taisiia Tikhomirova (MPIB), 2026-06-30** _(update to the deposit date if later)_.
- **G.4 Contamination note** — Llama-3.1 training cutoff ≈ December 2023; no known exposure to this study's specific materials.

## H · Internal selection procedure
- **H.1 Design-space search** — Minimal. Validated via schema/`clean.R` integration tests and a 17-respondent pilot; selection criteria were format validity, parse-success rate, and plausible response spread. No outcome data used.

## I · Reproducibility & frozen artifacts
- **I.1 Code & materials** — https://github.com/tikhomirno/silicon-sample-submission ; secrets removed (Census API key not committed); seeds documented (per-respondent, from `profile_id`).
- **I.2 Raw output logs** — All raw model responses + prompts archived in `logs.jsonl` (one line per respondent); included in the Zenodo deposit and covered by the release hash.
- **I.3 Computational resources** — ~850 model calls (plus retries); local open-weights model, monetary cost ≈ $0; total tokens and wall-clock time _[from run]_.
