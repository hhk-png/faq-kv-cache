# FAQ Datasets

Each subdirectory is a dataset containing per-category JSON files.

## Data Format

Each file is a JSON array:
```json
[
  {
    "id": "auto-generated-12-char-hex",
    "category": "CategoryName",
    "question": "The question text",
    "answer": "The answer text",
    "tags": ["tag1", "tag2"]
  }
]
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | No | Unique ID; auto-generated if omitted |
| `category` | string | Yes | Category/department name |
| `question` | string | Yes | The question text |
| `answer` | string | Yes | The answer text |
| `tags` | string[] | No | Optional tags |

## Datasets

- `amagasaki/` - Translated municipal government FAQ
- `oncology/` - Medical FAQ from CSV import

## Config

Switch dataset in `config.py`:
```python
faq_dataset_path: str = "data/faq_datasets/oncology"
```
