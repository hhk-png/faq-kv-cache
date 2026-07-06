# FAQ KV Cache Agent

基于 **LLM Prefix Caching** 的智能 FAQ 问答系统。预缓存 FAQ 的 KV Cache，在用户提问时快速匹配相关条目并流式生成回答，兼顾速度与成本。

> **核心思路**：将 FAQ 按类别分块，启动时通过 `max_tokens=1` 请求预建立 LLM 的 prefix cache；用户提问时先用 LLM 匹配类别，再从缓存命中块中检索相关 FAQ，最后生成回答。FAQ 检索和回答生成各只调一次 LLM。

---

## 特性

- **FAQ 管理** — 增删改查、批量导入（JSON/CSV）、按类别/关键词过滤
- **问答对话** — 基于 SSE 的流式回答，展示引用来源，注入先验知识
- **文档管理** — 上传 PDF/DOCX/TXT/MD，自动提取文本内容
- **KV Cache 加速** — FAQ 变更后自动重建缓存块并预热
- **多会话** — 支持多用户多会话隔离，历史消息持久化

---

## 架构

```
User Question
    │
    ▼
┌─────────────────────────────────────────┐
│  Step 1: Catgeory Matching (LLM call)   │  ← LLM 匹配合适类别
│  "哪些类别与用户问题相关？"              │
└──────────────┬──────────────────────────┘
               │ matched categories
               ▼
┌─────────────────────────────────────────┐
│  Step 2: In-Block Retrieval (LLM call)  │  ← 对每个候选块并发搜索（KV Cache 命中）
│  "找出与当前对话相关的 FAQ"              │
└──────────────┬──────────────────────────┘
               │ matched FAQ items
               ▼
┌─────────────────────────────────────────┐
│  Step 3: Answer Generation (Streaming)  │  ← 拼接上下文，SSE 流式吐出
│  系统提示 + 历史消息 + FAQ + 问题        │
└─────────────────────────────────────────┘
```

### 缓存策略

```
启动 / FAQ变更
    │
    ▼
┌──────────────────────┐
│  rebuild_blocks()    │  ← 按类别分块，每块 ~300K tokens
│  类别A: block_001    │
│  类别A: block_002    │
│  类别B: block_001    │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│  warmup_all_blocks() │  ← 并发请求各块，max_tokens=1
│  prompt = prefix +   │    建立 prefix cache
│  content + warmup q  │
└──────────────────────┘
```

---

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | React 18 + TypeScript + TailwindCSS + Vite + pnpm |
| 后端 | Python 3.10+ + FastAPI + Uvicorn |
| LLM SDK | OpenAI Python SDK（兼容 DeepSeek / 任意 OpenAI 风格 API） |
| 存储 | 本地 JSON 文件 + `filelock` 线程安全读写 |
| 部署 | Docker + Docker Compose + Nginx |

---

## 快速开始

### 前置要求

- Python 3.10+
- Node.js 24+ + pnpm
- LLM API Key（DeepSeek / OpenAI / 兼容接口）

### 1. 后端

```bash
cd backend

# 安装依赖
python run.py install
# 或：pip install -r requirements.txt

# 配置环境变量
cp .env-example .env
# 编辑 .env，填入你的 API Key 和模型信息

# 启动 API 服务
python run.py api
# → http://localhost:8000
```

### 2. 前端

```bash
cd frontend
pnpm install
pnpm dev
# → http://localhost:5173
```

Vite 会自动将 `/api/*` 请求代理到 `localhost:8000`。

### 3. Docker 部署

```bash
docker-compose up -d
```

---

## 项目结构

