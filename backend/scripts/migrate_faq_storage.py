#!/usr/bin/env python
"""
Migrate FAQ data from monolithic data/faqs.json to category-based directory structure.

Before:
    data/faqs.json          # All FAQs in one file

After:
    data/faq/
        _index.json         # Category index
        format.md           # Overall format doc
        社会保障/
            data.json       # FAQs for this category
            format.md       # Category format doc
        医疗健康/
            data.json
            format.md
        ...
"""
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

BASE_DIR = Path(os.path.dirname(__file__)) / ".." / "data"
OLD_FILE = BASE_DIR / "faqs.json"
NEW_DIR = BASE_DIR / "faq"

FORMAT_MD_ROOT = """# FAQ 数据格式说明

## 目录结构
```
data/faq/
├── _index.json          # 类别索引（自动维护）
├── format.md            # 本文件
├── {category_name}/     # 每个类别一个目录
│   ├── data.json        # 该类别的 FAQ 数据
│   └── format.md        # 该类别的格式说明
```

## 如何新增 FAQ

1. 找到对应的类别目录 `data/faq/{category}/`
2. 编辑 `data.json`
3. 按以下格式添加条目：

```json
{
  "category": "类别名称",
  "question": "问题",
  "answer": "答案",
  "tags": ["标签1", "标签2"]
}
```

4. `id` 字段可选，不填则系统自动生成
5. 保存后重启后端即可生效

## 如何新增类别

1. 创建目录 `data/faq/{新类别}/`
2. 创建 `data.json` 文件，内容为 `[]`
3. 系统启动时会自动扫描到该类别
"""

FORMAT_MD_CATEGORY = """# {category} FAQ 数据格式

## 文件位置
`data/faq/{category}/data.json`

## 数据格式
JSON 数组，每个元素包含：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 否 | 唯一标识，不填自动生成 |
| category | string | 是 | 固定为 "{category}" |
| question | string | 是 | 问题内容 |
| answer | string | 是 | 答案内容 |
| tags | string[] | 否 | 标签列表 |

## 示例
```json
[
  {{
    "category": "{category}",
    "question": "示例问题",
    "answer": "示例答案",
    "tags": ["标签"]
  }}
]
```
"""


def migrate():
    if not OLD_FILE.exists():
        print(f"[ERR] 未找到 {OLD_FILE}，跳过迁移")
        return

    # Read old data
    with open(OLD_FILE, "r", encoding="utf-8") as f:
        all_faqs = json.load(f)

    print(f"[INFO] 读取 {len(all_faqs)} 条 FAQ")

    # Group by category
    grouped = defaultdict(list)
    for faq in all_faqs:
        cat = faq.get("category", "未分类")
        grouped[cat].append(faq)

    print(f"[INFO] 按 {len(grouped)} 个类别分组")

    # Create new directory structure
    NEW_DIR.mkdir(parents=True, exist_ok=True)

    # Build index
    categories = []
    for cat_name in sorted(grouped.keys()):
        faqs = grouped[cat_name]
        # Sanitize directory name: replace / and other path-unfriendly chars
        safe_name = cat_name.replace("/", "_").replace("\\", "_").replace(":", "_")
        cat_dir = NEW_DIR / safe_name
        cat_dir.mkdir(exist_ok=True)

        # Write data.json
        data_file = cat_dir / "data.json"
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(faqs, f, ensure_ascii=False, indent=2)
        print(f"  [OK] {cat_name}: {len(faqs)} 条 -> {data_file}")

        # Write format.md
        fmt_file = cat_dir / "format.md"
        fmt_file.write_text(
            FORMAT_MD_CATEGORY.format(category=cat_name),
            encoding="utf-8",
        )

        categories.append({"name": cat_name, "dir": safe_name, "faq_count": len(faqs)})

    # Write _index.json
    index_file = NEW_DIR / "_index.json"
    with open(index_file, "w", encoding="utf-8") as f:
        json.dump({"categories": categories}, f, ensure_ascii=False, indent=2)
    print(f"  [OK] 索引 -> {index_file}")

    # Write root format.md
    fmt_root = NEW_DIR / "format.md"
    fmt_root.write_text(FORMAT_MD_ROOT, encoding="utf-8")
    print(f"  [OK] 格式文档 -> {fmt_root}")

    # Backup old file
    backup = OLD_FILE.with_suffix(".json.bak")
    OLD_FILE.rename(backup)
    print(f"  📦 旧文件已备份为 {backup}")

    print(f"\n[OK] 迁移完成！{len(all_faqs)} 条 FAQ 已按 {len(grouped)} 个类别存储。")
    print(f"   如需恢复，将 {backup} 重命名为 faqs.json 即可。")


if __name__ == "__main__":
    migrate()
