import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import type { FaqReference } from '../types'

interface ChatMessageProps {
  role: 'user' | 'assistant' | 'system'
  content: string
  references?: FaqReference[]
  loading?: boolean
}

/** 判断字符串是否包含 markdown 标记 */
function containsMarkdown(text: string): boolean {
  // 标题、粗体、斜体、代码块、行内代码、列表、引用、表格
  return /(#{1,6}\s|(\*\*|__).*?\*\*|__|`{1,3}|^\s*[-*+]\s|^\s*\d+\.\s|^>\s|^\s*\|.+?\|)/m.test(text)
}

const MarkdownContent: React.FC<{ content: string }> = ({ content }) => {
  return (
    <div className="prose prose-invert prose-sm max-w-none prose-headings:text-dark-text prose-a:text-accent prose-code:bg-dark-bg prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-pre:bg-transparent prose-pre:p-0">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw]}
        components={{
          code({ className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || '')
            const codeStr = String(children).replace(/\n$/, '')
            if (match) {
              return (
                <SyntaxHighlighter
                  style={oneDark}
                  language={match[1]}
                  PreTag="div"
                  customStyle={{ margin: 0, borderRadius: 8, fontSize: 13 }}
                >
                  {codeStr}
                </SyntaxHighlighter>
              )
            }
            // 行内代码
            return (
              <code className={className} {...props}>
                {children}
              </code>
            )
          },
          table({ children }) {
            return (
              <div className="overflow-auto my-2">
                <table className="min-w-full border-collapse border border-dark-border text-sm">
                  {children}
                </table>
              </div>
            )
          },
          th({ children }) {
            return (
              <th className="border border-dark-border bg-dark-card px-3 py-2 text-left font-medium">
                {children}
              </th>
            )
          },
          td({ children }) {
            return (
              <td className="border border-dark-border px-3 py-2">{children}</td>
            )
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
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
          {isUser ? (
            // 用户消息保持纯文本
            <p className="whitespace-pre-wrap">{content}</p>
          ) : containsMarkdown(content) ? (
            // AI / 系统消息 — 渲染 markdown
            <MarkdownContent content={content} />
          ) : (
            // 没有 markdown 标记时仍用纯文本，避免不必要的渲染开销
            <p className="whitespace-pre-wrap">{content}</p>
          )}
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