```
faq-kv-cache/
├── frontend/                     # React 前端
│   ├── src/
│   │   ├── pages/
│   │   │   ├── QaChat/           # 问答对话页
│   │   │   ├── FaqManage/        # FAQ 管理页
│   │   │   ├── DocumentManage/   # 文档管理页
│   │   │   └── Login.tsx         # 用户登录页
│   │   ├── components/
│   │   │   ├── Layout.tsx        # 全局布局 + 侧边栏
│   │   │   ├── ChatMessage.tsx   # 消息气泡（Markdown 渲染）
│   │   │   ├── FaqCard.tsx       # FAQ 卡片
│   │   │   ├── DocumentCard.tsx  # 文档卡片
│   │   │   └── PriorKnowledgeSelector.tsx  # 先验知识选择器
│   │   ├── services/             # API 客户端
│   │   │   ├── qa.ts             # 问答（含流式重连逻辑）
│   │   │   ├── faq.ts
│   │   │   ├── document.ts
│   │   │   └── session.ts
│   │   ├── types/index.ts        # TypeScript 类型定义
│   │   ├── App.tsx               # 路由入口
│   │   └── main.tsx              # 挂载点
│   ├── vite.config.ts
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── api/                  # FastAPI 路由
│   │   │   ├── qa.py             # 问答接口（流式 + 非流式）
│   │   │   ├── faq.py            # FAQ CRUD
│   │   │   ├── document.py       # 文档上传/管理
│   │   │   ├── session.py        # 会话管理
│   │   │   └── auth.py           # 登录认证
│   │   ├── services/
│   │   │   ├── qa_service.py     # 问答核心逻辑
│   │   │   ├── block_manager.py  # KV Cache 块管理 + 类别匹配 + 块内检索
│   │   │   ├── faq_service.py    # FAQ 业务逻辑
│   │   │   └── document_service.py  # 文档提取
│   │   ├── core/
│   │   │   ├── config.py         # Pydantic 配置（.env 加载）
│   │   │   └── llm_client.py     # LLM 客户端（同步/异步/流式/缓存预热）
│   │   ├── storage/              # 存储层
│   │   │   ├── file_store.py     # JSON 文件 + filelock 读写
│   │   │   ├── session_store.py  # 会话持久化
│   │   │   └── user_store.py     # 用户存储
│   │   └── main.py               # FastAPI 应用入口 + 启动缓存预热
│   ├── data/
│   │   ├── faq_datasets/         # FAQ 数据集（按类别分文件）
│   │   │   ├── oncology/         # 肿瘤学 FAQ
│   │   │   └── amagasaki/        # 市政 FAQ（日语翻译）
│   │   └── sessions/             # 会话记录
│   ├── scripts/                  # 管理脚本
│   │   ├── faq_cli.py            # FAQ CLI（增删查 + 导入）
│   │   ├── import_oncology_csv.py
│   │   ├── translate_faqs.py     # FAQ 翻译
│   │   └── split_faqs.py         # 数据集拆分
│   ├── tests/                    # pytest 测试
│   ├── run.py                    # 一键启动脚本
│   ├── requirements.txt
│   └── pyproject.toml
│
├── docker-compose.yml
├── nginx.conf
└── Makefile
```

---

## API 文档

### 问答

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/qa/ask` | 非流式问答，返回完整回答 + 引用 |
| `POST` | `/api/qa/ask/stream` | 流式问答（SSE），逐 token 推送 |

**流式请求体**：

```json
{
  "question": "化疗期间需要注意什么？",
  "session_id": "session_xxx",
  "user_id": "user_xxx",
  "prior_knowledge_type": "text",
  "prior_knowledge_content": "患者为 65 岁女性...",
  "document_id": null,
  "previous_assistant_content": null
}
```

**流式 SSE 事件**：

```
data: {"type":"status","content":"正在匹配相关类别..."}

data: {"type":"token","content":"化疗"}

data: {"type":"token","content":"期间"}

data: {"type":"done","references":[{"id":"...","question":"...","category":"..."}]}

data: {"type":"error","content":"错误信息"}
```

| 事件类型 | 说明 |
|----------|------|
| `status` | 处理进度（搜索中、生成中） |
| `token`  | 逐 token 回答内容 |
| `done`   | 回答完毕，携带引用来源 |
| `error`  | 服务端错误 |

### FAQ 管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET`    | `/api/faqs` | 列表，支持 `?category=&keyword=` 过滤 |
| `POST`   | `/api/faqs` | 创建 FAQ |
| `POST`   | `/api/faqs/batch` | 批量创建 |
| `GET`    | `/api/faqs/{id}` | 获取单个 |
| `PUT`    | `/api/faqs/{id}` | 更新 |
| `DELETE` | `/api/faqs/{id}` | 删除 |
| `POST`   | `/api/faqs/rebuild-cache` | 触发缓存重建 + 预热 |

### 文档管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST`   | `/api/documents/upload` | 上传文件（PDF/DOCX/TXT/MD） |
| `GET`    | `/api/documents` | 文档列表 |
| `GET`    | `/api/documents/{id}/content` | 获取提取的文本 |
| `DELETE` | `/api/documents/{id}` | 删除文档 |

