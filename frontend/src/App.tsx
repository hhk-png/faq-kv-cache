import React, { useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import FaqManage from './pages/FaqManage'
import DocumentManage from './pages/DocumentManage'
import QaChat from './pages/QaChat'
import Login from './pages/Login'

const App: React.FC = () => {
  const [userId, setUserId] = useState(localStorage.getItem('faq_user_id') || '')

  const handleLogin = (id: string) => {
    localStorage.setItem('faq_user_id', id)
    setUserId(id)
  }

  if (!userId) {
    return (
      <BrowserRouter>
        <Routes>
          <Route path="*" element={<Login onLogin={handleLogin} />} />
        </Routes>
      </BrowserRouter>
    )
  }

  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Navigate to="/qa" replace />} />
          <Route path="/faq" element={<FaqManage />} />
          <Route path="/documents" element={<DocumentManage />} />
          <Route path="/qa" element={<QaChat />} />
          <Route path="/qa/:sessionId" element={<QaChat />} />
          <Route path="*" element={<Navigate to="/qa" replace />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}

export default App
