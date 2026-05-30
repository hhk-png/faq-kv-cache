import React from 'react'
import type { FaqItem } from '../types'

interface FaqCardProps {
  faq: FaqItem
  onEdit: (faq: FaqItem) => void
  onDelete: (id: string) => void
}

const FaqCard: React.FC<FaqCardProps> = ({ faq, onEdit, onDelete }) => {
  return (
    <div className="bg-dark-card border border-dark-border rounded-xl p-5 hover:shadow-card-hover transition-all">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="text-dark-text font-medium text-base truncate">
            {faq.question}
          </h3>
          <div className="flex items-center gap-2 mt-1.5">
            <span className="text-xs bg-accent/10 text-accent px-2 py-0.5 rounded-full">
              {faq.category}
            </span>
            {faq.tags.map((tag) => (
              <span
                key={tag}
                className="text-xs bg-dark-border/50 text-dark-text-secondary px-2 py-0.5 rounded-full"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>
        {/* Actions */}
        <div className="flex gap-2 ml-3 flex-shrink-0">
          <button
            onClick={() => onEdit(faq)}
            className="px-3 py-1.5 text-xs text-dark-text-secondary hover:text-accent border border-dark-border hover:border-accent/30 rounded-lg transition-all"
          >
            编辑
          </button>
          <button
            onClick={() => onDelete(faq.id)}
            className="px-3 py-1.5 text-xs text-dark-text-secondary hover:text-danger border border-dark-border hover:border-danger/30 rounded-lg transition-all"
          >
            删除
          </button>
        </div>
      </div>

      {/* Answer preview */}
      <p className="text-sm text-dark-text-secondary line-clamp-2 leading-relaxed">
        {faq.answer}
      </p>

      {/* Footer */}
      <div className="mt-3 flex items-center justify-between text-xs text-dark-text-secondary">
        <span>ID: {faq.id}</span>
        <span>{new Date(faq.created_at).toLocaleDateString('zh-CN')}</span>
      </div>
    </div>
  )
}

export default FaqCard
