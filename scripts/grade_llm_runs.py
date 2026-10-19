"""Grade recorded AI-improvement runs against the gold cases in data/eval/kr (LLM judge).

uv run python scripts/grade_llm_runs.py qwen3-14b-local claude-sonnet-5-5 ...
Writes data/outputs/llm_runs/<label>/grades.json and prints a score table.

The judge sees the rubric and the real prosecution outcome, never the model name. Scores are a
relative yardstick for comparing runs, not a legal quality certificate.
"""

import argparse
import json
import sys
from pathlib import Path

import anthropic
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.config import Settings  # noqa: E402

EVAL = ROOT / "data/eval/kr"
RUNS = ROOT / "data/outputs/llm_runs"
JUDGE_MODEL = "claude-sonnet-5-5"


class Verdict(BaseModel):
    id: str
    passed: bool
    reason: str


class Grade(BaseModel):
    verdicts: list[Verdict]


def suggestion_text(record):
    if not record.get("ok"):
        return "(no suggestion: run failed: " + record.get("error", "") + ")"
    s = record["response"]["suggestion"]
    lines = ["issue_summary: " + s["issue_summary"]]
    for i, st in enumerate(s["strategies"], 1):
        lines.append(
            f"strategy {i} [{st['action_type']}] {st['title']}: {st['description']} "
            f"| expected: {st['expected_effect']} | tradeoff: {st['tradeoff']}"
        )
    if not s["strategies"]:
        lines.append("(no strategies: the model abstained)")
    for c in s["element_comparison"][:8]:
        lines.append(f"comparison: {c['claim_element'][:120]} -> {c['examiner_position'][:200]}")
    return "\n".join(lines)


def grade(client, gold, record):
    prompt = (
        "You grade an AI's suggested response strategy to a Korean patent office action.\n"
        "The AI only saw the first office action. Below is what really happened later, and a "
        "rubric. Answer each rubric item strictly from the AI suggestion text: passed=true only "
        "if the suggestion clearly does what the question asks. A vague mention is not enough.\n\n"
        "REAL PROSECUTION:\n"
        + json.dumps(gold["prosecution"], ensure_ascii=False)
        + "\n\nRUBRIC:\n"
        + json.dumps(gold["rubric"], ensure_ascii=False)
        + "\n\nAI SUGGESTION:\n"
        + suggestion_text(record)
        + "\n\nReturn one verdict per rubric id, reason in Korean (one sentence)."
    )
    response = client.messages.parse(
        model=JUDGE_MODEL,
        max_tokens=4000,
        output_config={"effort": "medium"},
        messages=[{"role": "user", "content": prompt}],
        output_format=Grade,
    )
    verdicts = {v.id: v for v in response.parsed_output.verdicts}
    total = sum(r["weight"] for r in gold["rubric"])
    score = sum(
        r["weight"] for r in gold["rubric"] if verdicts.get(r["id"]) and verdicts[r["id"]].passed
    )
    return {
        "score": score,
        "max": total,
        "verdicts": {k: v.model_dump() for k, v in verdicts.items()},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("labels", nargs="+")
    parser.add_argument("--repeats", type=int, default=3, help="judge runs per answer (averaged)")
    args = parser.parse_args()
    settings = Settings()
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key or None)
    golds = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in EVAL.glob("*.json")}
    table = []
    for label in args.labels:
        grades = {}
        for app, gold in golds.items():
            path = RUNS / label / f"{app}.json"
            if not path.exists():
                continue
            record = json.loads(path.read_text(encoding="utf-8"))
            runs = [grade(client, gold, record) for _ in range(args.repeats)]
            grades[app] = {
                "score": round(sum(r["score"] for r in runs) / len(runs), 2),
                "scores": [r["score"] for r in runs],
                "max": runs[0]["max"],
                "runs": runs,
            }
        (RUNS / label / "grades.json").write_text(
            json.dumps(grades, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        row = [label] + [
            f"{grades[a]['score']}/{grades[a]['max']} {grades[a]['scores']}" if a in grades else "-"
            for a in sorted(golds)
        ]
        table.append(row)
    print("label | " + " | ".join(sorted(golds)))
    for row in table:
        print(" | ".join(row))


if __name__ == "__main__":
    main()
