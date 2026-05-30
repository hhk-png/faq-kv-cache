from typing import Optional
from dataclasses import dataclass, field


@dataclass
class AgentState:
    question: str = ""
    prior_knowledge_type: Optional[str] = None
    prior_knowledge_content: Optional[str] = None
    document_id: Optional[str] = None
    prior_text: str = ""
    category_index: str = ""
    matched_categories: list = field(default_factory=list)
    faq_candidates: list = field(default_factory=list)
    candidates_count: int = 0
    need_human_input: bool = False
    human_prompt: Optional[str] = None
    confirmed_categories: list = field(default_factory=list)
    answer: Optional[str] = None
    references: list = field(default_factory=list)
    error: Optional[str] = None
