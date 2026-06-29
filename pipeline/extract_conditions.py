"""
Block 2 (conditions) -- Extract the intervention stimulus texts.
=================================================================

PURPOSE
    Produce pipeline/conditions.json: for each of the 16 interventions, the exact
    stimulus passage a respondent reads before answering. Block 4 injects
    `interventions[<label>]["stimulus_text"]` into the prompt; `control` gets none.

SOURCE OF TRUTH
    survey/questionnaire.txt -- the chronological, human-readable rendering of the
    instrument. Its CONDITION section lists each intervention as a `### <Title>`
    block, and the titles match scripts/lib/submission_spec.R verbatim (the same
    16 labels pinned in pipeline/schema.json). We parse those blocks.

    `survey/survey.json` is the deeper structured source (Blocks / SurveyFlow); if
    you later want to refine wording or model the exact branching, go there. For a
    working first pass, questionnaire.txt is the faithful, intended reference.

SPECIAL CASES (flagged in the output `note` field)
    * control ............... shows one of three neutral OFF-TOPIC filler texts
                              (neckties / baseball / dances), not reproduced in
                              the questionnaire -> stimulus_text = None.
    * Extreme weather predictions .. state-branched (4 cases by home state). We use
                              "Case 4", the state-agnostic fallback, as the single
                              representative stimulus. Refine later if desired.
    * Funding / Consensus / High public trust .. interactive (interspersed
                              estimate/agree items + feedback). We keep the full
                              informational passage and flag has_interactive_elements.

RUN
    python pipeline/extract_conditions.py
OUTPUT
    pipeline/conditions.json   (+ a printed summary)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUESTIONNAIRE = ROOT / "survey" / "questionnaire.txt"
OUT = Path(__file__).resolve().parent / "conditions.json"

# Lines that are pure layout / not part of the read passage.
_PAGEBREAK = re.compile(r"^[\s\-—–]*page\s*break[\s\-—–.]*$", re.IGNORECASE)
_BOUNDARY = re.compile(r"^\s*(-{6,}|={6,}|TRANSITION)\s*$")
# Heuristic flags for interactive conditions (informational only).
_INTERACTIVE = re.compile(r"slider|Strongly disagree|best estimate|percentage of scientists",
                          re.IGNORECASE)


def _condition_section(lines: list[str]) -> tuple[list[str], int]:
    """Return the lines of the CONDITION section and the file offset of its start."""
    start = next(i for i, l in enumerate(lines)
                 if l.strip().startswith("CONDITION") and "exactly ONE" in l)
    end = next(i for i, l in enumerate(lines) if "POST-TREATMENT OUTCOMES" in l)
    return lines[start:end], start


def _clean(body: list[str]) -> str:
    """Drop page-break markers + any trailing TRANSITION/divider, tidy blank lines."""
    out: list[str] = []
    for raw in body:
        if _BOUNDARY.match(raw):           # stop at a section divider / TRANSITION
            break
        if _PAGEBREAK.match(raw):          # skip "— page break —" style lines
            continue
        out.append(raw.rstrip())
    # collapse 3+ blank lines to one; trim leading/trailing blanks
    text = "\n".join(out)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def _extract_case4(body_text: str) -> str:
    """For 'Extreme weather predictions': pull the state-agnostic Case 4 passage.

    The body holds 4 case stimuli ("Case 1".."Case 4") followed by a references
    block whose lines read "Case N is based on ...". We match the exact "Case 4"
    HEADING line (not the reference line) and take everything up to "References".
    """
    lines = body_text.split("\n")
    starts = [i for i, l in enumerate(lines) if l.strip() == "Case 4"]
    if not starts:
        return body_text
    s = starts[-1]
    end = next((i for i in range(s + 1, len(lines)) if "References" in lines[i]), len(lines))
    return "\n".join(lines[s + 1:end]).strip()


def extract() -> dict:
    lines = QUESTIONNAIRE.read_text(encoding="utf-8").splitlines()
    section, base = _condition_section(lines)

    # locate every "### <Title>" header within the section
    headers = [(i, m.group(1).strip())
               for i, l in enumerate(section)
               if (m := re.match(r"^###\s+(.+?)\s*$", l))]

    interventions: dict[str, dict] = {}
    for k, (i, title) in enumerate(headers):
        j = headers[k + 1][0] if k + 1 < len(headers) else len(section)
        body_text = _clean(section[i + 1:j])
        note = ""

        if title == "Extreme weather predictions":
            full = body_text
            body_text = _extract_case4(full)
            note = ("state-branched (4 cases by home state); using Case 4, the "
                    "state-agnostic fallback, as the representative stimulus.")

        entry = {
            "label": title,
            "stimulus_text": body_text,
            "char_len": len(body_text),
            "has_interactive_elements": bool(_INTERACTIVE.search(body_text)),
            "source_lines": [base + i + 1, base + j],   # 0-based file offsets of block
        }
        if note:
            entry["note"] = note
        if entry["has_interactive_elements"] and "note" not in entry:
            entry["note"] = ("contains interspersed estimate/agree items + feedback; "
                             "full informational passage kept for the first pass.")
        interventions[title] = entry

    schema = {
        "meta": {
            "generated_by": "pipeline/extract_conditions.py",
            "source": "survey/questionnaire.txt (CONDITION section)",
            "n_interventions": len(interventions),
            "control": "control",
            "how_to_use": ("Block 4 injects interventions[<condition>]['stimulus_text'] "
                           "into each respondent's prompt; the control condition "
                           "presents no climate-related stimulus."),
        },
        "control": {
            "label": "control",
            "is_control": True,
            "stimulus_text": None,
            "note": ("shows one of three neutral, off-topic filler texts (History of "
                     "Neckties / Rules of Baseball / Types of Dances), not reproduced "
                     "in the questionnaire; present no intervention."),
        },
        "interventions": interventions,
    }
    return schema


def main() -> dict:
    schema = extract()
    OUT.write_text(json.dumps(schema, indent=2, ensure_ascii=False), encoding="utf-8")
    iv = schema["interventions"]
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"  interventions extracted: {len(iv)}")
    for label, e in iv.items():
        flag = " [interactive]" if e["has_interactive_elements"] else ""
        print(f"    - {label:32} {e['char_len']:5d} chars{flag}")
    return schema


if __name__ == "__main__":
    main()
