<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getPendingTransfers,
  getTransferDetail,
  acceptTransfer,
  replyToUser,
  completeTransfer,
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

async function loadTickets() {
  try {
    const data = await getPendingTransfers()
    tickets.value = data.tickets
  } catch {
    // 静默失败，轮询时不影响
  }
}

async function openDetail(ticket: TransferTicket) {
  detailLoading.value = true
  try {
    selectedTicket.value = await getTransferDetail(ticket.id)
  } catch (e) {
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
    await loadTickets()
  } catch {
    ElMessage.error('接听失败')
  } finally {
    loading.value = false
  }
}

async function handleReply() {
  if (!selectedTicket.value || !replyContent.value.trim()) return
  replying.value = true
  try {
    await replyToUser(selectedTicket.value.ticket.id, replyContent.value.trim())
    ElMessage.success('回复已发送')
    // 刷新聊天记录
    selectedTicket.value = await getTransferDetail(selectedTicket.value.ticket.id)
    replyContent.value = ''
  } catch {
    ElMessage.error('回复失败')
  } finally {
    replying.value = false
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
  const map: Record<string, string> = { pending: '待处理', accepted: '服务中', completed: '已完成' }
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
})
</script>

<template>
  <div class="transfer-page">
    <!-- 左侧：工单列表 -->
    <div class="ticket-list">
      <div class="list-header">
        <span class="title">转人工队列</span>
        <el-tag type="warning" size="small">{{ tickets.length }} 待处理</el-tag>
      </div>
      <div v-if="tickets.length === 0" class="empty-hint">
        暂无待处理的转接工单
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

        <!-- 聊天记录 -->
        <div class="chat-messages">
          <div
            v-for="(msg, idx) in selectedTicket.recent_messages"
            :key="idx"
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
