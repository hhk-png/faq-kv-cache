// ===== FAQ Types =====
export interface FaqItem {
  id: string;
  category: string;
  question: string;
  answer: string;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface FaqListResponse {
  data: FaqItem[];
  total: number;
}

export interface FaqCreateRequest {
  category: string;
  question: string;
  answer: string;
  tags?: string[];
}

export interface FaqBatchCreateRequest {
  items: FaqCreateRequest[];
}

// ===== Document Types =====
export interface DocumentItem {
  id: string;
  filename: string;
  title: string;
  file_type: string;
  status: 'processing' | 'ready' | 'error';
  char_count: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentContent {
  id: string;
  content: string;
  status: string;
}

export interface DocumentListResponse {
  data: DocumentItem[];
  total: number;
}

// ===== QA Types =====
export interface MessageItem {
  role: 'user' | 'assistant';
  content: string;
}

export interface AskRequest {
  messages: MessageItem[];
  prior_knowledge_type?: 'document' | 'text' | null;
  prior_knowledge_content?: string;
  document_id?: string;
}

export interface QaResponse {
  answer: string | null;
  references: FaqReference[];
}

export interface FaqReference {
  id: string;
  question: string;
  category: string;
}

// ===== SSE Stream Types =====
export interface SseStatus {
  type: 'status';
  content: string;
}

export interface SseSearchDecision {
  type: 'search_decision';
  search: boolean;
}

export interface SseToken {
  type: 'token';
  content: string;
}

export interface SseDone {
  type: 'done';
  answer?: string;
  references: FaqReference[];
}

export interface SseError {
  type: 'error';
  content: string;
}

export type SseEvent = SseStatus | SseSearchDecision | SseToken | SseDone | SseError;

// ===== API Response Types =====
export interface ApiResponse<T> {
  data: T;
  message?: string;
  total?: number;
}

// ===== Category Type =====
export interface CategoryInfo {
  name: string;
  count: number;
}
