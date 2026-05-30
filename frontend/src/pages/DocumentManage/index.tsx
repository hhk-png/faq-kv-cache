import React, { useState, useEffect, useCallback } from 'react'
import { fetchDocuments, uploadDocument, fetchDocumentContent, deleteDocument, updateDocumentTitle } from '../../services/document'
import type { DocumentItem } from '../../types'

const DocumentManage: React.FC = () => {
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)

  // Preview
  const [previewDoc, setPreviewDoc] = useState<DocumentItem | null>(null)
  const [previewContent, setPreviewContent] = useState('')
  const [previewLoading, setPreviewLoading] = useState(false)

  // Delete
  const [deleteId, setDeleteId] = useState<string | null>(null)

  // Edit title
  const [editDocId, setEditDocId] = useState<string | null>(null)
  const [editTitle, setEditTitle] = useState('')

  const loadDocs = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchDocuments()
      setDocuments(res.data)
    } catch (err: any) {
      console.error('Failed to load documents', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadDocs() }, [loadDocs])

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      await uploadDocument(file)
      loadDocs()
    } catch (err: any) {
      alert(err.message || '上传失败')
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  const handlePreview = async (doc: DocumentItem) => {
    setPreviewDoc(doc)
    setPreviewLoading(true)
    try {
      const res = await fetchDocumentContent(doc.id)
      setPreviewContent(res.data.content || '（无提取内容）')
    } catch (err: any) {
      setPreviewContent('加载失败: ' + (err.message || '未知错误'))
    } finally {
      setPreviewLoading(false)
    }
  }

  const handleDelete = async () => {
    if (!deleteId) return
    try {
      await deleteDocument(deleteId)
      setDeleteId(null)
      loadDocs()
    } catch (err: any) {
      alert(err.message || '删除失败')
    }
  }

  const handleTitleEdit = async (docId: string) => {
    if (!editTitle.trim()) return
    try {
      await updateDocumentTitle(docId, editTitle)
      setEditDocId(null)
      loadDocs()
    } catch (err: any) {
      alert(err.message || '修改失败')
    }
  }

  const statusBadge = (status: string) => {
    const config: Record<string, string> = {
      processing: 'text-yellow-400 bg-yellow-500/10',
      ready: 'text-success bg-success/10',
      error: 'text-danger bg-danger/10',
    }
    const labels: Record<string, string> = {
      processing: '提取中',
      ready: '就绪',
      error: '失败',
    }
    return (
      <span className={`text-xs px-2 py-0.5 rounded-full ${config[status] || ''}`}>
        {labels[status] || status}
      </span>
    )
  }

  const fileIcon = (type: string) => {
    const icons: Record<string, string> = { pdf: '📕', docx: '📘', txt: '📄', md: '📝' }
    return icons[type] || '📄'
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-dark-text">文档管理</h1>
          <p className="text-sm text-dark-text-secondary mt-1">上传文档并自动提取文本，用于问答时的先验知识</p>
        </div>
        <div className="relative">
          <input
            type="file"
            accept=".pdf,.docx,.txt,.md"
            onChange={handleUpload}
            disabled={uploading}
            className="hidden"
            id="file-upload"
          />
          <label
            htmlFor="file-upload"
            className={`inline-block px-4 py-2 text-sm bg-accent/10 text-accent border border-accent/20 rounded-lg hover:bg-accent/20 transition-all cursor-pointer ${uploading ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            {uploading ? '上传中...' : '+ 上传文档'}
          </label>
        </div>
      </div>

      {/* Supported formats */}
      <div className="mb-4 flex gap-3 text-xs text-dark-text-secondary">
        <span>支持格式：</span>
        <span>📕 PDF</span>
        <span>📘 DOCX</span>
        <span>📄 TXT</span>
        <span>📝 MD</span>
      </div>

      {/* Document Grid */}
      {loading ? (
        <div className="grid grid-cols-2 gap-4">
          {[1,2,3,4].map(i => (
            <div key={i} className="bg-dark-card border border-dark-border rounded-xl p-5">
              <div className="skeleton h-12 w-12 rounded-lg mb-3" />
              <div className="skeleton h-5 w-2/3 mb-2" />
              <div className="skeleton h-4 w-1/2 mb-2" />
              <div className="skeleton h-4 w-1/3" />
            </div>
          ))}
        </div>
      ) : documents.length === 0 ? (
        <div className="text-center py-20">
          <p className="text-dark-text-secondary text-lg mb-2">暂无文档</p>
          <p className="text-dark-text-secondary text-sm">点击右上角"上传文档"按钮上传文件</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          {documents.map((doc) => (
            <div key={doc.id} className="bg-dark-card border border-dark-border rounded-xl p-5 hover:shadow-card-hover transition-all">
              <div className="flex items-start gap-4">
                <div className="text-3xl flex-shrink-0">{fileIcon(doc.file_type)}</div>
                <div className="flex-1 min-w-0">
                  {editDocId === doc.id ? (
                    <div className="flex gap-2 mb-1">
                      <input
                        value={editTitle}
                        onChange={e => setEditTitle(e.target.value)}
                        className="flex-1 bg-dark-bg border border-dark-border rounded px-2 py-1 text-sm text-dark-text outline-none"
                        autoFocus
                        onKeyDown={e => e.key === 'Enter' && handleTitleEdit(doc.id)}
                      />
                      <button onClick={() => handleTitleEdit(doc.id)} className="text-xs text-accent">保存</button>
                      <button onClick={() => setEditDocId(null)} className="text-xs text-dark-text-secondary">取消</button>
                    </div>
                  ) : (
                    <h3
                      className="text-dark-text font-medium truncate cursor-pointer hover:text-accent transition-colors"
                      onClick={() => { setEditDocId(doc.id); setEditTitle(doc.title) }}
                      title="点击修改标题"
                    >
                      {doc.title}
                    </h3>
                  )}
                  <p className="text-sm text-dark-text-secondary truncate">{doc.filename}</p>
                  <div className="flex items-center gap-2 mt-2">
                    {statusBadge(doc.status)}
                    <span className="text-xs text-dark-text-secondary">{doc.file_type.toUpperCase()}</span>
                    {doc.char_count > 0 && (
                      <span className="text-xs text-dark-text-secondary">{doc.char_count.toLocaleString()} 字符</span>
                    )}
                  </div>
                  <div className="flex gap-2 mt-3">
                    <button onClick={() => handlePreview(doc)} className="px-3 py-1.5 text-xs text-dark-text-secondary hover:text-accent border border-dark-border hover:border-accent/30 rounded-lg transition-all">预览</button>
                    <button onClick={() => setDeleteId(doc.id)} className="px-3 py-1.5 text-xs text-dark-text-secondary hover:text-danger border border-dark-border hover:border-danger/30 rounded-lg transition-all">删除</button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Preview Modal */}
      {previewDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="bg-dark-card border border-dark-border rounded-2xl w-full max-w-2xl max-h-[80vh] flex flex-col shadow-2xl">
            <div className="flex items-center justify-between p-4 border-b border-dark-border">
              <div>
                <h2 className="text-base font-medium text-dark-text">{previewDoc.title}</h2>
                <p className="text-xs text-dark-text-secondary">{previewDoc.filename}</p>
              </div>
              <button onClick={() => { setPreviewDoc(null); setPreviewContent('') }} className="text-dark-text-secondary hover:text-dark-text text-xl leading-none">&times;</button>
            </div>
            <div className="flex-1 overflow-auto p-4">
              {previewLoading ? (
                <div className="space-y-2">
                  <div className="skeleton h-4 w-full" />
                  <div className="skeleton h-4 w-5/6" />
                  <div className="skeleton h-4 w-4/6" />
                </div>
              ) : (
                <pre className="text-sm text-dark-text whitespace-pre-wrap font-sans leading-relaxed">{previewContent}</pre>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirm */}
      {deleteId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="bg-dark-card border border-dark-border rounded-2xl p-6 w-full max-w-sm shadow-2xl">
            <h2 className="text-lg font-semibold text-dark-text mb-2">确认删除</h2>
            <p className="text-sm text-dark-text-secondary mb-6">确定要删除这个文档及其提取的文本吗？此操作不可恢复。</p>
            <div className="flex justify-end gap-3">
              <button onClick={() => setDeleteId(null)} className="px-4 py-2 text-sm text-dark-text-secondary border border-dark-border rounded-lg hover:text-dark-text transition-all">取消</button>
              <button onClick={handleDelete} className="px-4 py-2 text-sm bg-danger/10 text-danger border border-danger/20 rounded-lg hover:bg-danger/20 transition-all">删除</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default DocumentManage
