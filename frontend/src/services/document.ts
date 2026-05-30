import type { DocumentItem, DocumentContent, ApiResponse, DocumentListResponse } from '../types'

const BASE_URL = '/api/documents'

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export async function fetchDocuments(): Promise<DocumentListResponse> {
  return request<DocumentListResponse>(BASE_URL)
}

export async function fetchDocument(id: string): Promise<ApiResponse<DocumentItem>> {
  return request<ApiResponse<DocumentItem>>(`${BASE_URL}/${id}`)
}

export async function fetchDocumentContent(id: string): Promise<ApiResponse<DocumentContent>> {
  return request<ApiResponse<DocumentContent>>(`${BASE_URL}/${id}/content`)
}

export async function uploadDocument(file: File): Promise<ApiResponse<DocumentItem>> {
  const formData = new FormData()
  formData.append('file', file)
  return request<ApiResponse<DocumentItem>>(`${BASE_URL}/upload`, {
    method: 'POST',
    body: formData,
  })
}

export async function updateDocumentTitle(id: string, title: string): Promise<ApiResponse<DocumentItem>> {
  return request<ApiResponse<DocumentItem>>(`${BASE_URL}/${id}`, {
    method: 'PUT',
    body: JSON.stringify({ title }),
    headers: { 'Content-Type': 'application/json' },
  })
}

export async function deleteDocument(id: string): Promise<ApiResponse<null>> {
  return request<ApiResponse<null>>(`${BASE_URL}/${id}`, { method: 'DELETE' })
}
