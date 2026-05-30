import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import FaqManage from './pages/FaqManage'
import DocumentManage from './pages/DocumentManage'
import QaChat from './pages/QaChat'

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Navigate to="/qa" replace />} />
          <Route path="/faq" element={<FaqManage />} />
          <Route path="/documents" element={<DocumentManage />} />
          <Route path="/qa" element={<QaChat />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}

export default App
