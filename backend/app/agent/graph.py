from typing import TypedDict, Optional
import json

from app.agent.state import AgentState
from app.storage.file_store import get_faq_store
from app.services.qa_service import generate_answer
from app.core.llm_client import chat_completion


# Define graph nodes as async functions

async def preprocess_node(state: AgentState) -> AgentState:
    """Process prior knowledge and build context."""
    prior_text = ""
    if state.prior_knowledge_type == "text" and state.prior_knowledge_content:
        prior_text = state.prior_knowledge_content
    elif state.prior_knowledge_type == "document" and state.document_id:
        from app.services.document_service import get_document_content
        doc_text = get_document_content(state.document_id)
        if doc_text:
            prior_text = doc_text[:3000]
    state.prior_text = prior_text
    return state


async def category_filter_node(state: AgentState) -> AgentState:
    """L1 filter: match user question to FAQ categories."""
    all_faqs = get_faq_store().read_all()
    categories = {}
    for faq in all_faqs:
        cat = faq.get("category", "未分类")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(faq)

    # Build category index text
    cat_lines = ["# FAQ类别索引"]
    for cat, items in categories.items():
        cat_lines.append(f"- {cat}: {len(items)}条")
    state.category_index = "\n".join(cat_lines)

    # Simple keyword matching
    question_lower = state.question.lower()
    matched = []
    for cat in categories:
        cat_words = cat.lower().split()
        if any(word in question_lower for word in cat_words if len(word) > 1):
            matched.append(cat)

    if not matched:
        matched = list(categories.keys())

    state.matched_categories = matched

    # Collect candidates
    candidates = []
    for cat in matched:
        candidates.extend(categories[cat])
    state.faq_candidates = candidates
    state.candidates_count = len(candidates)

    return state


async def human_confirm_node(state: AgentState) -> AgentState:
    """Check if human confirmation is needed (candidates > 10)."""
    if state.candidates_count > 10:
        state.need_human_input = True
        cat_summary = "; ".join(
            f"{cat}: {len([f for f in state.faq_candidates if f.get('category') == cat])}"
            for cat in state.matched_categories
        )
        state.human_prompt = (
            f"候选FAQ共{state.candidates_count}条，涉及以下类别：{cat_summary}\n"
            f"用户问题：{state.question}\n"
            "是否需要限制FAQ范围？请选择要使用的类别或确认全部使用。"
        )
    else:
        state.need_human_input = False
    return state


async def generate_answer_node(state: AgentState) -> AgentState:
    """Generate final answer from FAQ candidates."""
    if not state.faq_candidates:
        state.answer = "未找到相关FAQ，无法回答您的问题。"
        state.references = []
        return state

    answer_data = await generate_answer(
        question=state.question,
        faq_candidates=state.faq_candidates[:10],
        prior_text=state.prior_text,
    )
    state.answer = answer_data["answer"]
    state.references = answer_data["references"]
    return state


# Simple graph runner (since LangGraph may have import complexities)
class AgentGraph:
    def __init__(self):
        self.nodes = [
            ("preprocess", preprocess_node),
            ("category_filter", category_filter_node),
            ("human_confirm", human_confirm_node),
            ("generate_answer", generate_answer_node),
        ]

    async def run(self, state: AgentState) -> AgentState:
        for name, node in self.nodes:
            if state.need_human_input and name == "generate_answer":
                continue
            state = await node(state)
            if state.error:
                break
        return state


agent_graph = AgentGraph()
