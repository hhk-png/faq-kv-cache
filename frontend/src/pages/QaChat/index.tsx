import React, { useState, useRef, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import ChatMessage from '../../components/ChatMessage'
import PriorKnowledgeSelector from '../../components/PriorKnowledgeSelector'
import { askQuestionStream } from '../../services/qa'
import { fetchSession, createSession } from '../../services/session'
import type { FaqReference } from '../../types'

interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  references?: FaqReference[]
  isStatus?: boolean
}

let msgId = 0
const nextId = () => `msg_${++msgId}`

/* ────────── InputArea ────────── */
const InputArea: React.FC<{
  loading: boolean
  onSend: (text: string) => void
}> = ({ loading, onSend }) => {
  const [text, setText] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  const submit = () => {
    const q = text.trim()
    if (!q || loading) return
    onSend(q)
    setText('')
  }

  return (
    <div className="flex gap-3">
      <input
        ref={inputRef}
        value={text}
        onChange={e => setText(e.target.value)}
        onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() } }}
        placeholder="输入您的问题..."
        disabled={loading}
        className="flex-1 bg-dark-card border border-dark-border rounded-xl px-4 py-3 text-sm text-dark-text outline-none focus:border-accent/50 transition-all placeholder-dark-text-secondary/50 disabled:opacity-50"
      />
      <button
        onClick={submit}
        disabled={loading || !text.trim()}
        className="px-6 py-3 bg-accent/10 text-accent border border-accent/20 rounded-xl hover:bg-accent/20 transition-all text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? '处理中...' : '发送'}
      </button>
    </div>
  )
}

/* ────────── MessageList ────────── */
const MessageList: React.FC<{
  messages: Message[]
  streamingMsgId: string | null
}> = React.memo(({ messages, streamingMsgId }) => {
  const endRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const initialScrolled = useRef(false)

  // 初始加载 / 切换对话时直接到底，后续流式更新只在底部时自动跟
  useEffect(() => {
    // 消息从有到无 → 切换对话了，重置标记
    if (messages.length === 0) {
      initialScrolled.current = false
      return
    }
    // 首次加载 → 直接滚到底，无动画
    if (!initialScrolled.current) {
      initialScrolled.current = true
      endRef.current?.scrollIntoView({ behavior: 'auto' })
      return
    }
    // 后续更新：只有用户在底部时才自动跟
    const container = containerRef.current?.parentElement
    if (!container) return
    const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 150
    if (isNearBottom) {
      endRef.current?.scrollIntoView({ behavior: 'auto' })
    }
  }, [messages])

  if (messages.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center px-4">
        <div className="text-5xl mb-4">💬</div>
        <p className="text-dark-text-secondary text-lg mb-2">开始提问</p>
        <p className="text-dark-text-secondary text-sm max-w-md">
          在下方输入您的问题，系统将自动搜索FAQ库并为您提供智能回答。
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-1" ref={containerRef}>
      {messages.map(msg => (
        <ChatMessage
          key={msg.id}
          role={msg.role}
          content={msg.content}
          references={msg.references}
          loading={msg.id === streamingMsgId && msg.content === ''}
        />
      ))}
      <div ref={endRef} />
    </div>
  )
})

const QaChat: React.FC = () => {
  const { sessionId: urlSessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()
  const [sessionId, setSessionId] = useState<string>(urlSessionId || '')
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [streamingMsgId, setStreamingMsgId] = useState<string | null>(null)
  const [initialLoading, setInitialLoading] = useState(true)
  const justCreatedRef = useRef(false)

  // Prior knowledge state
  const [pkMode, setPkMode] = useState<'none' | 'document' | 'text'>('none')
  const [pkDocId, setPkDocId] = useState<string | null>(null)
  const [pkText, setPkText] = useState('')

  // Load session messages on mount / session change
  useEffect(() => {
    // Skip loading if we just created this session (handleSubmit handles it)
    if (justCreatedRef.current) {
      justCreatedRef.current = false
      setInitialLoading(false)
      return
    }

    const loadSession = async () => {
      const sid = urlSessionId
      if (!sid) {
        // No session in URL → just show empty state
        setSessionId('')
        setMessages([])
        setInitialLoading(false)
        return
      }

      setSessionId(sid)
      setMessages([])  // 先清空旧消息，把DOM卸载和挂载拆成两次渲染
      try {
        const res = await fetchSession(sid)
        const loadedMessages: Message[] = (res.data.messages || []).map(
          (m: { role: string; content: string }) => ({
            id: nextId(),
            role: m.role as 'user' | 'assistant',
            content: m.content,
          }),
        )
        setMessages(loadedMessages)
      } catch {
        // Session not found → show empty state
        setSessionId('')
        setMessages([])
      }
      setInitialLoading(false)
    }
    loadSession()
  }, [urlSessionId, navigate])

  const handleSubmit = useCallback(async (question: string) => {
    if (!question || loading) return

    // Create session if not exists
    let sid = sessionId
    if (!sid) {
      try {
        const res = await createSession()
        sid = res.data.id
        setSessionId(sid)
        justCreatedRef.current = true
        window.dispatchEvent(new CustomEvent('session-changed'))
        navigate(`/qa/${sid}`, { replace: true })
      } catch {
        return
      }
    }

    // Add user message to local state
    const userMsg: Message = { id: nextId(), role: 'user', content: question }
    const assistMsg: Message = { id: nextId(), role: 'assistant', content: '' }
    setMessages(prev => [...prev, userMsg, assistMsg])
    setStreamingMsgId(assistMsg.id)
    setLoading(true)

    await askQuestionStream(
      {
        question,
        prior_knowledge_type: pkMode === 'none' ? null : pkMode,
        prior_knowledge_content: pkMode === 'text' ? pkText : undefined,
        document_id: pkMode === 'document' ? (pkDocId ?? undefined) : undefined,
      },
      sid,
      {
        onStatus: (statusText) => {
          // Show search process as status message
          const statusId = `status_${assistMsg.id}`
          setMessages(prev => {
            const exists = prev.find(m => m.id === statusId)
            if (exists) {
              return prev.map(m => m.id === statusId ? { ...m, content: statusText } : m)
            }
            const idx = prev.findIndex(m => m.id === assistMsg.id)
            const statusMsg: Message = { id: statusId, role: 'system' as const, content: statusText, isStatus: true }
            const copy = [...prev]
            copy.splice(idx, 0, statusMsg)
            return copy
          })
        },
        onToken: (token) => {
          setMessages(prev =>
            prev.map(m =>
              m.id === assistMsg.id ? { ...m, content: m.content + token } : m,
            ),
          )
        },
        onDone: (references) => {
          setMessages(prev =>
            prev.map(m =>
              m.id === assistMsg.id ? { ...m, references } : m,
            ),
          )
          setStreamingMsgId(null)
          setLoading(false)
        },
        onError: (error) => {
          setMessages(prev =>
            prev.map(m =>
              m.id === assistMsg.id
                ? { ...m, content: `请求失败: ${error}` }
                : m,
            ),
          )
          setStreamingMsgId(null)
          setLoading(false)
        },
      },
    )
  }, [loading, sessionId, pkMode, pkText, pkDocId, navigate])

  if (initialLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-dark-text-secondary">加载中...</div>
      </div>
    )
  }

  return (
    <div className="flex h-full">
      {/* Chat Area */}
      <div className="flex-1 flex flex-col">
        <div className="px-6 py-4 border-b border-dark-border">
          <h1 className="text-xl font-semibold text-dark-text">FAQ智能问答</h1>
          <p className="text-sm text-dark-text-secondary mt-1">
            基于FAQ库的智能搜索问答系统
          </p>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-auto py-4">
          <MessageList messages={messages} streamingMsgId={streamingMsgId} />
        </div>

        {/* Input Area */}
        <div className="px-6 py-4 border-t border-dark-border">
          <InputArea loading={loading} onSend={handleSubmit} />
        </div>
      </div>

      {/* Side Panel */}
      <div className="w-72 border-l border-dark-border p-4 overflow-auto">
        <h2 className="text-sm font-medium text-dark-text mb-4">先验知识</h2>
        <PriorKnowledgeSelector
          mode={pkMode}
          onModeChange={setPkMode}
          selectedDocId={pkDocId}
          onDocSelect={setPkDocId}
          customText={pkText}
          onTextChange={setPkText}
        />
        <div className="mt-4">
          <p className="text-xs text-dark-text-secondary leading-relaxed">
            先验知识会在问答时注入到系统提示词中，帮助模型优先遵循您提供的信息。
          </p>
        </div>
      </div>
    </div>
  )
}

export default QaChat
