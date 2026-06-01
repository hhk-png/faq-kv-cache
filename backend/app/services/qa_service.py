import json
from typing import AsyncGenerator, Optional

from app.core.llm_client import chat_completion, chat_completion_stream
from app.core.config import settings
from app.services.block_manager import block_manager

SYSTEM_PROMPT = """你是一个智能AI助手，可以基于FAQ库和自身知识回答用户问题。

规则：
1. 当用户问题涉及具体政策、流程、规定时，优先从FAQ库中查找相关信息。
2. 引用FAQ时标注来源ID。
3. 对于非FAQ问题（如闲聊、常识），直接用自己的知识回答。"""

SEARCH_DECISION_PROMPT = """你是一个FAQ搜索决策助手。请判断是否需要搜索FAQ库来回答用户的问题。

需要搜索FAQ的情况：用户询问具体政策、流程、规定、手续、申请方法、费用、条件、所需材料等。
不需要搜索FAQ的情况：日常聊天、问候、常识问题、观点讨论、创意写作等与具体政策无关的内容。

只需回复"search"或"nosearch"，不要包含其他文字。"""


async def _should_search_faq(question: str, history: list[dict] | None = None) -> bool:
    """Use LLM to decide if FAQ search is needed."""
    conv_parts = []
    if history:
        for msg in history[-2:]:
            role = "用户" if msg["role"] == "user" else "助手"
            conv_parts.append(f"{role}: {msg['content']}")
    conv_parts.append(f"用户: {question}")
    conv_context = "\n".join(conv_parts)

    try:
        result = await chat_completion(
            messages=[
                {"role": "system", "content": SEARCH_DECISION_PROMPT},
                {"role": "user", "content": conv_context},
            ],
            model=settings.llm_model,
            max_tokens=10,
            temperature=0,
        )
        result = result.strip().lower()
        # 检查是否明确说了不需要搜索
        if result.startswith("no") or "不" in result[:5]:
            return False
        return True  # 默认搜索
    except Exception:
        return True  # Default to search on error


async def process_question_stream(
    messages: list[dict],
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
        # Step 1: Decide if FAQ search is needed
        yield f"data: {json.dumps({'type': 'status', 'content': '正在分析问题...'})}\n\n"
        should_search = await _should_search_faq(question, history)
        yield f"data: {json.dumps({'type': 'search_decision', 'search': should_search})}\n\n"

        # Step 2: Get prior knowledge
        prior_text = ""
        if prior_knowledge_type == "text" and prior_knowledge_content:
            prior_text = prior_knowledge_content
        elif prior_knowledge_type == "document" and document_id:
            from app.services.document_service import get_document_content
            doc_text = get_document_content(document_id)
            if doc_text:
                prior_text = doc_text[:3000]

        # Step 3: Search FAQ if needed
        selected_faqs = []
        if should_search:
            yield f"data: {json.dumps({'type': 'status', 'content': f'正在搜索FAQ库（共{block_manager.block_count}个数据块）...'})}\n\n"

            if block_manager.block_count == 0:
                yield f"data: {json.dumps({'type': 'status', 'content': 'FAQ库为空，跳过搜索。'})}\n\n"
            else:
                # Search all blocks for relevant FAQ IDs
                relevant_ids = await block_manager.search_relevant_faq_ids(question, history)
                if relevant_ids:
                    # If less than max_results, take all; otherwise take top
                    selected_faqs = block_manager.get_faqs_by_ids(relevant_ids, settings.faq_max_results)
                    yield f"data: {json.dumps({'type': 'status', 'content': f'找到 {len(relevant_ids)} 条相关FAQ，已选择 {len(selected_faqs)} 条作为参考。'})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'status', 'content': '未找到直接相关的FAQ条目。'})}\n\n"

        # Step 4: Build context and generate answer
        yield f"data: {json.dumps({'type': 'status', 'content': '正在生成回答...'})}\n\n"

        system_content = SYSTEM_PROMPT
        if prior_text:
            system_content = f"以下是先验知识，请优先遵循：\n{prior_text}\n\n{system_content}"

        # Build conversation context for the LLM
        conv_messages = []
        conv_messages.append({"role": "system", "content": system_content})

        # Add selected FAQs as context
        if selected_faqs:
            faq_context = "以下是来自FAQ库的参考信息：\n\n"
            for i, faq in enumerate(selected_faqs):
                faq_context += f"[FAQ {faq['id']}] {faq['question']}\n{faq['answer']}\n\n"
            conv_messages.append({"role": "system", "content": faq_context})

        # Add conversation history
        if history:
            for msg in history[-6:]:  # Last 6 turns
                conv_messages.append({"role": msg["role"], "content": msg["content"]})

        # Add current question
        conv_messages.append({"role": "user", "content": question})

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

    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"


async def process_question(
    messages: list[dict],
    prior_knowledge_type: Optional[str] = None,
    prior_knowledge_content: Optional[str] = None,
    document_id: Optional[str] = None,
) -> dict:
    """Non-streaming version - collects stream result into a single response."""
    answer = ""
    references = []
    async for event_str in process_question_stream(
        messages, prior_knowledge_type, prior_knowledge_content, document_id
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
