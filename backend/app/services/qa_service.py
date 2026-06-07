import json
from typing import AsyncGenerator, Optional

from app.core.llm_client import chat_completion_stream
from app.core.config import settings
from app.services.block_manager import block_manager

SYSTEM_PROMPT = """你是一个智能AI助手，可以基于FAQ库和自身知识回答用户问题。

规则：
1. 当用户问题涉及具体政策、流程、规定时，优先从FAQ库中查找相关信息。
2. 引用FAQ时标注来源ID。
3. 对于非FAQ问题（如闲聊、常识），直接用自己的知识回答。"""

# 每次提问都搜索FAQ库，不做智能判断


async def process_question_stream(
    messages: list[dict],
    session_id: str = "",
    user_id: str = "",
    prior_knowledge_type: Optional[str] = None,
    prior_knowledge_content: Optional[str] = None,
    document_id: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """Process multi-turn conversation with streaming.

    Yields SSE events:
      {"type": "status", "content": "..."}       - search process updates
      {"type": "search_decision", "search": bool} - whether searching FAQ
      {"type": "token", "content": "..."}         - answer tokens
      {"type": "done", "references": [...]}       - completion
      {"type": "error", "content": "..."}          - error
    """
    if not messages:
        yield f"data: {json.dumps({'type': 'error', 'content': 'No messages provided'})}\n\n"
        return

    question = messages[-1]["content"] if messages else ""
    history = messages[:-1] if len(messages) > 1 else None

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
        yield f"data: {json.dumps({'type': 'status', 'content': f'正在搜索FAQ库（共{block_manager.block_count}个数据块）...'})}\n\n"

        if block_manager.block_count == 0:
            yield f"data: {json.dumps({'type': 'status', 'content': 'FAQ库为空，跳过搜索。'})}\n\n"
        else:
            relevant_ids = await block_manager.search_relevant_faq_ids(question, history)
            if relevant_ids:
                selected_faqs = block_manager.get_faqs_by_ids(relevant_ids, settings.faq_max_results)
                yield f"data: {json.dumps({'type': 'status', 'content': f'找到 {len(relevant_ids)} 条相关FAQ，已选择 {len(selected_faqs)} 条作为参考。'})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'status', 'content': '未找到直接相关的FAQ条目。'})}\n\n"

        # Step 4: Build context and generate answer
        yield f"data: {json.dumps({'type': 'status', 'content': '正在生成回答...'})}\n\n"

        # Build messages in cache-friendly order:
        #   1. system prompt (fixed → cached)
        #   2. conversation history (partially cached)
        #   3. current question
        #   4. FAQ context (varies → at end, won't break prefix cache)
        conv_messages = []

        # 1. System prompt (fixed, with optional prior knowledge)
        system_content = SYSTEM_PROMPT
        if prior_text:
            system_content = f"以下是先验知识，请优先遵循：\n{prior_text}\n\n{system_content}"
        conv_messages.append({"role": "system", "content": system_content})

        # 2. All conversation history (prefix grows predictably)
        if history:
            for msg in history:
                conv_messages.append({"role": msg["role"], "content": msg["content"]})

        # 3. Current user question
        conv_messages.append({"role": "user", "content": question})

        # 4. FAQ context at the end (varies per query, doesn't break prefix cache)
        if selected_faqs:
            faq_context = "\n\n以下是来自FAQ库的参考信息：\n\n"
            for faq in selected_faqs:
                faq_context += f"[FAQ {faq['id']}] {faq['question']}\n{faq['answer']}\n\n"
            conv_messages.append({"role": "system", "content": faq_context})

        # Stream the answer
        full_answer = ""
        async for token in chat_completion_stream(conv_messages):
            full_answer += token
            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

        # Extract references
        references = []
        for faq in selected_faqs:
            if faq["id"] in full_answer:
                references.append({
                    "id": faq["id"],
                    "question": faq["question"],
                    "category": faq.get("category", ""),
                })

        yield f"data: {json.dumps({'type': 'done', 'references': references})}\n\n"

        # Auto-save conversation to session store
        if session_id and user_id:
            from app.storage import session_store
            all_msgs = []
            if history:
                all_msgs.extend(history)
            all_msgs.append({"role": "user", "content": question})
            all_msgs.append({"role": "assistant", "content": full_answer})
            session_store.append_messages(user_id, session_id, all_msgs)

    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"


async def process_question(
    messages: list[dict],
    session_id: str = "",
    user_id: str = "",
    prior_knowledge_type: Optional[str] = None,
    prior_knowledge_content: Optional[str] = None,
    document_id: Optional[str] = None,
) -> dict:
    """Non-streaming version - collects stream result into a single response."""
    answer = ""
    references = []
    async for event_str in process_question_stream(
        messages, session_id, user_id, prior_knowledge_type, prior_knowledge_content, document_id
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
