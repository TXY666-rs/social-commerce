<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getCookie } from '@/utils/cookie'
import {
  getPendingTransfers,
  getTransferDetail,
  acceptTransfer,
  replyToUser,
  completeTransfer,
  clearAllTransfers,
  type TransferTicket,
  type TransferDetail,
} from '@/api/ai-agent'

const loading = ref(false)
const tickets = ref<TransferTicket[]>([])
const selectedTicket = ref<TransferDetail | null>(null)
const replyContent = ref('')
const replying = ref(false)
const detailLoading = ref(false)
let pollTimer: ReturnType<typeof setInterval> | null = null
let transferSseAbort: AbortController | null = null
// 独立 chatMessages：getTransferDetail 拉历史 → 启动 SSE 推增量
const chatMessages = ref<Array<{ role: string; content: string; source?: string; timestamp?: number }>>([])

async function loadTickets() {
  try {
    const data = await getPendingTransfers()
    tickets.value = data.tickets
  } catch {
    // 静默失败，轮询时不影响
  }
}

async function clearTickets() {
  try {
    await ElMessageBox.confirm('确认清空所有转人工工单？此操作不可恢复。', '清空工单', {
      confirmButtonText: '确认清空',
      cancelButtonText: '取消',
      type: 'warning',
    })
    const result = await clearAllTransfers()
    tickets.value = []
    selectedTicket.value = null
    ElMessage.success(`已清空 ${result.cleared} 条工单记录`)
  } catch {
    // 取消或失败
  }
}

async function openDetail(ticket: TransferTicket) {
  detailLoading.value = true
  disconnectTransferStream()
  chatMessages.value = []
  try {
    selectedTicket.value = await getTransferDetail(ticket.id)
    // 待处理或服务中的工单 → 加载历史 + 连接 SSE 实时收用户消息
    // （pending 阶段也连，让客服在接听前就能看到用户后续输入）
    if (selectedTicket.value?.ticket.status === 'accepted' || selectedTicket.value?.ticket.status === 'pending') {
      chatMessages.value = (selectedTicket.value.recent_messages || []).map(m => ({
        role: m.role,
        content: m.content,
        source: (m as any).source,
        timestamp: (m as any).timestamp ? Number((m as any).timestamp) * 1000 : undefined,
      }))
      connectTransferStream(ticket.id)
    }
  } catch {
    ElMessage.error('获取工单详情失败')
  } finally {
    detailLoading.value = false
  }
}

async function handleAccept() {
  if (!selectedTicket.value) return
  loading.value = true
  try {
    await acceptTransfer(selectedTicket.value.ticket.id)
    ElMessage.success('已接听')
    selectedTicket.value.ticket.status = 'accepted'
    // 重新拉详情 + 启动 SSE
    selectedTicket.value = await getTransferDetail(selectedTicket.value.ticket.id)
    chatMessages.value = (selectedTicket.value.recent_messages || []).map(m => ({
      role: m.role,
      content: m.content,
      source: (m as any).source,
      timestamp: (m as any).timestamp ? Number((m as any).timestamp) * 1000 : undefined,
    }))
    connectTransferStream(selectedTicket.value.ticket.id)
    await loadTickets()
  } catch {
    ElMessage.error('接听失败')
  } finally {
    loading.value = false
  }
}

async function handleReply() {
  if (!selectedTicket.value || !replyContent.value.trim()) return
  const content = replyContent.value.trim()
  const ticketId = selectedTicket.value.ticket.id
  // 乐观追加到本地（避免等 SSE 推回自己）
  chatMessages.value.push({
    role: 'assistant',
    content,
    source: 'human_agent',
    timestamp: Date.now(),
  })
  replyContent.value = ''
  replying.value = true
  try {
    await replyToUser(ticketId, content)
  } catch {
    ElMessage.error('回复失败')
    chatMessages.value.pop()
  } finally {
    replying.value = false
  }
}

// ── SSE 实时收用户消息（Pub/Sub 推过来的帧） ──
const AI_AGENT_BASE_URL = (import.meta as any).env.VITE_AI_AGENT_URL || 'http://localhost:9000/api/ai'

