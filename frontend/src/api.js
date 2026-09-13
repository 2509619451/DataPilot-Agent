import axios from 'axios'

export const api = axios.create({ baseURL: '/api', timeout: 120000 })

export async function uploadDataset(file) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post('/datasets/upload', form)
  return data
}

export async function createReport(sessionId) {
  const { data } = await api.post('/reports', { session_id: sessionId })
  return data
}

export async function streamChat(body, onEvent) {
  const response = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  })
  if (!response.ok) throw new Error(await response.text())
  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop() || ''
    for (const part of parts) {
      const line = part.split('\n').find(x => x.startsWith('data: '))
      if (!line) continue
      onEvent(JSON.parse(line.slice(6)))
    }
  }
}
