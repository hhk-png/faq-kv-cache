import type { ApiResponse } from '../types'

const BASE_URL = '/api/sessions'

// Get user ID from localStorage (persistent across tabs)
function getUserId(): string {
  return localStorage.getItem('faq_user_id') || ''
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-User-ID': getUserId(),
  }
  // Merge with any additional headers from options
  const existing = (options?.headers as Record<string, string>) || {}
  for (const [k, v] of Object.entries(existing)) {
    if (typeof v === 'string') headers[k] = v
  }
  const res = await fetch(url, { ...options, headers })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export interface SessionInfo {
  id: string
  title: string
  created_at: string
  updated_at: string
}

export async function fetchSessions(): Promise<ApiResponse<SessionInfo[]>> {
  return request<ApiResponse<SessionInfo[]>>(BASE_URL)
}

export async function createSession(title = '新对话'): Promise<ApiResponse<SessionInfo>> {
  return request<ApiResponse<SessionInfo>>(BASE_URL, {
    method: 'POST',
    body: JSON.stringify({ title }),
  })
}

export async function fetchSession(sessionId: string): Promise<ApiResponse<SessionInfo & { messages: { role: string; content: string }[] }>> {
  return request(`${BASE_URL}/${sessionId}`)
}

export async function updateSessionTitle(sessionId: string, title: string): Promise<ApiResponse<null>> {
  return request(`${BASE_URL}/${sessionId}`, {
    method: 'PUT',
    body: JSON.stringify({ title }),
  })
}

export async function deleteSession(sessionId: string): Promise<ApiResponse<null>> {
  return request(`${BASE_URL}/${sessionId}`, { method: 'DELETE' })
}

export async function appendMessages(sessionId: string, messages: { role: string; content: string }[]): Promise<ApiResponse<null>> {
  return request(`${BASE_URL}/${sessionId}/messages`, {
    method: 'POST',
    body: JSON.stringify({ messages }),
  })
}
