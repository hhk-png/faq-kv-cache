import React from 'react'
import type { DocumentItem } from '../types'

interface DocumentCardProps {
  doc: DocumentItem
  onPreview: (doc: DocumentItem) => void
  onDelete: (id: string) => void
}

const statusConfig: Record<string, { label: string; color: string }> = {
  processing: { label: '提取中', color: 'text-yellow-400 bg-yellow-500/10' },
  ready: { label: '就绪', color: 'text-success bg-success/10' },
  error: { label: '失败', color: 'text-danger bg-danger/10' },
}

const fileTypeIcons: Record<string, string> = {
  pdf: '📕',
  docx: '📘',
  txt: '📄',
  md: '📝',
}

const DocumentCard: React.FC<DocumentCardProps> = ({ doc, onPreview, onDelete }) => {
  const status = statusConfig[doc.status] || statusConfig.error
  const icon = fileTypeIcons[doc.file_type] || '📄'

  return (
    <div className="bg-dark-card border border-dark-border rounded-xl p-5 hover:shadow-card-hover transition-all">
      <div className="flex items-start gap-4">
        {/* File icon */}
        <div className="text-3xl flex-shrink-0">{icon}</div>

        <div className="flex-1 min-w-0">
          {/* Title & Status */}
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-dark-text font-medium truncate">{doc.title}</h3>
            <span className={`text-xs px-2 py-0.5 rounded-full flex-shrink-0 ${status.color}`}>
              {status.label}
            </span>
          </div>

          {/* File info */}
          <p className="text-sm text-dark-text-secondary truncate">{doc.filename}</p>

          <div className="flex items-center gap-3 mt-2 text-xs text-dark-text-secondary">
            <span>类型: {doc.file_type.toUpperCase()}</span>
            {doc.char_count > 0 && <span>字符: {doc.char_count.toLocaleString()}</span>}
            <span>{new Date(doc.created_at).toLocaleDateString('zh-CN')}</span>
          </div>

          {/* Actions */}
          <div className="flex gap-2 mt-3">
            <button
              onClick={() => onPreview(doc)}
              className="px-3 py-1.5 text-xs text-dark-text-secondary hover:text-accent border border-dark-border hover:border-accent/30 rounded-lg transition-all"
            >
              预览
            </button>
            <button
              onClick={() => onDelete(doc.id)}
              className="px-3 py-1.5 text-xs text-dark-text-secondary hover:text-danger border border-dark-border hover:border-danger/30 rounded-lg transition-all"
            >
              删除
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default DocumentCard
