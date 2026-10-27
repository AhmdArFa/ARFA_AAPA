"""Demo CLI for the head-manager assistant."""

import argparse
import json
import sys
from pathlib import Path

from .agent import ask

REPO_ROOT = Path(__file__).resolve().parents[2]


def _print_answer(answer) -> None:
    status = "مؤكد من الداتا" if answer.confirmed else "امتناع"
    print(f"[{status}] {answer.text}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ARFA AAPA demo assistant")
    parser.add_argument("question", nargs="?", help="سؤال واحد بالعربي")
    parser.add_argument("--demo", action="store_true", help="تشغيل الأسئلة الذهبية")
    args = parser.parse_args(argv)

    if args.demo:
        golden_path = REPO_ROOT / "evals" / "golden_questions.json"
        questions = json.loads(golden_path.read_text(encoding="utf-8"))
        for item in questions:
            print(f"\nسؤال: {item['question']}")
            answer = ask(item["question"])
            _print_answer(answer)
            if answer.metric_key != item["expected_metric"]:
                print(f"  تنبيه: المقياس المتوقع {item['expected_metric']}، والمقياس الفعلي {answer.metric_key}.")
        return 0

    if args.question:
        _print_answer(ask(args.question))
        return 0

    print("اكتب سؤالك، أو اكتب خروج للإنهاء.")
    while True:
        try:
            question = input("المدير: ").strip()
        except EOFError:
            return 0
        if question in ("خروج", "exit", "quit"):
            return 0
        if question:
            _print_answer(ask(question))
    return 0


if __name__ == "__main__":
    sys.exit(main())
