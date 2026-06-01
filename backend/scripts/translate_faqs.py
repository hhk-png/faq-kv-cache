#!/usr/bin/env python
"""
Translate Japanese FAQ data to Chinese using Google Translate (free, no API key).

Usage:
    pip install deep-translator
    python scripts/translate_faqs.py

The script is resumable: if interrupted, re-run it and it will continue from where it left off.
"""
import sys
import os
import json
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
QUESTIONS_FILE = os.path.join(
    os.path.dirname(__file__), "..",
    "localgovfaq", "qas", "questions_in_Amagasaki.txt",
)
ANSWERS_FILE = os.path.join(
    os.path.dirname(__file__), "..",
    "localgovfaq", "qas", "answers_in_Amagasaki.txt",
)
OUTPUT_FILE = os.path.join(
    os.path.dirname(__file__), "..",
    "data", "faqs.json",
)

BATCH_SIZE = 30          # Translate N pairs per batch
SLEEP_BETWEEN = 2         # Seconds between batches (avoid rate limiting)
MAX_RETRIES = 3


def _load_tsv_column(filepath: str) -> dict[int, str]:
    """Load a TSV file where each line is: number\\ttext. Returns {id: text}."""
    items = {}
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t", 1)
            if len(parts) == 2:
                try:
                    idx = int(parts[0].strip())
                    text = parts[1].strip()
                    items[idx] = text
                except ValueError:
                    continue
    return items


def load_qa_pairs() -> list[dict]:
    """Load and merge questions & answers into QA pair dicts."""
    questions = _load_tsv_column(QUESTIONS_FILE)
    answers = _load_tsv_column(ANSWERS_FILE)

    # Find common IDs (intersection)
    common_ids = sorted(set(questions.keys()) & set(answers.keys()))
    pairs = []
    for idx in common_ids:
        q_text = questions[idx].replace("<改>", "\n")
        a_text = answers[idx].replace("<改>", "\n")
        pairs.append({"id": idx, "question": q_text, "answer": a_text})
    return pairs


# ---------------------------------------------------------------------------
# Existing translations (for resumability)
# ---------------------------------------------------------------------------
def _is_translated_entry(entry: dict) -> bool:
    """Check if an entry looks like a translated FAQ (faq_NNNN id pattern)."""
    return bool(entry.get("id", "").startswith("faq_"))


def load_existing_translations() -> dict[int, dict]:
    """Load already-translated entries. Returns {original_id: entry}."""
    if not os.path.exists(OUTPUT_FILE):
        return {}

    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except (json.JSONDecodeError, ValueError):
            return {}

    result = {}
    non_translated = []
    for entry in data:
        if _is_translated_entry(entry):
            orig_id = int(entry["id"].replace("faq_", ""))
            result[orig_id] = entry
        else:
            non_translated.append(entry)
    # Put back non-translated entries (they'll be rewritten on save)
    return result


def save_all_entries(translated: dict[int, dict], non_translated: list[dict]):
    """Write all entries to output file."""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    all_entries = list(non_translated)
    for orig_id in sorted(translated.keys()):
        entry = translated[orig_id]
        all_entries.append({
            "id": f"faq_{orig_id:04d}",
            "category": "",
            "question": entry["question"],
            "answer": entry["answer"],
            "tags": [],
            "created_at": entry.get("created_at", now),
            "updated_at": now,
        })

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_entries, f, ensure_ascii=False, indent=2)
    print(f"  💾 Saved {len(all_entries)} entries ({len(translated)} translated)")


# ---------------------------------------------------------------------------
# Translation
# ---------------------------------------------------------------------------
def _translate_text(text: str, translator) -> str:
    """Translate a single text string using deep-translator."""
    if not text.strip():
        return text
    # Split long text into chunks if needed (Google limit ~5000 chars)
    if len(text) > 4000:
        chunks = []
        for i in range(0, len(text), 3000):
            chunk = text[i:i + 3000]
            chunks.append(translator.translate(chunk))
        return " ".join(chunks)
    return translator.translate(text)


def translate_batch(batch: list[dict], translator) -> list[dict]:
    """Translate a batch of QA pairs."""
    results = []
    for item in batch:
        q_jp = item["question"]
        a_jp = item["answer"]

        try:
            q_cn = _translate_text(q_jp, translator)
            time.sleep(0.3)
            a_cn = _translate_text(a_jp, translator)

            results.append({
                "id": item["id"],
                "question": q_cn,
                "answer": a_cn,
            })
        except Exception as e:
            print(f"  ⚠️  Failed to translate FAQ {item['id']}: {e}")
            results.append({
                "id": item["id"],
                "question": q_jp,     # Fallback: keep Japanese
                "answer": a_jp,
            })

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("FAQ 翻译工具: 日文 → 中文 (Google Translate)")
    print("=" * 60)

    # Check if deep-translator is installed
    try:
        from deep_translator import GoogleTranslator
        translator = GoogleTranslator(source="ja", target="zh-CN")
        print("✅ Google Translator ready")
    except ImportError:
        print("❌ 请先安装: pip install deep-translator")
        sys.exit(1)

    # Load QA pairs
    print("\n📖 加载原始 FAQ 数据...")
    qa_pairs = load_qa_pairs()
    print(f"   共 {len(qa_pairs)} 条 FAQ")

    # Load existing translations
    print("\n📂 检查已有翻译...")
    existing = load_existing_translations()
    non_translated = []
    print(f"   已翻译: {len(existing)} 条")

    # Determine which IDs still need translation
    remaining = [p for p in qa_pairs if p["id"] not in existing]
    if not remaining:
        print("\n✅ 所有 FAQ 已翻译完毕！")
        return

    print(f"   待翻译: {len(remaining)} 条\n")

    # Process in batches
    total = len(remaining)
    for start in range(0, total, BATCH_SIZE):
        batch = remaining[start:start + BATCH_SIZE]
        batch_num = start // BATCH_SIZE + 1
        total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
        ids_range = f"{batch[0]['id']}~{batch[-1]['id']}"

        print(f"[{batch_num}/{total_batches}] 翻译第 {ids_range} 组 ({len(batch)} 条)...")

        for attempt in range(MAX_RETRIES):
            try:
                translated = translate_batch(batch, translator)
                for item in translated:
                    existing[item["id"]] = item
                save_all_entries(existing, non_translated)
                print(f"  ✅ 完成")
                time.sleep(SLEEP_BETWEEN)
                break
            except Exception as e:
                print(f"  ⚠️  第 {batch_num} 组失败 (尝试 {attempt+1}/{MAX_RETRIES}): {e}")
                time.sleep(SLEEP_BETWEEN * 2)
        else:
            print(f"  ❌ 第 {batch_num} 组翻译失败，跳过")

    # Final save
    save_all_entries(existing, non_translated)

    print(f"\n{'=' * 60}")
    print(f"✅ 完成! 共翻译 {len(existing)} 条 FAQ\n")


if __name__ == "__main__":
    main()
