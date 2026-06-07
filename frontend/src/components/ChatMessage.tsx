import React from 'react'
import type { FaqReference } from '../types'

interface ChatMessageProps {
  role: 'user' | 'assistant' | 'system'
  content: string
  references?: FaqReference[]
  loading?: boolean
}

const ChatMessage: React.FC<ChatMessageProps> = React.memo(({ role, content, references, loading }) => {
  if (loading) {
    return (
      <div className="flex gap-3 px-4 py-3">
        <div className="w-8 h-8 rounded-lg bg-accent/20 flex items-center justify-center text-sm flex-shrink-0">
          🤖
        </div>
        <div className="flex-1 space-y-2">
          <div className="skeleton h-4 w-3/4" />
          <div className="skeleton h-4 w-1/2" />
          <div className="skeleton h-4 w-2/3" />
        </div>
      </div>
    )
  }

  const isUser = role === 'user'
  const isSystem = role === 'system'

  return (
    <div className={`flex gap-3 px-4 py-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm flex-shrink-0 ${
          isUser
            ? 'bg-accent/20 text-accent'
            : isSystem
            ? 'bg-yellow-500/20 text-yellow-400'
            : 'bg-success/20 text-success'
        }`}
      >
        {isUser ? '👤' : isSystem ? '⚙️' : '🤖'}
      </div>

      {/* Bubble */}
      <div className={`max-w-[75%] ${isUser ? 'items-end' : 'items-start'}`}>
        <div
          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
            isUser
              ? 'bg-accent/10 text-dark-text border border-accent/20'
              : isSystem
              ? 'bg-yellow-500/5 text-yellow-300/80 border border-yellow-500/10'
              : 'bg-dark-card text-dark-text border border-dark-border'
          }`}
        >
          <p className="whitespace-pre-wrap">{content}</p>
        </div>

        {/* References */}
        {references && references.length > 0 && (
          <div className="mt-2 space-y-1">
            <p className="text-xs text-dark-text-secondary">📎 引用来源：</p>
            {references.map((ref, i) => (
              <div
                key={i}
                className="text-xs bg-accent/5 border border-accent/10 rounded-lg px-3 py-1.5 text-dark-text-secondary"
              >
                <span className="text-accent">[{ref.id}]</span>{' '}
                {ref.question}
                <span className="text-dark-text-secondary ml-1">({ref.category})</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
})

export default ChatMessage