### 会话

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST`   | `/api/sessions` | 创建会话 |
| `GET`    | `/api/sessions` | 用户会话列表 |
| `GET`    | `/api/sessions/{id}` | 获取会话消息 |
| `DELETE` | `/api/sessions/{id}` | 删除会话 |

### 其他

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET`    | `/api/health` | 健康检查，返回块数等信息 |
| `GET`    | `/api/cache/status` | 缓存预热状态 |

---

## 环境变量

通过 `.env` 或环境变量配置（参见 `app/core/config.py`）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LLM_API_KEY` | `sk-your-api-key` | LLM API 密钥 |
| `LLM_BASE_URL` | `https://api.deepseek.com/v1` | API 地址（兼容 OpenAI 格式） |
| `LLM_MODEL` | `deepseek-chat` | 模型名称 |
| `LLM_MAX_TOKENS` | `4096` | 单次最大输出 token 数 |
| `LLM_TEMPERATURE` | `0.3` | 生成温度 |
| `FAQ_BLOCK_MIN_TOKENS` | `300000` | 每个缓存块的最小 token 数 |
| `FAQ_MAX_RESULTS` | `5` | 每次问答最多引用的 FAQ 条数 |
| `DATA_DIR` | `data` | 数据存储目录 |
| `FAQ_DATASET_PATH` | `data/faq_datasets/oncology` | FAQ 数据集路径 |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | 允许的跨域来源 |

---

## 数据格式

FAQ 数据集按类别分文件存储，每个文件一个 JSON 数组：

```json
[
  {
    "id": "a1b2c3d4e5f6",
    "category": "化疗",
    "question": "化疗期间可以吃中药吗？",
    "answer": "化疗期间使用中药需要在主治医生指导下进行...",
    "tags": ["化疗", "中药", "副作用"]
  }
]
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 否 | 唯一 ID，不传则自动生成 |
| `category` | string | 是 | 类别/科室 |
| `question` | string | 是 | 问题 |
| `answer` | string | 是 | 答案 |
| `tags` | string[] | 否 | 可选标签 |

切换数据集只需修改配置 `FAQ_DATASET_PATH`。

---

## Cache Warmup 详解

### 为什么要预热？

LLM 的 **prompt prefix caching** 机制会缓存输入开头的 KV 计算状态。当新请求的前缀与已缓存内容匹配时，无需重新计算，显著降低首 token 延迟和成本。

### 预热流程

1. **分块**（`rebuild_blocks`）：按类别分组，每组累计 ~100K tokens 切一块，每块附带 `[CAT:{category}:{seq}]` 前缀标记
2. **预热**（`warmup_all_blocks`）：对每个块发送 `max_tokens=1` 的请求，让 LLM 服务端缓存该前缀的 KV 状态
3. **触发**：FAQ 创建/更新/删除后 5 秒防抖，自动触发重建 + 预热

### 查询流程

```
用户问题
  │
  ▼
类别匹配（LLM）──────→ 从所有类别中选出相关类别
  │
  ▼
块内搜索（LLM × N）──→ 对每个相关块的缓存进行并发检索（KV Cache 命中）
  │
  ▼
生成回答（SSE）──────→ 拼接完整上下文，流式输出
```

---

## CLI 工具

```bash
cd backend

# 添加单条 FAQ
python scripts/faq_cli.py add \
  --category "化疗" \
  --question "化疗后白细胞低怎么办？" \
  --answer "化疗后白细胞减少是常见副作用..."

# 从 JSON 导入
python scripts/faq_cli.py import \
  --file scripts/sample_data/faqs.json

# 从 CSV 导入
python scripts/faq_cli.py import \
  --file scripts/sample_data/faqs.csv \
  --format csv

# 列出所有 FAQ
python scripts/faq_cli.py list

# 其他工具脚本
python scripts/translate_faqs.py   # 翻译 FAQ
python scripts/split_faqs.py       # 拆分数据集
python scripts/import_oncology_csv.py  # 导入肿瘤学 CSV
```

---

## 测试

```bash
cd backend

# 运行所有测试
python run.py test
# 或：pytest tests/ -v --tb=short

# 带覆盖率
python run.py test --coverage

# 监听模式（文件变化自动重跑）
python run.py test --watch
```

## License

MIT