function connectTransferStream(transferId: string) {
  if (transferSseAbort) return
  const token = getCookie('token') || localStorage.getItem('token')
  if (!token) return
  transferSseAbort = new AbortController()
  const url = `${AI_AGENT_BASE_URL}/admin/transfer/${encodeURIComponent(transferId)}/stream?token=${encodeURIComponent(token)}`
  // Gateway 全局 JWT 鉴权需要 Authorization 头
  const headers: Record<string, string> = { Authorization: `Bearer ${token}` }
  fetch(url, { signal: transferSseAbort.signal, headers }).then(async (resp) => {
    if (!resp.ok) {
      console.error('[SSE] 连接失败:', resp.status, resp.statusText)
      transferSseAbort = null
      return
    }
    const reader = resp.body?.getReader()
    if (!reader) {
      console.error('[SSE] 无法获取响应流 reader')
      return
    }
    console.log('[SSE] 连接建立成功, transferId:', transferId)
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const msg = JSON.parse(line.slice(6))
          if (msg.type === 'connected') {
            console.log('[SSE] 服务端确认连接')
          } else if (msg.type === 'message' && msg.role === 'user') {
            const msgTs = Number(msg.timestamp || 0) * 1000
            // 严格去重（timestamp + content）
            const exists = chatMessages.value.some(m =>
              m.content === (msg.content || '') && (m.timestamp ?? 0) === msgTs
            )
            if (!exists) {
              chatMessages.value.push({
                role: 'user',
                content: msg.content || '',
                source: 'user',
                timestamp: msgTs,
              })
            }
          } else if (msg.type === 'status' && msg.status === 'completed') {
            disconnectTransferStream()
            loadTickets()
            return
          }
        } catch { /* ignore */ }
      }
    }
  }).catch((err) => {
    if (err?.name !== 'AbortError') {
      console.error('[SSE] 连接异常:', err)
    }
  }).finally(() => { transferSseAbort = null })
}

function disconnectTransferStream() {
  if (transferSseAbort) {
    transferSseAbort.abort()
    transferSseAbort = null
  }
}

async function handleComplete() {
  if (!selectedTicket.value) return
  try {
    await ElMessageBox.confirm('确定完成本次转接？', '确认')
    loading.value = true
    await completeTransfer(selectedTicket.value.ticket.id)
    ElMessage.success('转接已完成')
    selectedTicket.value = null
    await loadTickets()
  } catch {
    // 用户取消或失败
  } finally {
    loading.value = false
  }
}

