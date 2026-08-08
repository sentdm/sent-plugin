#!/usr/bin/env python3
"""Assert the preserved Sent utility fixture exit-code contract."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "packages" / "sent" / "skills"
CASES = (
    (
        "MDR good",
        SKILLS / "messaging-performance-analyzer" / "scripts" / "analyze_mdr_funnel.py",
        SKILLS / "messaging-performance-analyzer" / "scripts" / "fixtures" / "good.json",
        0,
    ),
    (
        "MDR bad",
        SKILLS / "messaging-performance-analyzer" / "scripts" / "analyze_mdr_funnel.py",
        SKILLS / "messaging-performance-analyzer" / "scripts" / "fixtures" / "bad.json",
        3,
    ),
    (
        "10DLC good",
        SKILLS / "sms-10dlc-registration" / "scripts" / "validate_10dlc_packet.py",
        SKILLS / "sms-10dlc-registration" / "scripts" / "fixtures" / "good.json",
        0,
    ),
    (
        "10DLC bad",
        SKILLS / "sms-10dlc-registration" / "scripts" / "validate_10dlc_packet.py",
        SKILLS / "sms-10dlc-registration" / "scripts" / "fixtures" / "bad.json",
        1,
    ),
    (
        "WABA template good",
        SKILLS / "waba-template-author" / "scripts" / "lint_waba_template.py",
        SKILLS / "waba-template-author" / "scripts" / "fixtures" / "utility_good.json",
        0,
    ),
    (
        "WABA template bad",
        SKILLS / "waba-template-author" / "scripts" / "lint_waba_template.py",
        SKILLS / "waba-template-author" / "scripts" / "fixtures" / "utility_bad.json",
        1,
    ),
)


def main() -> None:
    failures: list[str] = []
    for label, script, fixture, expected in CASES:
        result = subprocess.run(
            [sys.executable, str(script), str(fixture)],
            cwd=script.parent,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != expected:
            failures.append(
                f"{label}: expected {expected}, got {result.returncode}\n"
                f"stdout: {result.stdout.strip()}\nstderr: {result.stderr.strip()}"
            )
        else:
            print(f"PASS {label}: exit {expected}")
    if failures:
        raise SystemExit("\n\n".join(failures))
    print("Fixture contract preserved: MDR 0/3, 10DLC 0/1, WABA template 0/1.")


if __name__ == "__main__":
    main()
