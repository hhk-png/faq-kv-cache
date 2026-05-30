import React, { useState, useEffect, useCallback } from 'react'
import { fetchFaqs, createFaq, updateFaq, deleteFaq, batchCreateFaqs, rebuildCache } from '../../services/faq'
import { fetchCacheStatus } from '../../services/cache'
import type { FaqItem, FaqCreateRequest, CacheBlockStatus } from '../../types'

interface FaqFormData {
  category: string
  question: string
  answer: string
  tags: string
}

const emptyForm: FaqFormData = { category: '', question: '', answer: '', tags: '' }

const FaqManage: React.FC = () => {
  const [faqs, setFaqs] = useState<FaqItem[]>([])
  const [loading, setLoading] = useState(true)
  const [searchKeyword, setSearchKeyword] = useState('')
  const [searchCategory, setSearchCategory] = useState('')

  // Modal state
  const [showModal, setShowModal] = useState(false)
  const [editingFaq, setEditingFaq] = useState<FaqItem | null>(null)
  const [formData, setFormData] = useState<FaqFormData>(emptyForm)
  const [saving, setSaving] = useState(false)

  // Delete confirm
  const [deleteId, setDeleteId] = useState<string | null>(null)

  // Batch import
  const [showBatchModal, setShowBatchModal] = useState(false)
  const [batchInput, setBatchInput] = useState('')
  const [batchResult, setBatchResult] = useState<string | null>(null)

  // Cache status
  const [cacheStatus, setCacheStatus] = useState<CacheBlockStatus[]>([])
  const [showCachePanel, setShowCachePanel] = useState(false)

  const loadFaqs = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchFaqs(searchCategory || undefined, searchKeyword || undefined)
      setFaqs(res.data)
    } catch (err: any) {
      console.error('Failed to load FAQs', err)
    } finally {
      setLoading(false)
    }
  }, [searchCategory, searchKeyword])

  useEffect(() => { loadFaqs() }, [loadFaqs])

  const openCreate = () => {
    setEditingFaq(null)
    setFormData(emptyForm)
    setShowModal(true)
  }

  const openEdit = (faq: FaqItem) => {
    setEditingFaq(faq)
    setFormData({
      category: faq.category,
      question: faq.question,
      answer: faq.answer,
      tags: faq.tags.join(', '),
    })
    setShowModal(true)
  }

  const handleSave = async () => {
    if (!formData.category || !formData.question || !formData.answer) {
      alert('请填写分类、问题和答案')
      return
    }
    setSaving(true)
    try {
      const data: FaqCreateRequest = {
        category: formData.category,
        question: formData.question,
        answer: formData.answer,
        tags: formData.tags.split(',').map(t => t.trim()).filter(Boolean),
      }
      if (editingFaq) {
        await updateFaq(editingFaq.id, data)
      } else {
        await createFaq(data)
      }
      setShowModal(false)
      loadFaqs()
    } catch (err: any) {
      alert(err.message || '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!deleteId) return
    try {
      await deleteFaq(deleteId)
      setDeleteId(null)
      loadFaqs()
    } catch (err: any) {
      alert(err.message || '删除失败')
    }
  }

  const handleBatchImport = async () => {
    try {
      const items = JSON.parse(batchInput)
      if (!Array.isArray(items)) throw new Error('JSON必须为数组格式')
      const res = await batchCreateFaqs(items)
      setBatchResult(`成功导入 ${res.total || items.length} 条FAQ`)
      setBatchInput('')
      loadFaqs()
    } catch (err: any) {
      setBatchResult(`导入失败: ${err.message}`)
    }
  }

  const handleRebuildCache = async () => {
    try {
      await rebuildCache()
      alert('已触发缓存重建')
    } catch (err: any) {
      alert(err.message || '触发失败')
    }
  }

  const loadCacheStatus = async () => {
    try {
      const res = await fetchCacheStatus()
      setCacheStatus(res.data)
      setShowCachePanel(!showCachePanel)
    } catch (err: any) {
      alert(err.message || '获取缓存状态失败')
    }
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-dark-text">FAQ管理</h1>
          <p className="text-sm text-dark-text-secondary mt-1">管理FAQ问答条目，支持单条和批量操作</p>
        </div>
        <div className="flex gap-2">
          <button onClick={loadCacheStatus} className="px-4 py-2 text-sm text-dark-text-secondary border border-dark-border rounded-lg hover:border-accent/30 transition-all">
            {showCachePanel ? '隐藏缓存' : '缓存状态'}
          </button>
          <button onClick={handleRebuildCache} className="px-4 py-2 text-sm text-dark-text-secondary border border-dark-border rounded-lg hover:border-accent/30 transition-all">
            重建缓存
          </button>
          <button onClick={() => setShowBatchModal(true)} className="px-4 py-2 text-sm text-dark-text-secondary border border-dark-border rounded-lg hover:border-accent/30 transition-all">
            批量导入
          </button>
          <button onClick={openCreate} className="px-4 py-2 text-sm bg-accent/10 text-accent border border-accent/20 rounded-lg hover:bg-accent/20 transition-all">
            + 新增FAQ
          </button>
        </div>
      </div>

      {/* Cache Status Panel */}
      {showCachePanel && (
        <div className="mb-6 bg-dark-card border border-dark-border rounded-xl p-4">
          <h3 className="text-sm font-medium text-dark-text mb-3">缓存预热状态</h3>
          {cacheStatus.length === 0 ? (
            <p className="text-xs text-dark-text-secondary">暂无缓存数据，请先录入FAQ并触发缓存重建。</p>
          ) : (
            <div className="grid grid-cols-4 gap-2">
              {cacheStatus.map((block) => (
                <div key={block.block_id} className="bg-dark-bg rounded-lg p-3 border border-dark-border">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-mono text-dark-text-secondary truncate">{block.block_id}</span>
                    <span className={`text-xs px-1.5 py-0.5 rounded ${block.status === 'success' ? 'text-success bg-success/10' : 'text-danger bg-danger/10'}`}>
                      {block.status}
                    </span>
                  </div>
                  {block.usage && (
                    <p className="text-xs text-dark-text-secondary">{block.usage.total_tokens} tokens</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-3 mb-4">
        <input
          type="text"
          value={searchKeyword}
          onChange={(e) => setSearchKeyword(e.target.value)}
          placeholder="搜索关键词..."
          className="flex-1 bg-dark-card border border-dark-border rounded-lg px-4 py-2 text-sm text-dark-text outline-none focus:border-accent/50 transition-all placeholder-dark-text-secondary/50"
        />
        <input
          type="text"
          value={searchCategory}
          onChange={(e) => setSearchCategory(e.target.value)}
          placeholder="分类筛选..."
          className="w-40 bg-dark-card border border-dark-border rounded-lg px-4 py-2 text-sm text-dark-text outline-none focus:border-accent/50 transition-all placeholder-dark-text-secondary/50"
        />
      </div>

      {/* FAQ List */}
      {loading ? (
        <div className="space-y-3">
          {[1,2,3].map(i => (
            <div key={i} className="bg-dark-card border border-dark-border rounded-xl p-5">
              <div className="skeleton h-5 w-2/3 mb-3" />
              <div className="skeleton h-4 w-full mb-2" />
              <div className="skeleton h-4 w-1/2" />
            </div>
          ))}
        </div>
      ) : faqs.length === 0 ? (
        <div className="text-center py-20">
          <p className="text-dark-text-secondary text-lg mb-2">暂无FAQ数据</p>
          <p className="text-dark-text-secondary text-sm">点击右上角"新增FAQ"或"批量导入"添加数据</p>
        </div>
      ) : (
        <div className="space-y-3">
          {faqs.map((faq) => (
            <div key={faq.id} className="bg-dark-card border border-dark-border rounded-xl p-5 hover:shadow-card-hover transition-all">
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1 min-w-0">
                  <h3 className="text-dark-text font-medium truncate">{faq.question}</h3>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs bg-accent/10 text-accent px-2 py-0.5 rounded-full">{faq.category}</span>
                    {faq.tags.map(tag => (
                      <span key={tag} className="text-xs bg-dark-border/50 text-dark-text-secondary px-2 py-0.5 rounded-full">{tag}</span>
                    ))}
                  </div>
                </div>
                <div className="flex gap-2 ml-3">
                  <button onClick={() => openEdit(faq)} className="px-3 py-1.5 text-xs text-dark-text-secondary hover:text-accent border border-dark-border hover:border-accent/30 rounded-lg transition-all">编辑</button>
                  <button onClick={() => setDeleteId(faq.id)} className="px-3 py-1.5 text-xs text-dark-text-secondary hover:text-danger border border-dark-border hover:border-danger/30 rounded-lg transition-all">删除</button>
                </div>
              </div>
              <p className="text-sm text-dark-text-secondary line-clamp-2">{faq.answer}</p>
              <p className="mt-2 text-xs text-dark-text-secondary">ID: {faq.id} | {new Date(faq.created_at).toLocaleString('zh-CN')}</p>
            </div>
          ))}
        </div>
      )}

      {/* Create/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="bg-dark-card border border-dark-border rounded-2xl p-6 w-full max-w-lg shadow-2xl">
            <h2 className="text-lg font-semibold text-dark-text mb-4">{editingFaq ? '编辑FAQ' : '新增FAQ'}</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-dark-text-secondary mb-1">分类 *</label>
                <input
                  value={formData.category}
                  onChange={e => setFormData({...formData, category: e.target.value})}
                  className="w-full bg-dark-bg border border-dark-border rounded-lg px-4 py-2.5 text-sm text-dark-text outline-none focus:border-accent/50"
                  placeholder="例如：支付、物流、账户"
                />
              </div>
              <div>
                <label className="block text-sm text-dark-text-secondary mb-1">问题 *</label>
                <input
                  value={formData.question}
                  onChange={e => setFormData({...formData, question: e.target.value})}
                  className="w-full bg-dark-bg border border-dark-border rounded-lg px-4 py-2.5 text-sm text-dark-text outline-none focus:border-accent/50"
                  placeholder="输入标准问题"
                />
              </div>
              <div>
                <label className="block text-sm text-dark-text-secondary mb-1">答案 *</label>
                <textarea
                  value={formData.answer}
                  onChange={e => setFormData({...formData, answer: e.target.value})}
                  rows={4}
                  className="w-full bg-dark-bg border border-dark-border rounded-lg px-4 py-2.5 text-sm text-dark-text outline-none focus:border-accent/50 resize-none"
                  placeholder="输入标准答案"
                />
              </div>
              <div>
                <label className="block text-sm text-dark-text-secondary mb-1">标签（逗号分隔）</label>
                <input
                  value={formData.tags}
                  onChange={e => setFormData({...formData, tags: e.target.value})}
                  className="w-full bg-dark-bg border border-dark-border rounded-lg px-4 py-2.5 text-sm text-dark-text outline-none focus:border-accent/50"
                  placeholder="退款, 售后, 支付"
                />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button onClick={() => setShowModal(false)} className="px-4 py-2 text-sm text-dark-text-secondary border border-dark-border rounded-lg hover:text-dark-text transition-all">取消</button>
              <button onClick={handleSave} disabled={saving} className="px-4 py-2 text-sm bg-accent/10 text-accent border border-accent/20 rounded-lg hover:bg-accent/20 transition-all disabled:opacity-50">
                {saving ? '保存中...' : '保存'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirm */}
      {deleteId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="bg-dark-card border border-dark-border rounded-2xl p-6 w-full max-w-sm shadow-2xl">
            <h2 className="text-lg font-semibold text-dark-text mb-2">确认删除</h2>
            <p className="text-sm text-dark-text-secondary mb-6">确定要删除这条FAQ吗？此操作不可恢复。</p>
            <div className="flex justify-end gap-3">
              <button onClick={() => setDeleteId(null)} className="px-4 py-2 text-sm text-dark-text-secondary border border-dark-border rounded-lg hover:text-dark-text transition-all">取消</button>
              <button onClick={handleDelete} className="px-4 py-2 text-sm bg-danger/10 text-danger border border-danger/20 rounded-lg hover:bg-danger/20 transition-all">删除</button>
            </div>
          </div>
        </div>
      )}

      {/* Batch Import Modal */}
      {showBatchModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="bg-dark-card border border-dark-border rounded-2xl p-6 w-full max-w-xl shadow-2xl">
            <h2 className="text-lg font-semibold text-dark-text mb-4">批量导入FAQ</h2>
            <p className="text-sm text-dark-text-secondary mb-3">请输入JSON数组格式的FAQ数据：</p>
            <textarea
              value={batchInput}
              onChange={e => setBatchInput(e.target.value)}
              rows={8}
              className="w-full bg-dark-bg border border-dark-border rounded-lg px-4 py-2.5 text-sm text-dark-text outline-none focus:border-accent/50 resize-none font-mono"
              placeholder='[{"category": "支付", "question": "如何退款？", "answer": "在订单页面操作", "tags": ["退款"]}]'
            />
            {batchResult && (
              <p className={`mt-2 text-sm ${batchResult.includes('失败') ? 'text-danger' : 'text-success'}`}>
                {batchResult}
              </p>
            )}
            <div className="flex justify-end gap-3 mt-4">
              <button onClick={() => { setShowBatchModal(false); setBatchResult(null) }} className="px-4 py-2 text-sm text-dark-text-secondary border border-dark-border rounded-lg hover:text-dark-text transition-all">关闭</button>
              <button onClick={handleBatchImport} className="px-4 py-2 text-sm bg-accent/10 text-accent border border-accent/20 rounded-lg hover:bg-accent/20 transition-all">导入</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default FaqManage
