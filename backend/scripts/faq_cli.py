#!/usr/bin/env python
"""
FAQ CLI Tools for batch operations.

Usage:
    python scripts/faq_cli.py add --category "支付" --question "如何退款？" --answer "在订单页面点击申请退款..." --tags "退款,售后"
    python scripts/faq_cli.py import --file scripts/sample_data/faqs.json
    python scripts/faq_cli.py import --file scripts/sample_data/faqs.csv --format csv
    python scripts/faq_cli.py list
"""
import argparse
import json
import csv
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.storage.file_store import faq_store
from app.services.faq_service import create_faq, batch_create_faqs, list_faqs


def cmd_add(args):
    tags = [t.strip() for t in args.tags.split(",")] if args.tags else []
    faq = create_faq({
        "category": args.category,
        "question": args.question,
        "answer": args.answer,
        "tags": tags,
    })
    print(f"FAQ created: {faq['id']}")
    print(f"  Category: {faq['category']}")
    print(f"  Question: {faq['question']}")


def cmd_import(args):
    file_path = args.file
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    items = []
    if args.format == "json":
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict) and "items" in data:
                items = data["items"]
            else:
                print("Error: JSON must be an array or contain an 'items' key", file=sys.stderr)
                sys.exit(1)
    elif args.format == "csv":
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                tags = [t.strip() for t in row.get("tags", "").split(",") if t.strip()]
                items.append({
                    "category": row.get("category", ""),
                    "question": row.get("question", ""),
                    "answer": row.get("answer", ""),
                    "tags": tags,
                })
    else:
        print(f"Error: Unsupported format: {args.format}", file=sys.stderr)
        sys.exit(1)

    if not items:
        print("Error: No items found in file", file=sys.stderr)
        sys.exit(1)

    created = batch_create_faqs(items)
    print(f"Imported {len(created)} FAQs successfully.")


def cmd_list(args):
    items = list_faqs()
    if not items:
        print("No FAQs found.")
        return
    print(f"Total: {len(items)} FAQs\n")
    for faq in items:
        print(f"[{faq['id']}] ({faq.get('category', '')}) {faq['question']}")
        print(f"    Answer: {faq['answer'][:80]}..." if len(faq['answer']) > 80 else f"    Answer: {faq['answer']}")
        print()


def main():
    parser = argparse.ArgumentParser(description="FAQ Management CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # add
    add_parser = subparsers.add_parser("add", help="Add a single FAQ")
    add_parser.add_argument("--category", required=True)
    add_parser.add_argument("--question", required=True)
    add_parser.add_argument("--answer", required=True)
    add_parser.add_argument("--tags", default="")

    # import
    import_parser = subparsers.add_parser("import", help="Batch import FAQs from file")
    import_parser.add_argument("--file", required=True)
    import_parser.add_argument("--format", choices=["json", "csv"], default="json")

    # list
    list_parser = subparsers.add_parser("list", help="List all FAQs")

    args = parser.parse_args()
    if args.command == "add":
        cmd_add(args)
    elif args.command == "import":
        cmd_import(args)
    elif args.command == "list":
        cmd_list(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
