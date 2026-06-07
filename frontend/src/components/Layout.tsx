import React, { useState, useEffect } from 'react'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { fetchSessions, createSession, deleteSession, updateSessionTitle, type SessionInfo } from '../services/session'

const navItems = [
  { path: '/qa', label: '问答', icon: '💬' },
  { path: '/faq', label: 'FAQ管理', icon: '📋' },
  { path: '/documents', label: '文档管理', icon: '📄' },
]

const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [sessions, setSessions] = useState<SessionInfo[]>([])
  const [showSessions, setShowSessions] = useState(true)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editTitle, setEditTitle] = useState('')
  const location = useLocation()
  const navigate = useNavigate()

  // Load sessions on mount, and refresh on custom 'session-changed' event
  useEffect(() => {
    const load = () => fetchSessions().then(res => setSessions(res.data)).catch(() => {})
    load()
    window.addEventListener('session-changed', load)
    return () => window.removeEventListener('session-changed', load)
  }, [])

  // Auto-switch sidebar tab based on route
  useEffect(() => {
    if (location.pathname.startsWith('/qa')) {
      setShowSessions(true)
    } else {
      setShowSessions(false)
    }
  }, [location.pathname])

  const handleNewSession = async () => {
    try {
      const res = await createSession()
      setSessions(prev => [res.data, ...prev])
      navigate(`/qa/${res.data.id}`)
    } catch { /* ignore */ }
  }

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      await deleteSession(id)
      setSessions(prev => prev.filter(s => s.id !== id))
      if (location.pathname.includes(id)) {
        navigate('/qa')
      }
    } catch { /* ignore */ }
  }

  const handleRename = async (id: string) => {
    if (!editTitle.trim()) return
    try {
      await updateSessionTitle(id, editTitle)
      setSessions(prev => prev.map(s => s.id === id ? { ...s, title: editTitle } : s))
      setEditingId(null)
    } catch { /* ignore */ }
  }

  const handleLogout = () => {
    localStorage.removeItem('faq_user_id')
    window.location.reload()
  }

  const currentSessionId = location.pathname.startsWith('/qa/') ? location.pathname.split('/qa/')[1] : null

  return (
    <div className="flex h-screen bg-dark-bg">
      {/* Sidebar */}
      <aside className="w-60 bg-dark-card border-r border-dark-border flex flex-col flex-shrink-0">
        {/* Logo */}
        <div className="h-14 flex items-center px-4 border-b border-dark-border">
          <h1 className="text-base font-semibold text-dark-text">
            <span className="text-accent">FAQ</span> Agent
          </h1>
        </div>

        {/* Tabs: Navigation / Sessions */}
        <div className="flex border-b border-dark-border">
          <button
            onClick={() => setShowSessions(true)}
            className={`flex-1 py-2 text-xs font-medium transition-colors ${showSessions ? 'text-accent border-b border-accent' : 'text-dark-text-secondary hover:text-dark-text'}`}
          >
            会话
          </button>
          <button
            onClick={() => setShowSessions(false)}
            className={`flex-1 py-2 text-xs font-medium transition-colors ${!showSessions ? 'text-accent border-b border-accent' : 'text-dark-text-secondary hover:text-dark-text'}`}
          >
            导航
          </button>
        </div>

        {/* Session List */}
        {showSessions ? (
          <div className="flex-1 flex flex-col overflow-hidden">
            <div className="p-2">
              <button
                onClick={handleNewSession}
                className="w-full py-2 text-sm text-dark-text-secondary border border-dashed border-dark-border rounded-lg hover:text-accent hover:border-accent/30 transition-all"
              >
                + 新对话
              </button>
            </div>
            <div className="flex-1 overflow-y-auto px-2 space-y-0.5">
              {sessions.map((s, idx) => (
                <div
                  key={s.id}
                  onClick={() => navigate(`/qa/${s.id}`)}
                  className={`group flex items-center gap-2 px-3 py-2 rounded-lg text-sm cursor-pointer transition-all ${
                    currentSessionId === s.id
                      ? 'bg-accent/10 text-accent'
                      : 'text-dark-text-secondary hover:text-dark-text hover:bg-dark-border/50'
                  }`}
                >
                  {editingId === s.id ? (
                    <input
                      value={editTitle}
                      onChange={e => setEditTitle(e.target.value)}
                      onBlur={() => handleRename(s.id)}
                      onKeyDown={e => e.key === 'Enter' && handleRename(s.id)}
                      className="flex-1 bg-dark-bg border border-accent/30 rounded px-2 py-0.5 text-sm text-dark-text outline-none"
                      autoFocus
                      onClick={e => e.stopPropagation()}
                    />
                  ) : (
                    <span className="flex-1 truncate"><span className="text-dark-text-secondary mr-1">{idx + 1}.</span>{s.title}</span>
                  )}
                  <div className="hidden group-hover:flex gap-1">
                    <button
                      onClick={e => { e.stopPropagation(); setEditingId(s.id); setEditTitle(s.title) }}
                      className="text-dark-text-secondary hover:text-accent text-sm"
                      title="重命名"
                    >✎</button>
                    <button
                      onClick={e => handleDelete(s.id, e)}
                      className="text-dark-text-secondary hover:text-danger text-sm"
                      title="删除"
                    >✕</button>
                  </div>
                </div>
              ))}
              {sessions.length === 0 && (
                <p className="text-center text-dark-text-secondary text-sm py-8">暂无会话</p>
              )}
            </div>
          </div>
        ) : (
          /* Navigation */
          <nav className="flex-1 py-2 px-2 space-y-0.5">
            {navItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.path === '/qa'}
                className={({ isActive }) =>
                  `flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all ${
                    isActive
                      ? 'bg-accent/10 text-accent'
                      : 'text-dark-text-secondary hover:text-dark-text hover:bg-dark-border/50'
                  }`
                }
              >
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </NavLink>
            ))}
          </nav>
        )}

        {/* Footer */}
        <div className="p-3 border-t border-dark-border">
          <p className="text-[10px] text-dark-text-secondary">FAQ KV Cache v1.0</p>
          <button onClick={handleLogout} className="text-[10px] text-dark-text-secondary hover:text-danger">退出登录</button>
        </div>
      </aside>

      {/* Main Content — overflow-auto for FaqManage etc. that rely on page-level scroll */}
      <main className="flex-1 overflow-auto min-w-0">
        {children}
      </main>
    </div>
  )
}

export default Layout
