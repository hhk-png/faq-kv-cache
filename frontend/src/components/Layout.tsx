import React from 'react'
import { NavLink } from 'react-router-dom'

const navItems = [
  { path: '/qa', label: '问答', icon: '💬' },
  { path: '/faq', label: 'FAQ管理', icon: '📋' },
  { path: '/documents', label: '文档管理', icon: '📄' },
]

const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div className="flex h-screen bg-dark-bg">
      {/* Sidebar */}
      <aside className="w-60 bg-dark-card border-r border-dark-border flex flex-col">
        {/* Logo */}
        <div className="h-16 flex items-center px-6 border-b border-dark-border">
          <h1 className="text-lg font-semibold text-dark-text">
            <span className="text-accent">FAQ</span> Agent
          </h1>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-4 px-3 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm transition-all ${
                  isActive
                    ? 'bg-accent/10 text-accent border border-accent/20'
                    : 'text-dark-text-secondary hover:text-dark-text hover:bg-dark-border/50'
                }`
              }
            >
              <span className="text-lg">{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-dark-border">
          <p className="text-xs text-dark-text-secondary">
            FAQ KV Cache v1.0
          </p>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  )
}

export default Layout
