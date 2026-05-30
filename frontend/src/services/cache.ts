import type { CacheBlockStatus, ApiResponse } from '../types'

const BASE_URL = '/api/cache'

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

export async function fetchCacheStatus(): Promise<ApiResponse<CacheBlockStatus[]>> {
  return request<ApiResponse<CacheBlockStatus[]>>(`${BASE_URL}/status`)
}
