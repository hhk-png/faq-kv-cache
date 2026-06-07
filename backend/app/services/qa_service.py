import json
import logging
from typing import AsyncGenerator, Optional

from app.core.llm_client import chat_completion_stream
from app.core.config import settings
from app.services.block_manager import block_manager

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个智能AI助手，可以基于FAQ库和自身知识回答用户问题。

规则：
1. 当用户问题涉及具体政策、流程、规定时，优先从FAQ库中查找相关信息。
2. 引用FAQ时标注来源ID。
3. 对于非FAQ问题（如闲聊、常识），直接用自己的知识回答。"""

PRIOR_KNOWLEDGE_TEMPLATE = """
以下是先验知识，请优先遵循这些信息进行回答，可以自行回答用户的问题：

{content}
"""


def _load_history(session_id: str, user_id: str) -> list[dict] | None:
    """Load conversation history from session store."""
    if not session_id or not user_id:
        return None
    try:
        from app.storage import session_store
        stored = session_store.get_messages(user_id, session_id)
        return stored if stored else None
    except Exception:
        return None


def _format_references(faq_candidates: list[dict]) -> list[dict]:
    """Return all FAQ candidates as references for transparency."""
    return [
        {
            "id": faq["id"],
            "question": faq["question"],
            "category": faq.get("category", ""),
        }
        for faq in faq_candidates
    ]


async def process_question_stream(
    question: str,
    session_id: str = "",
    user_id: str = "",
    prior_knowledge_type: Optional[str] = None,
    prior_knowledge_content: Optional[str] = None,
    document_id: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """Process question with streaming. History loaded from session store."""
    if not question.strip():
        yield f"data: {json.dumps({'type': 'error', 'content': 'Question is required'})}\n\n"
        return

    history = _load_history(session_id, user_id)

    try:
        # Step 1: Get prior knowledge
        prior_text = ""
        if prior_knowledge_type == "text" and prior_knowledge_content:
            prior_text = prior_knowledge_content
        elif prior_knowledge_type == "document" and document_id:
            from app.services.document_service import get_document_content
            doc_text = get_document_content(document_id)
            if doc_text:
                prior_text = doc_text[:3000]

        # Step 2: Always search FAQ
        selected_faqs = []
        if block_manager.category_count == 0:
            yield f"data: {json.dumps({'type': 'status', 'content': 'FAQ库为空，跳过搜索。'})}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'status', 'content': '正在匹配相关类别...'})}\n\n"
            matched_cats = await block_manager.match_categories(question)
            if matched_cats:
                yield f"data: {json.dumps({'type': 'status', 'content': f'匹配到 {len(matched_cats)} 个相关类别，正在搜索...'})}\n\n"
                relevant_ids = await block_manager.search_ids_in_blocks(matched_cats, question, history)
                if relevant_ids:
                    selected_faqs = block_manager.get_faqs_by_ids(relevant_ids, settings.faq_max_results)
                    yield f"data: {json.dumps({'type': 'status', 'content': f'找到 {len(relevant_ids)} 条相关FAQ，已选择 {len(selected_faqs)} 条作为参考。'})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'status', 'content': '未在相关类别中找到匹配的FAQ条目。'})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'status', 'content': '未找到直接相关的FAQ条目。'})}\n\n"

        # Step 3: Build context and generate answer
        yield f"data: {json.dumps({'type': 'status', 'content': '正在生成回答...'})}\n\n"

        conv_messages = []

        # System prompt (fixed, with optional prior knowledge)
        system_content = SYSTEM_PROMPT
        if prior_text:
            system_content = f"以下是先验知识，请优先遵循：\n{prior_text}\n\n{system_content}"
        conv_messages.append({"role": "system", "content": system_content})

        # All conversation history
        if history:
            for msg in history:
                conv_messages.append({"role": msg["role"], "content": msg["content"]})

        # Build user message — FAQ context comes BEFORE the question so the model reads it as relevant context
        user_content = question
        if selected_faqs:
            faq_context = "\n\n以下是来自FAQ库的参考信息，请优先基于这些信息回答：\n\n"
            for faq in selected_faqs:
                faq_context += f"[FAQ {faq['id']}] {faq['category']} {faq['question']}\n{faq['answer']}\n\n"
            faq_context += "\n请基于以上FAQ信息回答用户的问题。如果FAQ信息不足以回答，可以结合自身知识补充。"
            user_content = faq_context + "\n\n" + question
        else:
            # Explicitly tell the AI no FAQ was found — prevents AI from fabricating a search narrative
            user_content = question + "\n\n【系统】FAQ库中未找到与问题相关的条目，请直接用自己的知识回答。"
        conv_messages.append({"role": "user", "content": user_content})

        # Stream the answer
        logger.info(f"开始生成回答，上下文共 {sum(len(m.get('content','')) for m in conv_messages)} 字符")
        full_answer = ""
        async for token in chat_completion_stream(conv_messages):
            full_answer += token
            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

        # Extract references
        references = _format_references(selected_faqs)
        yield f"data: {json.dumps({'type': 'done', 'references': references})}\n\n"

        # Auto-save conversation to session store (only new messages, append handles merging)
        if session_id and user_id:
            from app.storage import session_store
            session_store.append_messages(user_id, session_id, [
                {"role": "user", "content": question},
                {"role": "assistant", "content": full_answer},
            ])

    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"


async def process_question(
    question: str,
    session_id: str = "",
    user_id: str = "",
    prior_knowledge_type: Optional[str] = None,
    prior_knowledge_content: Optional[str] = None,
    document_id: Optional[str] = None,
) -> dict:
    """Non-streaming version."""
    answer = ""
    references = []
    async for event_str in process_question_stream(
        question, session_id, user_id, prior_knowledge_type, prior_knowledge_content, document_id
    ):
        prefix = "data: "
        if event_str.startswith(prefix):
            try:
                data = json.loads(event_str[len(prefix):].strip())
                if data.get("type") == "token":
                    answer += data.get("content", "")
                elif data.get("type") == "done":
                    references = data.get("references", [])
            except json.JSONDecodeError:
                pass
    return {"answer": answer, "references": references}
