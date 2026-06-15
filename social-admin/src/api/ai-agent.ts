const AI_AGENT_BASE_URL = import.meta.env.VITE_AI_AGENT_URL || 'http://localhost:8000'

import { getCookie } from '@/utils/cookie'

/** 安全读取 token：Cookie 优先 → localStorage 降级（与 social-frontend 统一） */
function readAuthToken(): string | null {
  return getCookie('token') || localStorage.getItem('token')
}

export interface AiAgentMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: number
}

export interface ChatResponse {
  reply: string
  session_id: string
  agent_type: string
  tools_called: string[]
  route_source: string
  skill_name: string
  eval: {
    route_confidence: string
    route_reason: string
    safety: Record<string, boolean>
    latency: Record<string, number>
    token: Record<string, number>
  }
}

/** Generate a session ID for admin user */
export function generateSessionId(userId?: number | string): string {
  if (userId) return `admin_${userId}`
  let sid = localStorage.getItem('ai_admin_session_id')
  if (!sid) {
    sid = `admin_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
    localStorage.setItem('ai_admin_session_id', sid)
  }
  return sid
}

/** Check if ai-agent is available */
export async function checkAiAgentHealth(): Promise<boolean> {
  try {
    const headers: Record<string, string> = {}
    const token = readAuthToken()
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }
    const res = await fetch(`${AI_AGENT_BASE_URL}/health`, {
      method: 'GET',
      headers,
      signal: AbortSignal.timeout(3000)
    })
    if (!res.ok) return false
    const data = await res.json()
    return data.status === 'ok'
  } catch {
    return false
  }
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

  fetch(`${AI_AGENT_BASE_URL}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId, token: token || null }),
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
export async function getChatHistory(sessionId: string): Promise<AiAgentMessage[]> {
  const res = await fetch(`${AI_AGENT_BASE_URL}/chat/history/${sessionId}`)
  if (!res.ok) return []
  const data = await res.json()
  const messages: AiAgentMessage[] = (data.messages || []).map((m: { role: string; content: string; timestamp: string }) => ({
    role: m.role as 'user' | 'assistant',
    content: m.content,
    timestamp: Number(m.timestamp) * 1000
  }))
  return messages
}

