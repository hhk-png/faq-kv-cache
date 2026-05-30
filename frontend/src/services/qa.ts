import type { AskRequest, ApiResponse, QaResponse, SseEvent } from '../types'

const BASE_URL = '/api/qa'

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export async function askQuestion(req: AskRequest): Promise<ApiResponse<QaResponse>> {
  return request<ApiResponse<QaResponse>>(`${BASE_URL}/ask`, {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export async function askQuestionStream(
  req: AskRequest,
  callbacks: {
    onToken: (token: string) => void
    onDone: (references: { id: string; question: string; category: string }[]) => void
    onError: (error: string) => void
  },
): Promise<void> {
  const res = await fetch(`${BASE_URL}/ask/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    callbacks.onError(err.detail || `HTTP ${res.status}`)
    return
  }

  const reader = res.body?.getReader()
  if (!reader) {
    callbacks.onError('No response body')
    return
  }

  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed.startsWith('data: ')) continue

        try {
          const data: SseEvent = JSON.parse(trimmed.slice(6))
          if (data.type === 'token') {
            callbacks.onToken(data.content)
          } else if (data.type === 'done') {
            callbacks.onDone(data.references)
          } else if (data.type === 'error') {
            callbacks.onError(data.content)
          }
        } catch {
          // Skip malformed JSON lines
        }
      }
    }
  } catch (err: any) {
    callbacks.onError(err.message || 'Stream read error')
  }
}
