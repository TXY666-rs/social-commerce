import { getCookie } from '@/utils/cookie'

const AI_AGENT_BASE_URL = import.meta.env.VITE_AI_AGENT_URL || 'http://localhost:8000'

/** 安全读取 token：Cookie 优先 → localStorage 降级 */
function readAuthToken(fallback?: string): string | null {
  return fallback || getCookie('token') || localStorage.getItem('token')
}

export interface AiAgentMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: number
}

export interface ChatResponse {
  reply: string
  session_id: string
}

/** Generate a session ID from user info（需登录后调用） */
export function generateSessionId(userId: number | string): string {
  return `user_${userId}`
}

/** Check if ai-agent is available */
export async function checkAiAgentHealth(): Promise<{ available: boolean; redisAvailable: boolean }> {
  try {
    const res = await fetch(`${AI_AGENT_BASE_URL}/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(3000)
    })
    if (!res.ok) return { available: false, redisAvailable: false }
    const data = await res.json()
    return {
      available: data.status === 'ok',
      redisAvailable: data.redis_available === true
    }
  } catch {
    return { available: false, redisAvailable: false }
  }
}

/** Send a message to the ai-agent and get a full reply */
export async function sendAiAgentMessage(
  message: string,
  sessionId: string,
  token?: string
): Promise<ChatResponse> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const authToken = readAuthToken(token)
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`
  }
  const res = await fetch(`${AI_AGENT_BASE_URL}/chat`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ message, session_id: sessionId, token: authToken || null })
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || `请求失败: ${res.status}`)
  }
  return res.json()
}

/**
 * SSE 流式调用 ai-agent
 */
export function streamAiAgentMessage(
  message: string,
  sessionId: string,
  token: string | undefined,
  onChunk: (text: string) => void,
  onDone: (sessionId: string) => void,
  onError: (error: Error) => void
): AbortController {
  const controller = new AbortController()
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const authToken = readAuthToken(token)
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`
  }

  fetch(`${AI_AGENT_BASE_URL}/chat/stream`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ message, session_id: sessionId, token: authToken || null }),
    signal: controller.signal
  })
    .then(async (response) => {
      if (!response.ok) {
        const text = await response.text().catch(() => '')
        throw new Error(text || `请求失败: ${response.status}`)
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error('无法读取响应流')

      const decoder = new TextDecoder()
      let buffer = ''
      let finalSessionId = sessionId

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed || !trimmed.startsWith('data:')) continue

          try {
            const data = JSON.parse(trimmed.slice(5).trim())
            if (data.done) {
              finalSessionId = data.session_id || sessionId
            } else if (data.content) {
              onChunk(data.content)
            }
          } catch {
            // ignore parse errors
          }
        }
      }

      if (buffer.trim()) {
        const trimmed = buffer.trim()
        if (trimmed.startsWith('data:')) {
          try {
            const data = JSON.parse(trimmed.slice(5).trim())
            if (data.done) {
              finalSessionId = data.session_id || sessionId
            } else if (data.content) {
              onChunk(data.content)
            }
          } catch {
            // ignore
          }
        }
      }

      onDone(finalSessionId)
    })
    .catch((err) => {
      if (err.name === 'AbortError') return
      onError(err)
    })

  return controller
}

/** Get chat history for a session */
export async function getAiAgentHistory(sessionId: string): Promise<{ session_id: string; messages: Array<{ role: string; content: string; timestamp: string }> }> {
  const url = `${AI_AGENT_BASE_URL}/chat/history/${sessionId}`
  console.log(`[AiCS-API] GET ${url}`)
  const headers: Record<string, string> = {}
  const authToken = readAuthToken()
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`
  }
  const res = await fetch(url, {
    headers,
    signal: AbortSignal.timeout(5000)
  })
  console.log(`[AiCS-API] 响应状态: ${res.status} ${res.statusText}`)
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    console.error(`[AiCS-API] 响应体: "${text}"`)
    throw new Error(`获取历史失败: ${res.status}`)
  }
  return res.json()
}

/** Clear a chat session */
export async function clearAiAgentSession(sessionId: string): Promise<void> {
  const res = await fetch(`${AI_AGENT_BASE_URL}/chat/clear/${sessionId}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(`清除会话失败: ${res.status}`)
}

// ============================================================
// A4: 用户反馈 API
// ============================================================

export interface FeedbackPayload {
  session_id: string
  rating: 'up' | 'down'
  message_content?: string
  token?: string
}

/** 提交 AI 回复的 👍/👎 反馈 */
export async function submitAiFeedback(payload: FeedbackPayload): Promise<void> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const authToken = readAuthToken(payload.token)
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`
  }
  const res = await fetch(`${AI_AGENT_BASE_URL}/chat/feedback`, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(`提交反馈失败: ${res.status}`)
}
