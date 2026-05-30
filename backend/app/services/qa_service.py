import json
from typing import AsyncGenerator, Optional

from app.storage.file_store import get_faq_store
from app.core.llm_client import chat_completion, chat_completion_stream
from app.core.config import settings

# ============================================================
# 提示词（用户可编辑）
# ============================================================

SYSTEM_PROMPT = """你是一个FAQ智能问答助手。请根据提供的FAQ库、先验知识以及自己的认识回答用户问题。

规则：
1. 优先使用FAQ库中的信息回答，如果FAQ中有匹配的问题，引用该FAQ回答问题。
2. 如果FAQ中没有完全匹配的内容，结合先验知识和你的知识给出回答，但需明确指出这不是标准FAQ内容。
3. 引用FAQ时，在答案中标注引用来源（FAQ ID和问题）。
"""

PRIOR_KNOWLEDGE_TEMPLATE = """
以下是先验知识，请优先遵循这些信息进行回答，可以自行回答用户的问题：

{content}
"""

# ============================================================
# 算法检索（快速，不调用LLM）
# ============================================================

def _score_faq_relevance(faq: dict, question: str) -> int:
    """Score how relevant a FAQ is to the question using keyword matching."""
    q_words = set(question.lower().split())
    score = 0

    # Match against question field
    faq_q_words = set(faq.get("question", "").lower().split())
    score += len(q_words & faq_q_words) * 3

    # Match against answer field
    faq_a_words = set(faq.get("answer", "").lower().split())
    score += len(q_words & faq_a_words) * 1

    # Match against category
    cat = faq.get("category", "").lower()
    if any(w in cat for w in q_words):
        score += 2

    # Match against tags
    for tag in faq.get("tags", []):
        if tag.lower() in question.lower():
            score += 2

    # Exact substring match in question
    if faq.get("question", "").lower() in question.lower() or question.lower() in faq.get("question", "").lower():
        score += 5

    return score


def _retrieve_relevant_faqs(question: str, max_results: int = 10) -> list[dict]:
    """Algorithmic FAQ retrieval. Fast, no LLM call."""
    all_faqs = get_faq_store().read_all()
    if not all_faqs:
        return []

    scored = [(faq, _score_faq_relevance(faq, question)) for faq in all_faqs]
    scored.sort(key=lambda x: x[1], reverse=True)

    # Filter out zero-scored items, keep top results
    candidates = [faq for faq, score in scored if score > 0]
    if not candidates:
        # Fallback: return most recent FAQs
        candidates = all_faqs

    return candidates[:max_results]


def _build_faq_context(faq_candidates: list[dict]) -> str:
    """Build FAQ context string."""
    context_parts = ["## 相关FAQ库内容\n"]
    for i, faq in enumerate(faq_candidates):
        context_parts.append(f"[FAQ {faq['id']}]")
        context_parts.append(f"类别: {faq.get('category', '')}")
        context_parts.append(f"问题: {faq['question']}")
        context_parts.append(f"答案: {faq['answer']}")
        if faq.get("tags"):
            context_parts.append(f"标签: {', '.join(faq['tags'])}")
        context_parts.append("")
    return "\n".join(context_parts)


def _extract_references(answer: str, faq_candidates: list[dict]) -> list[dict]:
    """Extract FAQ references mentioned in the answer."""
    references = []
    for faq in faq_candidates:
        if faq["id"] in answer:
            references.append({
                "id": faq["id"],
                "question": faq["question"],
                "category": faq.get("category", ""),
            })
    return references


# ============================================================
# 问答接口（非流式 + 流式）
# ============================================================

async def process_question(
    question: str,
    prior_knowledge_type: Optional[str] = None,
    prior_knowledge_content: Optional[str] = None,
    document_id: Optional[str] = None,
) -> dict:
    """Process question: algorithmic retrieval → LLM generation."""
    # 1. Algorithmic FAQ retrieval (fast, no LLM)
    candidates = _retrieve_relevant_faqs(question)

    if not candidates:
        return {
            "answer": "FAQ库为空，暂无法回答问题。请先录入FAQ数据。",
            "references": [],
        }

    # 2. Get prior knowledge
    prior_text = ""
    if prior_knowledge_type == "text" and prior_knowledge_content:
        prior_text = prior_knowledge_content
    elif prior_knowledge_type == "document" and document_id:
        from app.services.document_service import get_document_content
        doc_text = get_document_content(document_id)
        if doc_text:
            prior_text = doc_text[:3000]

    # 3. Build context and call LLM
    faq_context = _build_faq_context(candidates)

    system_content = SYSTEM_PROMPT
    if prior_text:
        system_content = PRIOR_KNOWLEDGE_TEMPLATE.format(content=prior_text) + "\n\n" + SYSTEM_PROMPT

    messages = [
        {"role": "system", "content": system_content + "\n\n" + faq_context},
        {"role": "user", "content": question},
    ]

    answer = await chat_completion(messages)
    references = _extract_references(answer, candidates)

    return {"answer": answer, "references": references}


async def process_question_stream(
    question: str,
    prior_knowledge_type: Optional[str] = None,
    prior_knowledge_content: Optional[str] = None,
    document_id: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """Process question with streaming response.

    Yields SSE-formatted strings:
      data: {"type": "token", "content": "..."}
      data: {"type": "done", "references": [...]}
      data: {"type": "error", "content": "..."}
    """
    # 1. Algorithmic FAQ retrieval (fast, no LLM)
    candidates = _retrieve_relevant_faqs(question)

    if not candidates:
        yield f"data: {json.dumps({'type': 'done', 'answer': 'FAQ库为空，暂无法回答问题。请先录入FAQ数据。', 'references': []})}\n\n"
        return

    # 2. Get prior knowledge
    prior_text = ""
    if prior_knowledge_type == "text" and prior_knowledge_content:
        prior_text = prior_knowledge_content
    elif prior_knowledge_type == "document" and document_id:
        from app.services.document_service import get_document_content
        doc_text = get_document_content(document_id)
        if doc_text:
            prior_text = doc_text[:3000]

    try:
        # 3. Build context
        faq_context = _build_faq_context(candidates)

        system_content = SYSTEM_PROMPT
        if prior_text:
            system_content = PRIOR_KNOWLEDGE_TEMPLATE.format(content=prior_text) + "\n\n" + SYSTEM_PROMPT

        messages = [
            {"role": "system", "content": system_content + "\n\n" + faq_context},
            {"role": "user", "content": question},
        ]

        # 4. Stream LLM response
        full_answer = ""
        async for token in chat_completion_stream(messages):
            full_answer += token
            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

        # 5. Extract references
        references = _extract_references(full_answer, candidates)
        yield f"data: {json.dumps({'type': 'done', 'references': references})}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
