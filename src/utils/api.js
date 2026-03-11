const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function fetchAPI(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options
  })
  if (!res.ok) throw new Error(`API ${path} failed: ${res.status}`)
  return res.json()
}

export const api = {
  getCalls: () => fetchAPI('/api/calls'),
  getRandomCall: () => fetchAPI('/api/calls/random'),
  getCall: (id) => fetchAPI(`/api/calls/${id}`),
  submitGuess: (body) => fetchAPI('/api/guess', { method: 'POST', body: JSON.stringify(body) }),
  getLeaderboard: () => fetchAPI('/api/leaderboard'),
  getStats: () => fetchAPI('/api/stats'),
  predictCall: (callId) => fetchAPI('/api/predict/call', { method: 'POST', body: JSON.stringify({ call_id: callId }) }),
}

export default api
