const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
const AUTH_KEY = 'smartWarehouseAuth'

export const authStorage = {
  load() {
    try {
      return JSON.parse(localStorage.getItem(AUTH_KEY) || 'null')
    } catch {
      return null
    }
  },
  save(payload) {
    localStorage.setItem(AUTH_KEY, JSON.stringify(payload))
  },
  clear() {
    localStorage.removeItem(AUTH_KEY)
  },
  token() {
    return this.load()?.token || ''
  },
  user() {
    return this.load()?.user || null
  }
}

async function request(url, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) }
  const token = authStorage.token()
  if (token) headers.Authorization = `Bearer ${token}`

  const response = await fetch(API_BASE + url, {
    headers,
    ...options
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(data.error || '请求失败')
  }
  return data
}

export const api = {
  login: (payload) => request('/api/auth/login', { method: 'POST', body: JSON.stringify(payload) }),
  register: (payload) => request('/api/auth/register', { method: 'POST', body: JSON.stringify(payload) }),
  getDashboard: () => request('/api/dashboard'),
  getTwin: () => request('/api/warehouse/twin'),
  getShelf: (id) => request(`/api/warehouse/shelves/${id}`),
  updateWarehouseStorageType: (warehouseId, payload) => request(`/api/warehouse/${warehouseId}/storage-type`, { method: 'PATCH', body: JSON.stringify(payload) }),
  getProducts: () => request('/api/products'),
  recommendInbound: (payload) => request('/api/inbound/recommend', { method: 'POST', body: JSON.stringify(payload) }),
  confirmInbound: (payload) => request('/api/inbound/confirm', { method: 'POST', body: JSON.stringify(payload) }),
  createOutbound: (payload) => request('/api/outbound/orders', { method: 'POST', body: JSON.stringify(payload) }),
  finishOutbound: (orderId) => request(`/api/outbound/orders/${orderId}/finish`, { method: 'POST' }),
  getColdChainOverview: () => request('/api/cold-chain/overview'),
  getDataPlatformOverview: () => request('/api/data-platform/overview'),
  getFreshBatches: () => request('/api/fresh/batches'),
  getRiskBatches: () => request('/api/fresh/batches/risk'),
  confirmFreshReceive: (payload) => request('/api/fresh/receive/confirm', { method: 'POST', body: JSON.stringify(payload) }),
  listWarnings: () => request('/api/warnings'),
  scanWarnings: () => request('/api/warnings/scan', { method: 'POST' }),
  confirmWarning: (id) => request(`/api/warnings/${id}/confirm`, { method: 'POST' }),
  chat: (question) => request('/api/ai/chat', { method: 'POST', body: JSON.stringify({ question }) }),
  listScheduleBatches: () => request('/api/schedules/batches'),
  listScheduleOrders: () => request('/api/schedules/orders'),
  listColdRoomsForSchedule: () => request('/api/schedules/cold-rooms'),
  listScheduleVehicles: () => request('/api/schedules/vehicles'),
  listScheduleRoutes: () => request('/api/schedules/routes'),
  solveSchedule: (payload) => request('/api/schedules/solve', { method: 'POST', body: JSON.stringify(payload || {}) }),
  getSchedule: (id) => request(`/api/schedules/${id}`),
  confirmSchedule: (id) => request(`/api/schedules/${id}/confirm`, { method: 'POST' })

}
