# FAQ KV Cache Agent

An intelligent FAQ question-answering system leveraging LLM **prefix caching** for fast, cost-effective retrieval. Built with FastAPI + LangGraph + React + TailwindCSS.

## Architecture

```
User Question
    │
    ▼
┌─────────────────────────────┐
│  Algorithmic FAQ Retrieval  │  ← Keyword scoring, no LLM call
│  (fast, user invisible)     │
└─────────────┬───────────────┘
              │ matched FAQs
              ▼
┌─────────────────────────────┐
│  LLM Answer Generation      │  ← Streamed via SSE
│  + KV Cache Hit             │  ← FAQ prefix cached from warmup
└─────────────────────────────┘
```

### Key Concepts

- **KV Cache Warmup**: FAQs are split into blocks (by category, 10 per block) and sent to the LLM API with `max_tokens=1` to pre-establish prefix caches.
- **Algorithmic Retrieval**: At query time, a fast keyword-scoring algorithm selects relevant FAQs — no LLM calls, user invisible.
- **Streaming**: Answers are streamed token-by-token via Server-Sent Events (SSE).

## Features

- **FAQ Management** — CRUD, batch import (JSON/CSV), category & keyword filtering
- **Document Management** — Upload PDF/DOCX/TXT/MD, auto text extraction
- **Q&A Chat** — Streaming answers, FAQ references, prior knowledge injection
- **Cache Management** — Auto cache warmup on FAQ changes, status monitoring
- **Admin CLI** — Script-based FAQ import and management

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + TypeScript + TailwindCSS + Vite + pnpm |
| Backend | Python + FastAPI + LangGraph |
| LLM | OpenAI SDK (DeepSeek compatible) |
| Task Queue | Celery + Redis |
| Storage | Local JSON files (file-lock safe) |
| Deployment | Docker + Docker Compose |

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- pnpm
- Redis
- LLM API key (OpenAI / DeepSeek / compatible)

### Backend Setup

```bash
# Install dependencies
cd backend
python run.py install

# Configure environment
echo "LLM_API_KEY=sk-your-key" > .env
echo "LLM_BASE_URL=https://api.deepseek.com/v1" >> .env
echo "LLM_MODEL=deepseek-chat" >> .env

# Start Redis (required for Celery)
redis-server

# Start FastAPI (terminal 1)
python run.py api

# Start Celery Worker (terminal 2, for cache warmup)
python run.py worker
```

### Frontend Setup

```bash
cd frontend
pnpm install
pnpm dev
```

Open http://localhost:5173

### Docker Deployment

```bash
docker-compose up -d
```

## API Endpoints

### FAQ Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/faqs` | Create FAQ |
| POST | `/api/faqs/batch` | Batch create |
| GET | `/api/faqs` | List (filter: `?category=&keyword=`) |
| GET | `/api/faqs/{id}` | Get by ID |
| PUT | `/api/faqs/{id}` | Update |
| DELETE | `/api/faqs/{id}` | Delete |
| POST | `/api/faqs/rebuild-cache` | Trigger cache warmup |

### Q&A
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/qa/ask` | Ask (non-streaming) |
| POST | `/api/qa/ask/stream` | Ask (SSE streaming) |

### Document Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/documents/upload` | Upload file |
| GET | `/api/documents` | List documents |
| GET | `/api/documents/{id}/content` | Get extracted text |
| DELETE | `/api/documents/{id}` | Delete |

### Cache
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/cache/status` | Cache warmup status |

## Project Structure

```
faq-agent/
├── frontend/               # React + Vite + TailwindCSS
│   ├── src/
│   │   ├── pages/          # FaqManage, DocumentManage, QaChat
│   │   ├── components/     # Layout, ChatMessage, PriorKnowledgeSelector
│   │   ├── services/       # API client (faq, document, qa, cache)
│   │   └── types/          # TypeScript interfaces
│   ├── package.json
│   └── vite.config.ts
│
├── backend/                # FastAPI + Celery
│   ├── app/
│   │   ├── api/            # Route handlers
│   │   ├── services/       # Business logic (qa, faq, cache, document)
│   │   ├── core/           # Config, LLM client
│   │   ├── agent/          # LangGraph agent definition
│   │   ├── storage/        # JSON file store
│   │   └── tasks/          # Celery async tasks
│   ├── scripts/            # CLI tools, sample data
│   ├── tests/              # pytest test suite
│   ├── run.py              # One-click launcher
│   └── requirements.txt
│
├── docker-compose.yml
├── nginx.conf
└── Makefile
```

## Testing

```bash
cd backend
python run.py test            # Run all tests
python run.py test --watch    # Watch mode (auto-rerun on changes)
python run.py test -c         # With coverage report
```

## CLI Tool

```bash
cd backend
python scripts/faq_cli.py add --category "Payment" --question "How to refund?" --answer "Click refund in order page."
python scripts/faq_cli.py import --file scripts/sample_data/faqs.json
python scripts/faq_cli.py import --file scripts/sample_data/faqs.csv --format csv
python scripts/faq_cli.py list
```

## Cache Warmup Strategy

FAQs are split into two cache layers:

- **L1 — Category Index**: All category names + counts, prefix `[FAQ_CATEGORY_INDEX]`
- **L2 — FAQ Blocks**: 10 FAQs per block per category, prefix `[FAQ_BLOCK:{category}:{seq}]`

On FAQ change → 5s debounce → Celery task rebuilds all blocks → sends `max_tokens=1` requests to establish prefix cache.

## License

MIT
