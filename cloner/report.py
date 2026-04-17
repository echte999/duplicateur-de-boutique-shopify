import csv
import json
from pathlib import Path

_REPORT_JSON = Path("output/clone_report.json")
_REPORT_CSV = Path("output/clone_report.csv")


def save_report(entries: list[dict]) -> None:
    _REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    _REPORT_JSON.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")

    if not entries:
        return

    fieldnames = list(entries[0].keys())
    with _REPORT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(entries)

    print(f"Report saved: {len(entries)} entries → {_REPORT_JSON}, {_REPORT_CSV}")
