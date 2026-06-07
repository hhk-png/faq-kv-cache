#!/usr/bin/env python
"""Split monolithic faqs.json into per-category JSON files with English names."""
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

BASE = Path(os.path.dirname(__file__)) / ".." / "data"
OLD_FILE = BASE / "faqs.json"
NEW_DIR = BASE / "faqs"

# Category -> English filename
CATEGORY_FILE = {
    "医疗健康": "medical_health",
    "儿童保育": "child_care",
    "其他": "other",
    "交通/道路": "transportation",
    "文化体育": "culture_sports",
    "城市规划/住宅": "urban_planning",
    "社会保障（年金、保险）": "social_security",
    "户籍/住民登记": "residence_registration",
    "税务": "tax",
    "垃圾回收/环境": "waste_environment",
    "支付": "payment",
    "物流": "logistics",
    "教育": "education",
    "消防/急救": "fire_emergency",
    "农业": "agriculture",
    "选举": "election",
    "A": "A",
    "B": "B",
    "C": "C",
    "D": "D",
    "X": "X",
    "Y": "Y",
    "测试": "test",
}

FORMAT_MD = """# FAQ Data

Each file is a JSON array of FAQ objects for one category.

## Format
```json
[
  {
    "category": "医疗健康",
    "question": "...",
    "answer": "...",
    "tags": []
  }
]
```

## Files
"""


def main():
    if not OLD_FILE.exists():
        print(f"[ERR] {OLD_FILE} not found")
        sys.exit(1)

    with open(OLD_FILE, "r", encoding="utf-8") as f:
        all_faqs = json.load(f)

    print(f"[INFO] Read {len(all_faqs)} FAQs")

    grouped = defaultdict(list)
    for faq in all_faqs:
        grouped[faq.get("category", "其他")].append(faq)

    NEW_DIR.mkdir(parents=True, exist_ok=True)

    file_list = []
    for cat, faqs in sorted(grouped.items()):
        fname = CATEGORY_FILE.get(cat, cat) + ".json"
        target = NEW_DIR / fname
        with open(target, "w", encoding="utf-8") as f:
            json.dump(faqs, f, ensure_ascii=False, indent=2)
        file_list.append(f"  - `{fname}`: {cat} ({len(faqs)})")
        print(f"  [OK] {fname} ({len(faqs)})")

    # Write format.md
    fmt = FORMAT_MD + "\n".join(file_list) + "\n"
    (NEW_DIR / "format.md").write_text(fmt, encoding="utf-8")
    print(f"  [OK] format.md")

    # Backup old file
    backup = OLD_FILE.with_suffix(".json.bak")
    if not backup.exists():
        OLD_FILE.rename(backup)
        print(f"  [BAK] backed up as {backup.name}")

    print(f"\n[OK] Done! {len(all_faqs)} FAQs in {len(grouped)} files.")


if __name__ == "__main__":
    main()
