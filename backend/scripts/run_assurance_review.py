from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from app.services.assurance import run_assurance_review


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the NEXUS technology-assurance control review.")
    parser.add_argument(
        "--output",
        default="assurance-report.json",
        help="Path for the generated JSON evidence report.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    with tempfile.TemporaryDirectory(prefix="nexus-assurance-") as tmp:
        report = run_assurance_review(Path(tmp), repo_root=repo_root)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["overall_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
