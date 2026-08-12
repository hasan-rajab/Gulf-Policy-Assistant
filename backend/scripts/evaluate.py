import json
import sys
from pathlib import Path

from app.dependencies import get_evaluation_service


def main(path: str):
    cases = json.loads(Path(path).read_text(encoding="utf-8"))
    result = get_evaluation_service().run(cases, "evaluation@gulfhorizon.local")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "../evaluation/eval_set.json")
