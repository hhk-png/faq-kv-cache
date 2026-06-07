#!/usr/bin/env python
"""
Import oncology FAQ CSV into the faq_datasets directory.

CSV format (gb18030 encoded):
    department, title, ask, answer

Mapping:
    department -> category
    title + ask -> question
    answer -> answer

Output:
    data/faq_datasets/oncology/{english_name}.json per department
"""
import csv
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

BASE = Path(os.path.dirname(__file__)) / ".." / "data" / "faq_datasets"
CSV_FILE = BASE / "肿瘤科5-10000.csv"
OUT_DIR = BASE / "oncology"

# No hardcoded mapping needed; sequential numeric filenames used instead

FORMAT_MD = """# Oncology FAQ Data

Source: 肿瘤科5-10000.csv

## File Format
Each JSON file is an array of objects:

```json
[
  {
    "category": "肿瘤科",
    "question": "title + ask text",
    "answer": "answer text",
    "tags": []
  }
]
```

## Fields
- `category`: Department name in Chinese
- `question`: Combined title and ask from source CSV
- `answer`: Answer text
"""


def sanitize(name: str) -> str:
    """Sanitize string for use as filename."""
    return "".join(c if c.isalnum() or c in "_-" else "_" for c in name)


def main():
    if not CSV_FILE.exists():
        print(f"[ERR] {CSV_FILE} not found")
        sys.exit(1)

    print(f"[INFO] Reading CSV (this may take a moment)...")

    # Read CSV with gb18030 encoding
    data = CSV_FILE.read_bytes()
    text = data.decode("gb18030")

    reader = csv.DictReader(text.splitlines())
    rows = list(reader)
    print(f"[INFO] Read {len(rows)} rows")

    # Group by department
    grouped = defaultdict(list)
    for row in rows:
        dept = row.get("department", "").strip()
        title = row.get("title", "").strip()
        ask = row.get("ask", "").strip()
        answer = row.get("answer", "").strip()

        # Combine title and ask as question
        if title and ask:
            question = title + " " + ask
        elif title:
            question = title
        else:
            question = ask

        grouped[dept].append({
            "category": dept,
            "question": question,
            "answer": answer,
            "tags": [],
        })

    print(f"[INFO] Grouped into {len(grouped)} departments")

    # Create output directory
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Build dept -> seq mapping
    sorted_depts = sorted(grouped.keys())
    dept_seq = {d: f"{i+1:03d}" for i, d in enumerate(sorted_depts)}

    # Write per-department files with numeric English filenames
    dept_map = {}  # seq -> dept name for the mapping file
    for dept in sorted_depts:
        faqs = grouped[dept]
        seq = dept_seq[dept]
        fname = f"{seq}.json"
        target = OUT_DIR / fname
        with open(target, "w", encoding="utf-8") as f:
            json.dump(faqs, f, ensure_ascii=False, indent=2)
        dept_map[seq] = {"department": dept, "count": len(faqs)}
        print(f"  [OK] {fname} = {dept} ({len(faqs)} rows)")

    # Write mapping file
    mapping_file = OUT_DIR / "_mapping.json"
    with open(mapping_file, "w", encoding="utf-8") as f:
        json.dump(dept_map, f, ensure_ascii=False, indent=2)
    print(f"  [OK] _mapping.json")

    # Write format.md
    (OUT_DIR / "format.md").write_text(FORMAT_MD, encoding="utf-8")
    print(f"  [OK] format.md")

    print(f"\n[OK] Done! {len(rows)} FAQs in {len(grouped)} files -> {OUT_DIR}")


if __name__ == "__main__":
    main()
