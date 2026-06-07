import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { login } from '../services/auth'

interface LoginProps {
  onLogin: (userId: string) => void
}

const Login: React.FC<LoginProps> = ({ onLogin }) => {
  const [input, setInput] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const userId = input.trim()
    if (!userId) return

    setLoading(true)
    setError('')
    try {
      await login(userId)
      onLogin(userId)
      navigate('/qa')
    } catch (err: any) {
      setError(err.message || '登录失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex items-center justify-center h-screen bg-dark-bg">
      <form onSubmit={handleSubmit} className="bg-dark-card border border-dark-border rounded-2xl p-8 w-full max-w-sm shadow-2xl">
        <h1 className="text-xl font-semibold text-dark-text text-center mb-2">
          <span className="text-accent">FAQ</span> Agent
        </h1>
        <p className="text-sm text-dark-text-secondary text-center mb-6">输入数字 ID 登录，不存在则自动创建</p>

        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="请输入用户ID（数字）"
          className="w-full bg-dark-bg border border-dark-border rounded-lg px-4 py-3 text-sm text-dark-text outline-none focus:border-accent/50 transition-all placeholder-dark-text-secondary/50 mb-4"
          autoFocus
          disabled={loading}
        />

        {error && <p className="text-danger text-xs mb-3">{error}</p>}

        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="w-full py-3 bg-accent/10 text-accent border border-accent/20 rounded-lg hover:bg-accent/20 transition-all text-sm font-medium disabled:opacity-50"
        >
          {loading ? '登录中...' : '进入'}
        </button>
      </form>
    </div>
  )
}

export default Login