/** Clear a chat session */
export async function clearAiAgentSession(sessionId: string): Promise<void> {
  const res = await fetch(`${AI_AGENT_BASE_URL}/chat/clear/${sessionId}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(`清除会话失败: ${res.status}`)
}

// ============================================================
// Admin Dashboard API
// ============================================================

export interface LlmModel {
  level: number
  name: string
  active: boolean
}

export interface LlmStatus {
  current_model: string
  is_healthy: boolean
  fallback_level: number
  total_models: number
  seconds_since_fallback: number | null
  models: LlmModel[]
}

export interface ModelUsage {
  name: string
  count: number
}

export interface AiAgentDashboard {
  today: {
    conversations: number
    faq_hits: number
    faq_rate: number
    transfers: number
    active_sessions: number
    total_tokens: number
  }
  sentiment: {
    positive: { count: number; pct: number }
    neutral: { count: number; pct: number }
    negative: { count: number; pct: number }
  }
  feedback: {
    up: number
    down: number
    rate: number
  }
  tools: Array<{ name: string; calls: number; errors: number }>
  tool_summary: {
    total: number
    success: number
    fail: number
  }
  llm_status: LlmStatus | null
  model_usage: ModelUsage[]
  conversations_detail: Array<{
    user_id: string
    input_tokens: number
    output_tokens: number
    total_tokens: number
    duration_ms: number
    agent: string
    model?: string
    time: string
  }>
  tool_details: Array<{
    name: string
    duration_ms: number
    success: boolean
    time: string
  }>
}

/** 获取 AI 客服运营监控面板数据 */
export async function getAiAgentDashboard(): Promise<AiAgentDashboard> {
  const headers: Record<string, string> = {}
  const token = readAuthToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  const res = await fetch(`${AI_AGENT_BASE_URL}/admin/dashboard`, {
    headers,
    signal: AbortSignal.timeout(5000)
  })
  if (!res.ok) throw new Error('获取AI客服数据失败')
  return res.json()
}

/** 手动切换 LLM 模型级别 */
export async function switchLlm(level: number): Promise<void> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const token = readAuthToken()
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(`${AI_AGENT_BASE_URL}/admin/llm/switch`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ level }),
    signal: AbortSignal.timeout(5000)
  })
  if (!res.ok) throw new Error('切换模型失败')
}

/** 重置 LLM 到主力模型 */
export async function resetLlm(): Promise<void> {
  const headers: Record<string, string> = {}
  const token = readAuthToken()
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(`${AI_AGENT_BASE_URL}/admin/llm/reset`, {
    method: 'POST',
    headers,
    signal: AbortSignal.timeout(5000)
  })
  if (!res.ok) throw new Error('重置模型失败')
}


// ============================================================
// 转人工管理 API
// ============================================================

export interface TransferTicket {
  id: string
  user_id: string
  reason: string
  summary: string
  created_at: number
  status: 'pending' | 'accepted' | 'completed'
  accepted_at?: number
  completed_at?: number
}

export interface TransferDetail {
  ticket: TransferTicket
  recent_messages: Array<{ role: string; content: string; timestamp?: number }>
}

/** 获取待处理的转接队列 */
export async function getPendingTransfers(): Promise<{ total: number; tickets: TransferTicket[] }> {
  const headers: Record<string, string> = {}
  const token = readAuthToken()
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(`${AI_AGENT_BASE_URL}/admin/transfer/pending`, {
    headers,
    signal: AbortSignal.timeout(5000)
  })
  if (!res.ok) throw new Error('获取转接队列失败')
  return res.json()
}

/** 获取转接工单详情 + 聊天记录 */
export async function getTransferDetail(transferId: string): Promise<TransferDetail> {
  const headers: Record<string, string> = {}
  const token = readAuthToken()
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(`${AI_AGENT_BASE_URL}/admin/transfer/${transferId}`, {
    headers,
    signal: AbortSignal.timeout(5000)
  })
  if (!res.ok) throw new Error('获取工单详情失败')
  return res.json()
}

/** 接听转接 */
export async function acceptTransfer(transferId: string): Promise<void> {
  const headers: Record<string, string> = {}
  const token = readAuthToken()
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(`${AI_AGENT_BASE_URL}/admin/transfer/${transferId}/accept`, {
    method: 'POST',
    headers,
    signal: AbortSignal.timeout(5000)
  })
  if (!res.ok) throw new Error('接听失败')
}

/** 人工回复用户 */
export async function replyToUser(transferId: string, content: string, agentName = '人工客服'): Promise<void> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const token = readAuthToken()
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(`${AI_AGENT_BASE_URL}/admin/transfer/${transferId}/reply`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ content, agent_name: agentName }),
    signal: AbortSignal.timeout(5000)
  })
  if (!res.ok) throw new Error('回复失败')
}

/** 完成转接 */
export async function completeTransfer(transferId: string): Promise<void> {
  const headers: Record<string, string> = {}
  const token = readAuthToken()
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(`${AI_AGENT_BASE_URL}/admin/transfer/${transferId}/complete`, {
    method: 'POST',
    headers,
    signal: AbortSignal.timeout(5000)
  })
  if (!res.ok) throw new Error('完成转接失败')
}

/** 清空所有转人工工单（队列 + 详情 + 标记） */
export async function clearAllTransfers(): Promise<{ cleared: number }> {
  const headers: Record<string, string> = {}
  const token = readAuthToken()
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(`${AI_AGENT_BASE_URL}/admin/transfer/clear`, {
    method: 'DELETE',
    headers,
    signal: AbortSignal.timeout(5000)
  })
  if (!res.ok) throw new Error('清空工单失败')
  return res.json()
}


// ============================================================
// 评估体系 API
// ============================================================

export interface EvalReport {
  generated_at: string
  summary: {
    total: number
    passed: number
    failed: number
    accuracy: number
    avg_latency_ms: number
    tool_call_accuracy: number
    task_completion_rate: number
    hallucination_rate: number
    skill_accuracy: number
    skill_total: number
    skill_matched_count: number
    by_domain: Record<string, { total: number; passed: number; accuracy: number }>
    by_skill: Record<string, { total: number; matched: number; accuracy: number }>
  }
  details: Array<{
    id: string
    message: string
    domain: string
    difficulty: string
    passed: boolean
    skill_matched: boolean
    expected_skill_name: string
    keywords_missed: string[]
    forbidden_found: string[]
    latency_ms: number
    reply_preview: string
    error: string | null
  }>
}

export interface EvalRunResult {
  status: string
  message: string
  result: { total: number; passed: number; accuracy: number }
}

/** 触发批量评估 */
export async function runEval(domain?: string, difficulty?: string): Promise<EvalRunResult> {
  const headers: Record<string, string> = {}
  const token = readAuthToken()
  if (token) headers['Authorization'] = `Bearer ${token}`

  const params = new URLSearchParams()
  if (domain) params.set('domain', domain)
  if (difficulty) params.set('difficulty', difficulty)
  if (token) params.set('token', token)
  const qs = params.toString() ? `?${params.toString()}` : ''

  const res = await fetch(`${AI_AGENT_BASE_URL}/admin/eval/run${qs}`, {
    method: 'POST',
    headers,
    signal: AbortSignal.timeout(120000) // 评估可能耗时较长
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || `评估失败: ${res.status}`)
  }
  return res.json()
}

/** 获取最新评估报告 */
export async function getEvalReport(): Promise<EvalReport> {
  const headers: Record<string, string> = {}
  const token = readAuthToken()
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(`${AI_AGENT_BASE_URL}/admin/eval/report`, {
    headers,
    signal: AbortSignal.timeout(5000)
  })
  if (!res.ok) throw new Error('暂无评估报告')
  return res.json()
}


// ============================================================
// 实时质量监控 API
// ============================================================

export interface EvalRealtimeData {
  summary: {
    total_requests: number
    avg_routing_ms: number
    avg_total_ms: number
    total_input_tokens: number
    total_output_tokens: number
    total_tokens: number
  }
  route_distribution: Record<string, number>
  agent_distribution: Record<string, number>
  skill_distribution: Record<string, number>
  safety_events: Record<string, number>
  recent_requests: Array<{
    user_id: string
    agent_type: string
    route_source: string
    skill_name: string
    routing_ms: number
    total_ms: number
    input_tokens: number
    output_tokens: number
    tools_called: string[]
    is_faq: boolean
    time: string
  }>
}

/** 获取实时质量监控数据 */
export async function getEvalRealtime(): Promise<EvalRealtimeData> {
  const headers: Record<string, string> = {}
  const token = readAuthToken()
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(`${AI_AGENT_BASE_URL}/admin/eval/realtime`, {
    headers,
    signal: AbortSignal.timeout(5000)
  })
  if (!res.ok) throw new Error('获取实时数据失败')
  return res.json()
}


// ============================================================
// 链路拆解 API
// ============================================================

export interface EvalTrace {
  user_id: string
  agent_type: string
  route_source: string
  skill_name: string
  routing_ms: number
  total_ms: number
  input_tokens: number
  output_tokens: number
  tools_called: string[]
  is_faq: boolean
  time: string
}

/** 获取最近 N 条请求链路明细 */
export async function getEvalTraces(limit = 30): Promise<EvalTrace[]> {
  const headers: Record<string, string> = {}
  const token = readAuthToken()
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(`${AI_AGENT_BASE_URL}/admin/eval/traces?limit=${limit}`, {
    headers,
    signal: AbortSignal.timeout(5000)
  })
  if (!res.ok) throw new Error('获取链路数据失败')
  return res.json()
}
