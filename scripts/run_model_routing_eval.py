#!/usr/bin/env python3
"""Run every routing YAML case through a model and enforce release thresholds.

Requires ``OPENAI_API_KEY``. The evaluator asks the model whether one candidate
skill should trigger, not which skill wins globally, so YAML expectations map
directly to trigger/no_trigger/ambiguous labels.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "evals"
SKILLS = ROOT / "packages" / "sent" / "skills"
LABELS = ("trigger", "no_trigger", "ambiguous")


def load_cases() -> list[dict[str, str]]:
    cases: list[dict[str, str]] = []
    for path in sorted(EVALS.glob("*.yaml")):
        suite = yaml.safe_load(path.read_text(encoding="utf-8"))
        skill = suite["skill"]
        description = yaml.safe_load(
            (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8").split("---", 2)[1]
        )["description"]
        for index, case in enumerate(suite["cases"], 1):
            cases.append(
                {
                    "id": f"{skill}:{index}",
                    "skill": skill,
                    "description": description,
                    "query": case["query"],
                    "expect": case["expect"],
                }
            )
    return cases


def response_text(response: dict[str, Any]) -> str:
    for item in response.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                return content["text"]
    raise RuntimeError("model response did not contain output_text")


def predict(cases: list[dict[str, str]]) -> dict[str, str]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for model-backed routing evaluation")
    model = os.environ.get("SENT_ROUTING_EVAL_MODEL", "gpt-5-mini")
    inputs = [
        {
            "id": case["id"],
            "candidate_skill": case["skill"],
            "candidate_description": case["description"],
            "user_query": case["query"],
        }
        for case in cases
    ]
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["predictions"],
        "properties": {
            "predictions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["id", "label"],
                    "properties": {
                        "id": {"type": "string"},
                        "label": {"type": "string", "enum": list(LABELS)},
                    },
                },
            }
        },
    }
    body = {
        "model": model,
        "instructions": (
            "For each independent case, decide whether the candidate skill should trigger for the user query. "
            "Use trigger when it clearly owns the request, no_trigger when it does not, and ambiguous when it "
            "substantially overlaps another skill or needs routing clarification. Return every id exactly once."
        ),
        "input": json.dumps(inputs, ensure_ascii=False),
        "text": {
            "format": {
                "type": "json_schema",
                "name": "sent_routing_predictions",
                "strict": True,
                "schema": schema,
            }
        },
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        parsed = json.load(response)
    result = json.loads(response_text(parsed))["predictions"]
    return {item["id"]: item["label"] for item in result}


def evaluate(cases: list[dict[str, str]], predictions: dict[str, str]) -> int:
    expected_ids = {case["id"] for case in cases}
    if set(predictions) != expected_ids:
        missing = sorted(expected_ids - set(predictions))
        extra = sorted(set(predictions) - expected_ids)
        print(f"Prediction coverage mismatch: missing={missing}, extra={extra}", file=sys.stderr)
        return 1
    confusion: Counter[tuple[str, str]] = Counter()
    failures: list[dict[str, str]] = []
    for case in cases:
        predicted = predictions[case["id"]]
        expected = case["expect"]
        confusion[(expected, predicted)] += 1
        if predicted != expected:
            failures.append({**case, "predicted": predicted})
    total = len(cases)
    correct = total - len(failures)
    accuracy = correct / total if total else 0.0
    hard_negatives = [case for case in cases if case["expect"] == "no_trigger"]
    hard_negative_success = sum(predictions[case["id"]] == "no_trigger" for case in hard_negatives) / len(hard_negatives)

    print("Confusion matrix (expected rows, predicted columns):")
    print("expected\\predicted\t" + "\t".join(LABELS))
    for expected in LABELS:
        print(expected + "\t" + "\t".join(str(confusion[(expected, predicted)]) for predicted in LABELS))
    print(f"Overall routing accuracy: {correct}/{total} ({accuracy:.1%})")
    print(f"Hard-negative success: {hard_negative_success:.1%}")
    if failures:
        print("Newly ambiguous or misrouted prompts:")
        for failure in failures:
            print(
                f"- {failure['id']}: expected={failure['expect']} predicted={failure['predicted']} "
                f"query={failure['query']!r}"
            )
    if hard_negative_success < 1.0 or accuracy < 0.95:
        return 1
    return 0


def main() -> int:
    cases = load_cases()
    predictions = predict(cases)
    return evaluate(cases, predictions)


if __name__ == "__main__":
    raise SystemExit(main())
