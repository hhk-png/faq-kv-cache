import React, { useState, useEffect } from 'react'
import { fetchDocuments } from '../services/document'
import type { DocumentItem } from '../types'

interface PriorKnowledgeSelectorProps {
  mode: 'none' | 'document' | 'text'
  onModeChange: (mode: 'none' | 'document' | 'text') => void
  selectedDocId: string | null
  onDocSelect: (id: string | null) => void
  customText: string
  onTextChange: (text: string) => void
}

const PriorKnowledgeSelector: React.FC<PriorKnowledgeSelectorProps> = ({
  mode,
  onModeChange,
  selectedDocId,
  onDocSelect,
  customText,
  onTextChange,
}) => {
  const [documents, setDocuments] = useState<DocumentItem[]>([])

  useEffect(() => {
    if (mode === 'document') {
      fetchDocuments().then((res) => {
        setDocuments(res.data.filter((d) => d.status === 'ready'))
      }).catch(() => {})
    }
  }, [mode])

  return (
    <div className="bg-dark-card border border-dark-border rounded-xl p-4">
      {/* Mode selector */}
      <div className="flex gap-2 mb-3">
        {[
          { value: 'none' as const, label: '不使用' },
          { value: 'document' as const, label: '选择文档' },
          { value: 'text' as const, label: '手动输入' },
        ].map((opt) => (
          <button
            key={opt.value}
            onClick={() => onModeChange(opt.value)}
            className={`px-3 py-1.5 text-xs rounded-lg transition-all ${
              mode === opt.value
                ? 'bg-accent/10 text-accent border border-accent/20'
                : 'text-dark-text-secondary border border-dark-border hover:text-dark-text'
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* Document selector */}
      {mode === 'document' && (
        <div>
          {documents.length === 0 ? (
            <p className="text-xs text-dark-text-secondary">没有可用的文档，请先上传并等待处理完成。</p>
          ) : (
            <select
              value={selectedDocId || ''}
              onChange={(e) => onDocSelect(e.target.value || null)}
              className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-sm text-dark-text outline-none focus:border-accent/50 transition-all"
            >
              <option value="">请选择文档...</option>
              {documents.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.title} ({doc.char_count.toLocaleString()} 字符)
                </option>
              ))}
            </select>
          )}
        </div>
      )}

      {/* Manual text input */}
      {mode === 'text' && (
        <textarea
          value={customText}
          onChange={(e) => onTextChange(e.target.value)}
          placeholder="请输入先验知识内容..."
          rows={3}
          className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-sm text-dark-text outline-none focus:border-accent/50 transition-all resize-none placeholder-dark-text-secondary/50"
        />
      )}
    </div>
  )
}

export default PriorKnowledgeSelector
