import type { FaqItem, FaqCreateRequest, ApiResponse, FaqListResponse } from '../types'

const BASE_URL = '/api/faqs'

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export async function fetchFaqs(category?: string, keyword?: string): Promise<FaqListResponse> {
  const params = new URLSearchParams()
  if (category) params.set('category', category)
  if (keyword) params.set('keyword', keyword)
  const qs = params.toString()
  return request<FaqListResponse>(`${BASE_URL}${qs ? `?${qs}` : ''}`)
}

export async function fetchFaq(id: string): Promise<ApiResponse<FaqItem>> {
  return request<ApiResponse<FaqItem>>(`${BASE_URL}/${id}`)
}

export async function createFaq(data: FaqCreateRequest): Promise<ApiResponse<FaqItem>> {
  return request<ApiResponse<FaqItem>>(BASE_URL, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateFaq(id: string, data: Partial<FaqCreateRequest>): Promise<ApiResponse<FaqItem>> {
  return request<ApiResponse<FaqItem>>(`${BASE_URL}/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteFaq(id: string): Promise<ApiResponse<null>> {
  return request<ApiResponse<null>>(`${BASE_URL}/${id}`, { method: 'DELETE' })
}

export async function batchCreateFaqs(items: FaqCreateRequest[]): Promise<ApiResponse<FaqItem[]>> {
  return request<ApiResponse<FaqItem[]>>(`${BASE_URL}/batch`, {
    method: 'POST',
    body: JSON.stringify({ items }),
  })
}

export async function rebuildCache(): Promise<ApiResponse<null>> {
  return request<ApiResponse<null>>(`${BASE_URL}/rebuild-cache`, { method: 'POST' })
}
