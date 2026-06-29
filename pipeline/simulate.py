"""
Block 4 -- Simulation harness (participant prompting).
=================================================================

For each persona in pipeline/personas.csv:
  1. build a participant prompt (system = the 6-demographic persona;
     user = condition stimulus [if any] + the 44 outcome questions),
  2. call an open model (default: llama3.1:8b via Ollama),
  3. parse the JSON answer, validate/clamp to each item's scale,
  4. log the RAW model response (Tier-1 deposits require raw logs),
  5. write one raw-export row (the 52 schema columns) for `make clean`.

Condition handling (Option A, expository): control gets no climate stimulus;
each intervention injects conditions.json[label]["stimulus_text"] verbatim
(including any reveal/feedback), framed as "earlier you read this".

The run is RESUMABLE and crash-safe: rows + logs are appended incrementally, and
re-running skips profile_ids already present in the output CSV.

RUN
    # quick pilot: one respondent per condition (17 calls)
    python pipeline/simulate.py --pilot
    # full run
    python pipeline/simulate.py
    # options
    python pipeline/simulate.py --limit 50 --model llama3.1:8b --temperature 0.9

OUTPUT  (under --out, default pipeline/sim_out/)
    raw_export.csv   one row per respondent, columns = schema raw_export_columns
    logs.jsonl       one line per respondent: prompt + raw response + parse status
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

import requests
from tqdm import tqdm

ROOT = Path(__file__).resolve().parent.parent
PIPE = Path(__file__).resolve().parent
SCHEMA = PIPE / "schema.json"
CONDITIONS = PIPE / "conditions.json"
PERSONAS = PIPE / "personas.csv"

PERSONA_FIELDS = ["profile_id", "condition", "gender", "year_birth",
                  "race", "education", "income", "party"]
CURRENT_YEAR = 2026


# --------------------------------------------------------------------------- #
# Prompt construction                                                          #
# --------------------------------------------------------------------------- #
def _demo_labels(schema: dict) -> dict[str, dict[str, str]]:
    return {d["qualtrics_label"]: d["scale"]["codes"]
            for d in schema["demographics"] if d["scale"]["kind"] == "categorical"}


def build_system(persona: dict, demo: dict[str, dict[str, str]]) -> str:
    age = CURRENT_YEAR - int(persona["year_birth"])
    return (
        "You are taking part in a research survey as the following person. "
        "Answer every question exactly as this person would, staying in character.\n\n"
        "About you:\n"
        f"- Age: {age}\n"
        f"- Gender: {demo['gender'][persona['gender']]}\n"
        f"- Race/ethnicity: {demo['race'][persona['race']]}\n"
        f"- Education: {demo['education'][persona['education']]}\n"
        f"- Household income: {demo['income'][persona['income']]}\n"
        f"- Political party: {demo['party'][persona['party']]}\n\n"
        "You live in the United States. Answer from this person's perspective, "
        "not as an AI. Most items are 0-100 sliders; answer with a whole number "
        "in that range. Return ONLY a JSON object, nothing else."
    )


def build_question_block(schema: dict) -> tuple[str, list[dict]]:
    """Static text listing all 44 items with scales, + the parse spec per item."""
    lines = ["Answer every item below from your perspective as this person.",
             "Sliders are whole numbers 0-100. Respond with a SINGLE JSON object "
             "whose keys are exactly the ids shown (in quotes).", ""]
    spec = []
    last_group = None
    for it in schema["elicited_items"]:
        g, s, q, lab = it["group"], it["scale"], it["question_text"], it["qualtrics_label"]
        if g != last_group:
            lines.append(f"[{g}]")
            last_group = g
        if s["kind"] == "slider":
            lo, hi = s.get("low_anchor", "0"), s.get("high_anchor", "100")
            lines.append(f'  "{lab}": {q}  (0={lo} … 100={hi})')
            spec.append({"label": lab, "kind": "slider", "min": 0, "max": 100})
        elif s["kind"] == "integer":
            lines.append(f'  "{lab}": {q}  (whole number {s["min"]}-{s["max"]})')
            spec.append({"label": lab, "kind": "integer", "min": s["min"], "max": s["max"]})
        elif s["kind"] == "binary":
            lines.append(f'  "{lab}": {q}  (answer "Yes" or "No")')
            spec.append({"label": lab, "kind": "binary"})
    keys = ", ".join(f'"{i["label"]}"' for i in spec)
    lines += ["", f"Use exactly these {len(spec)} keys: {keys}"]
    return "\n".join(lines), spec


def build_user(condition: str, stimulus: str | None, question_block: str) -> str:
    if stimulus:
        return (f'Earlier in this survey you read the following:\n"""\n{stimulus}\n"""\n\n'
                f"Now please answer the following questions.\n\n{question_block}")
    return f"Please answer the following questions.\n\n{question_block}"


# --------------------------------------------------------------------------- #
# Model backends. Both return the model's raw text (expected to be JSON).       #
#   ollama : local dev on a Mac (http://localhost:11434)                        #
#   openai : any OpenAI-compatible endpoint -- e.g. a vLLM server on the GPU    #
#            cluster (http://localhost:8000/v1), or a hosted open-model provider #
# Same prompts/parsing/logging/resume either way; only the transport differs.   #
# --------------------------------------------------------------------------- #
def ollama_chat(messages, model, temperature, seed, host, api_key=None, timeout=300):
    r = requests.post(f"{host}/api/chat", timeout=timeout, json={
        "model": model, "messages": messages, "stream": False, "format": "json",
        "options": {"temperature": temperature, "seed": seed},
    })
    r.raise_for_status()
    return r.json()["message"]["content"]


def openai_chat(messages, model, temperature, seed, host, api_key=None, timeout=300):
    r = requests.post(f"{host}/chat/completions", timeout=timeout,
                      headers={"Authorization": f"Bearer {api_key or 'EMPTY'}"},
                      json={"model": model, "messages": messages,
                            "temperature": temperature, "seed": seed,
                            "response_format": {"type": "json_object"}})
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


BACKENDS = {"ollama": ollama_chat, "openai": openai_chat}
DEFAULT_HOST = {"ollama": "http://localhost:11434", "openai": "http://localhost:8000/v1"}


# --------------------------------------------------------------------------- #
# Parsing / validation                                                         #
# --------------------------------------------------------------------------- #
def parse_response(raw: str, spec: list[dict]) -> tuple[dict, list[str]]:
    values, issues = {}, []
    try:
        obj = json.loads(raw)
        if not isinstance(obj, dict):
            raise ValueError("not a JSON object")
    except Exception as e:
        return {}, [f"json_error:{e}"]

    for item in spec:
        lab, kind = item["label"], item["kind"]
        v = obj.get(lab)
        if v is None:
            issues.append(f"missing:{lab}")
            values[lab] = ""
            continue
        if kind in ("slider", "integer"):
            try:
                n = float(v)
            except (TypeError, ValueError):
                issues.append(f"nonnumeric:{lab}")
                values[lab] = ""
                continue
            lo, hi = item["min"], item["max"]
            if not (lo <= n <= hi):
                issues.append(f"clamped:{lab}")
                n = max(lo, min(hi, n))
            values[lab] = str(int(round(n)))
        else:  # binary
            s = str(v).strip().lower()
            if s in ("yes", "y", "true", "1"):
                values[lab] = "Yes"
            elif s in ("no", "n", "false", "0"):
                values[lab] = "No"
            else:
                issues.append(f"badbinary:{lab}")
                values[lab] = ""
    return values, issues


# --------------------------------------------------------------------------- #
# Run                                                                          #
# --------------------------------------------------------------------------- #
def load_personas(path: Path, pilot: bool, limit: int | None) -> list[dict]:
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    if pilot:                       # one respondent per condition
        seen, out = set(), []
        for r in rows:
            if r["condition"] not in seen:
                seen.add(r["condition"]); out.append(r)
        return out
    return rows[:limit] if limit else rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", choices=list(BACKENDS), default="ollama",
                    help="ollama (local) | openai (vLLM/cluster or hosted)")
    ap.add_argument("--model", default="llama3.1:8b")
    ap.add_argument("--temperature", type=float, default=0.9)
    ap.add_argument("--host", default=None, help="defaults per backend")
    ap.add_argument("--api-key", default=os.getenv("OPENAI_API_KEY"),
                    help="for the openai backend (vLLM accepts any value)")
    ap.add_argument("--personas", default=str(PERSONAS))
    ap.add_argument("--out", default=str(PIPE / "sim_out"))
    ap.add_argument("--pilot", action="store_true", help="one respondent per condition (17)")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--retries", type=int, default=2)
    args = ap.parse_args()

    chat = BACKENDS[args.backend]
    host = args.host or DEFAULT_HOST[args.backend]

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    conditions = json.loads(CONDITIONS.read_text(encoding="utf-8"))
    demo = _demo_labels(schema)
    raw_cols = schema["raw_export_columns"]
    question_block, spec = build_question_block(schema)
    stim = {lab: e["stimulus_text"] for lab, e in conditions["interventions"].items()}

    personas = load_personas(Path(args.personas), args.pilot, args.limit)

    out_dir = Path(args.out); out_dir.mkdir(parents=True, exist_ok=True)
    out_csv, log_path = out_dir / "raw_export.csv", out_dir / "logs.jsonl"

    done = set()
    if out_csv.exists():
        done = {r["profile_id"] for r in csv.DictReader(out_csv.open(encoding="utf-8"))}
    todo = [p for p in personas if p["profile_id"] not in done]
    print(f"{len(personas)} personas | {len(done)} already done | {len(todo)} to run "
          f"| model={args.model} temp={args.temperature}")
    if not todo:
        print("nothing to do."); return

    csv_f = out_csv.open("a", newline="", encoding="utf-8")
    writer = csv.DictWriter(csv_f, fieldnames=raw_cols)
    if not done:
        writer.writeheader()
    log_f = log_path.open("a", encoding="utf-8")

    n_issue = 0
    for p in tqdm(todo, desc="simulating", unit="resp"):
        cond = p["condition"]
        seed = int("".join(ch for ch in p["profile_id"] if ch.isdigit()) or "0")
        messages = [{"role": "system", "content": build_system(p, demo)},
                    {"role": "user", "content": build_user(cond, stim.get(cond), question_block)}]

        raw, values, issues = "", {}, ["no_attempt"]
        for attempt in range(args.retries + 1):
            try:
                raw = chat(messages, args.model, args.temperature, seed + attempt, host, args.api_key)
                values, issues = parse_response(raw, spec)
                if not any(i.startswith("json_error") for i in issues) and \
                   sum(i.startswith("missing") for i in issues) <= 5:
                    break
            except Exception as e:
                issues = [f"request_error:{e}"]; time.sleep(1.0)

        # assemble the raw-export row: persona's assigned fields + parsed answers
        row = {c: "" for c in raw_cols}
        for fld in PERSONA_FIELDS:
            row[fld] = p[fld]
        row.update({k: v for k, v in values.items() if k in row})
        writer.writerow(row); csv_f.flush()

        log_f.write(json.dumps({
            "profile_id": p["profile_id"], "condition": cond, "model": args.model,
            "seed": seed, "messages": messages, "raw_response": raw,
            "parse_issues": issues, "ts": time.time(),
        }) + "\n"); log_f.flush()
        if issues:
            n_issue += 1

    csv_f.close(); log_f.close()
    print(f"\ndone. wrote {out_csv}  (+ {log_path})")
    print(f"respondents with parse issues: {n_issue}/{len(todo)} "
          f"(see parse_issues in logs.jsonl)")


if __name__ == "__main__":
    sys.exit(main())
