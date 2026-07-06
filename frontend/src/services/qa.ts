import type { AskRequest, ApiResponse, QaResponse, SseEvent } from '../types'

const BASE_URL = '/api/qa'
const MAX_RETRIES = 3
const FETCH_TIMEOUT = 30_000 // 初始连接超时
const MAX_BACKOFF = 5_000   // 最大退避时间

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
    body: JSON.stringify({ ...req, user_id: localStorage.getItem('faq_user_id') || '' }),
  })
}

/** 判断错误是否可重试 — 网络问题 / 5xx / 超时 / 429 */
function isRetryable(err: unknown): boolean {
  if (err instanceof DOMException && err.name === 'AbortError') return true
  const msg = (err as any)?.message ?? String(err)
  // fetch 网络错误（TypeError: Failed to fetch）或服务端过载
  if (/Failed to fetch|NetworkError|network|timeout|timed out/i.test(msg)) return true
  // 5xx / 429 由调用方通过 HTTP 状态码判断，传入消息中
  if (/(5\d{2}|429)/.test(msg)) return true
  return false
}

/** 指数退避等待 */
function backoff(attempt: number): Promise<void> {
  const delay = Math.min(1000 * 2 ** attempt + Math.random() * 500, MAX_BACKOFF)
  return new Promise(r => setTimeout(r, delay))
}

export async function askQuestionStream(
  req: AskRequest,
  sessionId: string,
  callbacks: {
    onStatus?: (status: string) => void
    onSearchDecision?: (search: boolean) => void
    onToken: (token: string) => void
    onDone: (references: { id: string; question: string; category: string }[]) => void
    onError: (error: string) => void
  },
): Promise<void> {
  let accumulatedContent = ''

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    // 如果不是首次，通知用户正在重连
    if (attempt > 0) {
      callbacks.onStatus?.(`⚠️ 连接中断，正在进行第 ${attempt} 次重试...`)
    }

    // 构建请求体
    const body: Record<string, unknown> = {
      ...req,
      session_id: sessionId,
      user_id: localStorage.getItem('faq_user_id') || '',
    }
    // 如果有已经收到的内容，传给后端让 LLM 续写
    if (accumulatedContent) {
      body.previous_assistant_content = accumulatedContent
    }

    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT)

    try {
      const res = await fetch(`${BASE_URL}/ask/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: controller.signal,
      })
      clearTimeout(timeoutId)

      if (!res.ok) {
        // 4xx（除 408/429 外）不可重试，直接报错
        if (res.status >= 400 && res.status < 500 && res.status !== 408 && res.status !== 429) {
          const err = await res.json().catch(() => ({ detail: res.statusText }))
          callbacks.onError(err.detail || `HTTP ${res.status}`)
          return
        }
        throw new Error(`HTTP ${res.status}`)
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
              switch (data.type) {
                case 'token':
                  accumulatedContent += data.content
                  callbacks.onToken(data.content)
                  break
                case 'done':
                  callbacks.onDone(data.references)
                  break
                case 'error':
                  // 服务端错误不重试
                  callbacks.onError(data.content)
                  return
                case 'status':
                  // 重连中的状态消息不要覆盖用户看到的消息链
                  if (attempt === 0) {
                    callbacks.onStatus?.(data.content)
                  }
                  break
                case 'search_decision':
                  callbacks.onSearchDecision?.(data.search)
                  break
              }
            } catch {
              // Skip malformed JSON lines
            }
          }
        }
      } catch (err: any) {
        // reader.read() 抛出的网络错误，走外层 retry 逻辑
        throw err
      }

      // 正常读完 → 成功
      return
    } catch (err: any) {
      clearTimeout(timeoutId)

      // 如果已经收到 done 事件，即使后续有错误也认为成功
      // （这里无法直接从 catch 判断，但 done 事件会 return，所以能到这说明没收到 done）

      if (attempt < MAX_RETRIES && isRetryable(err)) {
        await backoff(attempt)
        continue
      }

      // 不可重试的错误
      callbacks.onError(err.message || 'Stream read error')
      return
    }
  }

  // 所有重试耗尽
  callbacks.onError('连接失败，请检查网络后重试')
}