function formatTime(ts: number) {
  if (!ts) return ''
  return new Date(ts * 1000).toLocaleString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function statusLabel(status: string) {
  const map: Record<string, string> = { pending: '待接听', accepted: '正在处理', completed: '已完成' }
  return map[status] || status
}

function statusType(status: string) {
  const map: Record<string, string> = { pending: 'warning', accepted: 'success', completed: 'info' }
  return map[status] || 'info'
}

onMounted(() => {
  loadTickets()
  pollTimer = setInterval(loadTickets, 10000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
  disconnectTransferStream()
})
</script>

<template>
  <div class="transfer-page">
    <!-- 左侧：工单列表 -->
    <div class="ticket-list">
      <div class="list-header">
        <span class="title">转人工队列</span>
        <div class="header-actions">
          <el-tag type="warning" size="small">{{ tickets.length }} 待接听</el-tag>
          <el-button v-if="tickets.length > 0" type="danger" size="small" plain @click="clearTickets">
            清空队列
          </el-button>
        </div>
      </div>
      <div v-if="tickets.length === 0" class="empty-hint">
        暂无待接听的转接工单
      </div>
      <div
        v-for="ticket in tickets"
        :key="ticket.id"
        class="ticket-item"
        :class="{ active: selectedTicket?.ticket.id === ticket.id }"
        @click="openDetail(ticket)"
      >
        <div class="ticket-top">
          <span class="ticket-id">#{{ ticket.id }}</span>
          <el-tag :type="statusType(ticket.status) as any" size="small">
            {{ statusLabel(ticket.status) }}
          </el-tag>
        </div>
        <div class="ticket-reason">{{ ticket.reason }}</div>
        <div class="ticket-meta">
          <span>用户 {{ ticket.user_id }}</span>
          <span>{{ formatTime(ticket.created_at) }}</span>
        </div>
      </div>
    </div>

    <!-- 右侧：工单详情 + 聊天 -->
    <div class="ticket-detail">
      <div v-if="!selectedTicket" class="detail-empty">
        <p>选择左侧工单查看详情</p>
      </div>
      <div v-else v-loading="detailLoading" class="detail-content">
        <!-- 工单信息 -->
        <div class="detail-header">
          <div class="detail-info">
            <span class="detail-id">工单 #{{ selectedTicket.ticket.id }}</span>
            <el-tag :type="statusType(selectedTicket.ticket.status) as any" size="small">
              {{ statusLabel(selectedTicket.ticket.status) }}
            </el-tag>
          </div>
          <div class="detail-actions">
            <el-button
              v-if="selectedTicket.ticket.status === 'pending'"
              type="primary"
              size="small"
              :loading="loading"
              @click="handleAccept"
            >
              接听
            </el-button>
            <el-button
              v-if="selectedTicket.ticket.status === 'accepted'"
              type="danger"
              size="small"
              :loading="loading"
              @click="handleComplete"
            >
              结束服务
            </el-button>
          </div>
        </div>

        <!-- 对话摘要 -->
        <div v-if="selectedTicket.ticket.summary" class="summary-box">
          <div class="summary-title">对话摘要</div>
          <pre class="summary-text">{{ selectedTicket.ticket.summary }}</pre>
        </div>

        <!-- 聊天记录（实时更新：getTransferDetail 初始化 + SSE 推增量） -->
        <div class="chat-messages">
          <div
            v-for="(msg, idx) in chatMessages"
            :key="(msg.timestamp ?? 0) + '-' + idx"
            class="chat-msg"
            :class="msg.role"
          >
            <div class="msg-role">{{ msg.role === 'user' ? '用户' : '客服' }}</div>
            <div class="msg-content">{{ msg.content }}</div>
          </div>
        </div>

        <!-- 回复输入框 -->
        <div v-if="selectedTicket.ticket.status === 'accepted'" class="reply-box">
          <el-input
            v-model="replyContent"
            type="textarea"
            :rows="2"
            placeholder="输入回复内容..."
            @keydown.ctrl.enter="handleReply"
          />
          <el-button
            type="primary"
            :loading="replying"
            :disabled="!replyContent.trim()"
            @click="handleReply"
          >
            发送回复
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.transfer-page {
  display: flex;
  gap: 16px;
  height: calc(100vh - 120px);
}

.ticket-list {
  width: 320px;
  flex-shrink: 0;
  background: var(--bg-card);
  border-radius: var(--r-lg);
  border: 1px solid var(--border);
  overflow-y: auto;

  .list-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px;
    border-bottom: 1px solid var(--border);

    .title {
      font-weight: 600;
      color: var(--text-primary);
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 8px;
    }
  }

  .empty-hint {
    padding: 40px 16px;
    text-align: center;
    color: var(--text-caption);
    font-size: 14px;
  }

  .ticket-item {
    padding: 12px 16px;
    cursor: pointer;
    border-bottom: 1px solid var(--border);
    transition: background 0.15s;

    &:hover { background: var(--bg-hover); }
    &.active { background: var(--accent-glow); }

    .ticket-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 6px;

      .ticket-id {
        font-family: monospace;
        font-size: 13px;
        color: var(--text-caption);
      }
    }

    .ticket-reason {
      font-size: 14px;
      color: var(--text-primary);
      margin-bottom: 6px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .ticket-meta {
      display: flex;
      justify-content: space-between;
      font-size: 12px;
      color: var(--text-caption);
    }
  }
}

.ticket-detail {
  flex: 1;
  background: var(--bg-card);
  border-radius: var(--r-lg);
  border: 1px solid var(--border);
  display: flex;
  flex-direction: column;

  .detail-empty {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-caption);
    font-size: 14px;
  }

  .detail-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: 16px;
    overflow: hidden;
  }

  .detail-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;

    .detail-info {
      display: flex;
      align-items: center;
      gap: 8px;

      .detail-id {
        font-weight: 600;
        font-size: 15px;
        color: var(--text-primary);
      }
    }
  }

  .summary-box {
    background: var(--bg-deep);
    border-radius: var(--r-md);
    padding: 10px 14px;
    margin-bottom: 12px;

    .summary-title {
      font-size: 12px;
      color: var(--text-caption);
      margin-bottom: 6px;
    }

    .summary-text {
      font-size: 13px;
      color: var(--text-primary);
      white-space: pre-wrap;
      margin: 0;
      font-family: inherit;
    }
  }

  .chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 8px 0;

    .chat-msg {
      margin-bottom: 10px;

      .msg-role {
        font-size: 12px;
        color: var(--text-caption);
        margin-bottom: 3px;
      }

      .msg-content {
        padding: 8px 12px;
        border-radius: var(--r-md);
        font-size: 14px;
        line-height: 1.5;
        max-width: 80%;
        word-break: break-word;
      }

      &.user .msg-content {
        background: var(--bg-deep);
        color: var(--text-primary);
      }

      &.assistant .msg-content {
        background: var(--accent-glow);
        color: var(--text-primary);
        margin-left: auto;
      }
    }
  }

  .reply-box {
    display: flex;
    gap: 8px;
    align-items: flex-end;
    padding-top: 12px;
    border-top: 1px solid var(--border);

    .el-input { flex: 1; }
  }
}
</style>
