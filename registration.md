# Silicon Sample Benchmark — method registration form

Fill in every item before the prediction lock and deposit this file on Zenodo. Items marked **★**
must be disclosed **fully publicly** (never escrowed or withheld). Items not applicable to your
approach: write `N/A`. When several models serve different pipeline stages, complete the model
sections (B) once per model. See the call's *Disclosure policy* for escrow rules.

---

## 0 · Approach identity and output
- **0.1 Team ★** — name, members, affiliations, corresponding contact:
- **0.2 Plain-language summary ★** — one paragraph, what the approach does (not how):
- **0.3 Submission tier & approach family ★** — tier (1/2/3); family (e.g. per-respondent simulation / agent / direct forecast; single model / ensemble / multi-agent; zero-shot / literature-conditioned):
- **0.4 Pipeline diagram** — ordered steps from raw inputs to submitted file:
- **0.5 Coverage ★** — number of respondents/cells/estimates; mapping to conditions; coverage of the 16 interventions and 13 outcomes (all, or a declared subset + justification):

## A · Scope of LLM use
- **A.1 Purpose** — every workflow stage where LLMs are used:
- **A.2 Degree of automation ★** — confirm fully automated, no human in the loop at prediction time; note any exception:

## B · Model / system details (once per model)
- **B.1 Model name(s)** — exact identifiers incl. provider, size, version/timestamp, source link:
- **B.2 Access & context mode** — API/web/local; API name + version; chat vs stateless; exact call dates:
- **B.3 Configuration** — temperature, top-p/top-k, max tokens, penalties, stop sequences, seeds, reasoning effort, completions per item:
- **B.4 Customization** — fine-tuning, RAG, prompt optimization, tool use, web search, agentic scaffolds (cross-ref F):
- **B.5 Persistent memory** — across interactions? what persisted:
- **B.6 Inference stack** — for local models: serving framework + version, quantization, hardware:
- **B.7 Ensembles** — members + exact aggregation rule:

## C · Prompts
- **C.1 Exact prompts** — verbatim text or link to deposited file; were they iteratively refined? pre-specified vs in response to outputs:
- **C.2 System-wide instructions**:

## C · Persona / profile construction (Tiers 1–2)
- **C.3 Profile source** — provided GSS pool / ANES / Census / other / synthetic / none; register any deviation from the published pool incl. condition assignments:
- **C.4 Profile verbalization** — which variables, rendered how (template vs generated narrative; if generated: model + prompt):
- **C.5 Assignment & weighting** — number of personas, assignment to conditions, reuse, weighting/matching:

## C · Stimulus and survey administration
- **C.6 Stimulus presentation** — verbatim vs paraphrase; how state-contingent content is handled:
- **C.7 Survey walk-through** — one item/call vs blocks vs whole survey; context carry-over; item/option ordering & randomization; scale display; attention/comprehension handling:
- **C.8 Response elicitation** — free text / constrained choice / structured output / token log-probabilities (if logprobs: normalization & mapping):

## D · Stochasticity and aggregation
- **D.1 Runs & seeds** — runs per respondent/item/estimate; seeds; reproducibility under identical settings:
- **D.2 Aggregation rule** — how multiple generations become submitted values (mean/median/mode/first/sampled/…):

## E · Validation & post-processing
- **E.1 Human validation** — any human review of outputs (often N/A):
- **E.2 Post-processing** — parsing rules; handling of refusals/malformed/missing/out-of-range; exclusions; effective N per condition:
- **E.3 Calibration corrections** — any post-hoc scaling/shifting/debiasing and exactly what data it was fit on (cross-ref F/G):

## F · Learning and conditioning components
- **F.1 Fine-tuning data** — exact corpus (hashes/DOIs), hyperparameters, checkpoints:
- **F.2 Context & retrieval corpora** — exact document set in context / indexed, archived in the deposit:

## G · Data inputs, blinding, and competing interests
- **G.1 Competing interests ★** — funding, in-kind compute/model access, relationships with LLM-interested entities:
- **G.2 External human data** — all external human datasets that informed the approach anywhere (training/fine-tuning/retrieval/ICL/calibration):
- **G.3 Blinding attestation ★** — **mandatory.** Signed attestation that no team member accessed, solicited, or was shown any human outcome data from this study, including pilots, before the prediction lock:
- **G.4 Contamination note** — training cutoff of every model vs public release dates of this project's materials; note any known exposure:

## H · Internal selection procedure
- **H.1 Design-space search** — how the final pipeline was chosen: how many configurations tried, internal validation criterion, what data it ran against:

## I · Reproducibility & frozen artifacts
- **I.1 Code & materials** — link/DOI, secrets removed, determinism/seeds documented (also record the link in `metadata.json` → `code_repository` / `code_doi`):
- **I.2 Raw output logs** — complete unprocessed model responses archived, hashed, time-stamped:
- **I.3 Computational resources** — API-call counts, total tokens, cost, compute time:
