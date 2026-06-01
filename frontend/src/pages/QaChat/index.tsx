import React, { useState, useRef, useEffect, useCallback } from 'react'
import ChatMessage from '../../components/ChatMessage'
import PriorKnowledgeSelector from '../../components/PriorKnowledgeSelector'
import { askQuestionStream } from '../../services/qa'
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

const QaChat: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [streamingMsgId, setStreamingMsgId] = useState<string | null>(null)
  const [statusMsgId, setStatusMsgId] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Prior knowledge state
  const [pkMode, setPkMode] = useState<'none' | 'document' | 'text'>('none')
  const [pkDocId, setPkDocId] = useState<string | null>(null)
  const [pkText, setPkText] = useState('')

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSubmit = useCallback(async () => {
    const question = input.trim()
    if (!question || loading) return

    setInput('')

    // Build conversation history for the API
    const convHistory = messages
      .filter(m => m.role === 'user' || m.role === 'assistant')
      .map(m => ({ role: m.role as 'user' | 'assistant', content: m.content }))

    // Add user message to local state
    const userMsg: Message = { id: nextId(), role: 'user', content: question }
    const assistMsg: Message = { id: nextId(), role: 'assistant', content: '' }

    setMessages(prev => [...prev, userMsg, assistMsg])
    setStreamingMsgId(assistMsg.id)
    setLoading(true)

    await askQuestionStream(
      {
        messages: [...convHistory, { role: 'user', content: question }],
        prior_knowledge_type: pkMode === 'none' ? null : pkMode,
        prior_knowledge_content: pkMode === 'text' ? pkText : undefined,
        document_id: pkMode === 'document' ? pkDocId : undefined,
      },
      {
        onStatus: (statusText) => {
          // Show search process status in a system message
          const statusId = `status_${assistMsg.id}`
          setStatusMsgId(statusId)
          setMessages(prev => {
            const exists = prev.find(m => m.id === statusId)
            if (exists) {
              return prev.map(m => m.id === statusId ? { ...m, content: statusText } : m)
            }
            // Insert status before the assistant message
            const idx = prev.findIndex(m => m.id === assistMsg.id)
            const statusMsg: Message = { id: statusId, role: 'system', content: statusText, isStatus: true }
            const copy = [...prev]
            copy.splice(idx, 0, statusMsg)
            return copy
          })
        },
        onSearchDecision: (search) => {
          // Optionally show whether we're searching
        },
        onToken: (token) => {
          setMessages(prev => {
            // Remove status messages related to this turn
            const filtered = prev.filter(m => !(m.isStatus && m.id.includes(assistMsg.id)))
            setStatusMsgId(null)
            return filtered.map(m =>
              m.id === assistMsg.id ? { ...m, content: m.content + token } : m,
            )
          })
        },
        onDone: (references) => {
          setMessages(prev =>
            prev.map(m =>
              m.id === assistMsg.id ? { ...m, references } : m,
            ),
          )
          setStreamingMsgId(null)
          setLoading(false)
          inputRef.current?.focus()
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
  }, [input, loading, pkMode, pkText, pkDocId, messages])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const clearChat = () => {
    setMessages([])
    setStreamingMsgId(null)
    setStatusMsgId(null)
  }

  return (
    <div className="flex h-full">
      {/* Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-dark-border flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-dark-text">FAQ智能问答</h1>
            <p className="text-sm text-dark-text-secondary mt-1">
              基于FAQ库的智能搜索问答系统
            </p>
          </div>
          {messages.length > 0 && (
            <button
              onClick={clearChat}
              className="px-3 py-1.5 text-xs text-dark-text-secondary border border-dark-border rounded-lg hover:text-dark-text transition-all"
            >
              清空对话
            </button>
          )}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-auto py-4">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center px-4">
              <div className="text-5xl mb-4">💬</div>
              <p className="text-dark-text-secondary text-lg mb-2">开始提问</p>
              <p className="text-dark-text-secondary text-sm max-w-md">
                在下方输入您的问题，系统将自动判断是否需要搜索FAQ库，并为您提供智能回答。
              </p>
            </div>
          ) : (
            <div className="space-y-1">
              {messages.map(msg => (
                <ChatMessage
                  key={msg.id}
                  role={msg.role}
                  content={msg.content}
                  references={msg.references}
                  loading={msg.id === streamingMsgId && msg.content === ''}
                />
              ))}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="px-6 py-4 border-t border-dark-border">
          <div className="flex gap-3">
            <input
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入您的问题..."
              disabled={loading}
              className="flex-1 bg-dark-card border border-dark-border rounded-xl px-4 py-3 text-sm text-dark-text outline-none focus:border-accent/50 transition-all placeholder-dark-text-secondary/50 disabled:opacity-50"
            />
            <button
              onClick={handleSubmit}
              disabled={loading || !input.trim()}
              className="px-6 py-3 bg-accent/10 text-accent border border-accent/20 rounded-xl hover:bg-accent/20 transition-all text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? '处理中...' : '发送'}
            </button>
          </div>
        </div>
      </div>

      {/* Side Panel - Prior Knowledge */}
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
