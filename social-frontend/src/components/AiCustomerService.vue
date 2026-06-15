<template>
  <div v-if="userStore.isLoggedIn" class="ai-cs-container">
    <!-- Floating button -->
    <div
      v-if="!isOpen"
      class="ai-cs-fab"
      :style="fabStyle"
      @mousedown="onDragStart"
      @click="toggleOpen"
      @touchstart.passive="onTouchStart"
    >
      <el-icon :size="28" color="#fff"><Monitor /></el-icon>
      <span class="fab-tooltip">AI 客服</span>
    </div>

    <!-- Chat window -->
    <transition name="ai-cs-pop">
      <div v-if="isOpen" class="ai-cs-window" :class="{ 'ai-cs-mobile': isMobile }" :style="windowStyle">
        <!-- Header -->
        <div class="ai-cs-header" @mousedown="onDragStart" @touchstart.passive="onTouchStart">
          <div class="header-left">
            <el-avatar :size="32" class="ai-avatar">
              <el-icon :size="18"><Monitor /></el-icon>
            </el-avatar>
            <span class="header-title">AI 智能客服</span>
          </div>
          <div class="header-actions">
            <el-icon class="action-icon" @click.stop="clearChat"><Delete /></el-icon>
            <el-icon class="action-icon" @click.stop="toggleOpen"><Close /></el-icon>
          </div>
        </div>

        <!-- Service unavailable -->
        <div v-if="!isServiceAvailable && !isChecking" class="ai-cs-unavailable">
          <el-icon :size="48" color="#9e96a7"><WarningFilled /></el-icon>
          <p>AI 客服暂时不可用</p>
          <el-button type="primary" @click="checkHealth" size="small">重试连接</el-button>
        </div>

        <!-- Messages -->
        <div v-else ref="messagesRef" class="ai-cs-messages" @click="onMessageClick">
          <!-- 转人工提示条 -->
          <div v-if="transferStatus !== 'none'" class="transfer-banner">
            <el-icon :size="14"><Promotion /></el-icon>
            <span v-if="transferStatus === 'pending'">已转接人工客服，正在为您接入...</span>
            <span v-else>正在与人工客服对话中，AI 已暂停响应</span>
          </div>

          <div v-if="messages.length === 0" class="welcome">
            <el-icon :size="40" color="var(--text-ghost)"><Monitor /></el-icon>
            <p>你好！有什么可以帮你的？</p>
            <div class="quick-questions">
              <span v-for="(q, i) in quickQuestions" :key="i" class="quick-tag" @click="sendQuick(q)">{{ q }}</span>
            </div>
          </div>

          <div v-for="(msg, idx) in messages" :key="idx" class="msg-row" :class="msg.role">
            <template v-if="msg.role === 'assistant'">
              <el-avatar :size="28" :class="msg.source === 'human' ? 'msg-human-avatar' : 'msg-ai-avatar'" :aria-label="msg.source === 'human' ? '人工客服头像' : 'AI客服头像'">
                <el-icon :size="14"><Monitor v-if="msg.source !== 'human'" /><Promotion v-else /></el-icon>
              </el-avatar>
              <div class="msg-bubble-wrapper">
                <span v-if="msg.source === 'human'" class="msg-source-tag">人工客服</span>
                <div class="msg-bubble" :class="msg.source === 'human' ? 'human-bubble' : 'ai-bubble'" role="article" :aria-label="(msg.source === 'human' ? '人工客服: ' : 'AI回复: ') + msg.content.slice(0, 50)">
                  <div class="msg-text" v-html="renderMarkdown(msg.content)"></div>
                </div>
                <!-- A4: 反馈按钮（仅非空回复显示） -->
                <div v-if="msg.content && msg.content.length > 5 && !msg.isSystem && msg.source !== 'human'" class="msg-feedback">
                  <button
                    class="fb-btn"
                    :class="{ active: msg.feedback === 'up' }"
                    @click.stop="submitFeedback(idx, 'up')"
                    :disabled="msg.feedbackSubmitting"
                    :aria-label="msg.feedback === 'up' ? '已点赞' : '点赞此回复'"
                    title="有帮助"
                  >👍</button>
                  <button
                    class="fb-btn"
                    :class="{ active: msg.feedback === 'down' }"
                    @click.stop="submitFeedback(idx, 'down')"
                    :disabled="msg.feedbackSubmitting"
                    :aria-label="msg.feedback === 'down' ? '已点踩' : '点踩此回复'"
                    title="没帮助"
                  >👎</button>
                </div>
              </div>
            </template>
            <template v-else>
              <div class="msg-bubble user-bubble" role="article" aria-label="用户消息">
                <div class="msg-text">{{ msg.content }}</div>
              </div>
            </template>
          </div>

          <div v-if="isLoading" class="msg-row assistant">
            <el-avatar :size="28" class="msg-ai-avatar">
              <el-icon :size="14"><Monitor /></el-icon>
            </el-avatar>
            <div class="msg-bubble ai-bubble">
              <div class="typing-dots"><span></span><span></span><span></span></div>
            </div>
          </div>
        </div>

        <!-- Input -->
        <div v-if="isServiceAvailable" class="ai-cs-input">
          <el-input
            v-model="inputText"
            :rows="1"
            :autosize="{ minRows: 1, maxRows: 3 }"
            type="textarea"
            placeholder="输入消息..."
            :disabled="isLoading"
            @keydown.enter.exact.prevent="handleSend"
          />
          <el-button type="primary" :disabled="!inputText.trim() || isLoading" @click="handleSend" class="send-btn">
            <el-icon v-if="isLoading" class="is-loading"><Loading /></el-icon>
            <el-icon v-else><Promotion /></el-icon>
          </el-button>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, computed, onBeforeUnmount, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import {
  streamAiAgentMessage,
  generateSessionId,
  clearAiAgentSession,
  checkAiAgentHealth,
  getAiAgentHistory,
  submitAiFeedback,
  getTransferStatus,
  type AiAgentMessage
} from '@/api/ai-agent'
import { Monitor, Delete, Close, Promotion, Loading, WarningFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const userStore = useUserStore()
const router = useRouter()

// --- State ---
const isOpen = ref(false)
const messages = ref<(AiAgentMessage & { feedback?: 'up' | 'down'; feedbackSubmitting?: boolean; isSystem?: boolean; source?: 'human' | 'ai' })[]>([])
const inputText = ref('')
const isLoading = ref(false)
const messagesRef = ref<HTMLElement>()
const isServiceAvailable = ref(true)
// 转人工状态：none / pending / accepted（控制 UI 提示条 + 输入框文案）
const transferStatus = ref<'none' | 'pending' | 'accepted'>('none')
const isChecking = ref(false)
const isMobile = ref(window.innerWidth <= 768)
let currentController: AbortController | null = null
let currentSessionId: string | null = null
let transferWaitController: AbortController | null = null
// 主动断开标志：watch(isOpen=false) / 切账号 / 状态变 none 时置 true，
// 防止 SSE 断开后 finally 块无限重连
let isManualDisconnect = true
// 转人工状态轮询 timer：兜底感知转人工状态变化（用户可能没开聊天窗）
let transferPollTimer: ReturnType<typeof setTimeout> | null = null
// 轮询间隔：无转人工时 15s（省请求），pending/accepted 时 5s（快感知）
const POLL_IDLE_MS = 15000
const POLL_ACTIVE_MS = 5000

async function ensureSessionId(): Promise<string> {
  if (currentSessionId) return currentSessionId
  if (!userStore.userInfo?.id) {
    await userStore.getUserInfo()
  }
  const uid = userStore.userInfo?.id
  if (!uid) throw new Error('无法获取用户信息，请重新登录')
  currentSessionId = generateSessionId(uid)
  return currentSessionId
}

const quickQuestions = ['你好', '有什么功能？']

// --- Position & Drag ---
const posX = ref(window.innerWidth - 80)
const posY = ref(window.innerHeight - 80)
const isDragging = ref(false)
let dragOffsetX = 0
let dragOffsetY = 0
let hasMoved = false

const fabStyle = computed(() => ({
  left: `${posX.value}px`,
  top: `${posY.value}px`
}))

const windowWidth = 380
const windowHeight = 520

const windowStyle = computed(() => {
  if (isMobile.value) {
    return {} // CSS handles mobile positioning
  }
  let x = posX.value - windowWidth + 60
  let y = posY.value - windowHeight - 10
  x = Math.max(8, Math.min(x, window.innerWidth - windowWidth - 8))
  y = Math.max(8, Math.min(y, window.innerHeight - windowHeight - 8))
  return { left: `${x}px`, top: `${y}px` }
})

// --- Responsive ---
function onResize() {
  isMobile.value = window.innerWidth <= 768
}
window.addEventListener('resize', onResize)

// --- Health check ---
async function checkHealth() {
  isChecking.value = true
  try {
    const result = await checkAiAgentHealth()
    isServiceAvailable.value = result.available
    if (!result.redisAvailable) {
      console.warn('[AiCS] AI Agent 在线但 Redis 不可用，历史记录可能无法加载')
    }
  } finally {
    isChecking.value = false
  }
}

async function loadHistory() {
  console.log('[AiCS] loadHistory() 开始执行')
  try {
    const sid = await ensureSessionId()
    console.log('[AiCS] sessionId =', sid)
    
    const data = await getAiAgentHistory(sid)
    console.log('[AiCS] API 原始返回:', JSON.stringify(data))
    
    messages.value = (data.messages || []).map(m => ({
      role: m.role as 'user' | 'assistant',
      content: m.content,
      timestamp: Number(m.timestamp) * 1000
    }))
    console.log(`[AiCS] messages.value 已设置, 数量=${messages.value.length}`)
    
    if (messages.value.length > 0) {
      // 历史加载成功 = 服务肯定可用，反哺健康状态
      if (!isServiceAvailable.value) {
        console.log('[AiCS] health check 误判为不可用，已根据历史记录加载成功修正')
        isServiceAvailable.value = true
      }
      scrollToBottom()
    }
  } catch (err) {
    console.error('[AiCS] 加载历史记录失败:', err)
    messages.value = []
  }
}

// 连接 /chat/transfer-wait SSE 长连接，接收管理员消息（Pub/Sub 推送）
async function connectTransferStream() {
  if (transferWaitController) return
  isManualDisconnect = false
  try {
    const sid = await ensureSessionId()
    const tk = userStore.token || ''
    transferWaitController = new AbortController()
    // 后端 ai-agent 端点用 query token；Gateway 全局 JWT 用 Authorization 头
    const url = `${import.meta.env.VITE_AI_AGENT_URL ?? 'http://localhost:8000'}/chat/transfer-wait?session_id=${encodeURIComponent(sid)}&token=${encodeURIComponent(tk)}`
    const headers: Record<string, string> = {}
    if (tk) headers['Authorization'] = `Bearer ${tk}`
    const resp = await fetch(url, { signal: transferWaitController.signal, headers })
    const reader = resp.body?.getReader()
    if (!reader) return
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
          const data = JSON.parse(line.slice(6))
          if (data.content) {
            const msgTs = Number(data.timestamp ?? 0) * 1000 || Date.now()
            // 严格去重（timestamp + content），防止重连 / 历史补齐 / 重复推送
            const exists = messages.value.some(m => m.content === data.content && Number(m.timestamp ?? 0) === msgTs)
            if (!exists) {
              messages.value.push({
                role: 'assistant',
                content: data.content,
                timestamp: msgTs,
                source: 'human',   // 标识为人工客服消息（区别于 AI）
              })
              scrollToBottom()
            }
          }
          if (data.done) {
            transferWaitController = null
            return
          }
        } catch { /* ignore */ }
      }
    }
  } catch { /* ignore abort */ }
  transferWaitController = null
  // 异常断开：仅在非主动断开时 1s 重连
  if (!isManualDisconnect) {
    setTimeout(() => connectTransferStream(), 1000)
  }
}

function disconnectTransferStream() {
  isManualDisconnect = true
  if (transferWaitController) {
    transferWaitController.abort()
    transferWaitController = null
  }
}

// 检查转人工状态；处于 pending/accepted 时建立 SSE 连接
// 同时作为定时轮询的入口，根据状态自适应调整下次轮询间隔
async function checkTransfer() {
  if (!userStore.userInfo?.id) {
    scheduleNextPoll(POLL_IDLE_MS)
    return
  }
  try {
    const r = await getTransferStatus(userStore.userInfo.id)
    const s = (r.status as any) || 'none'
    transferStatus.value = s
    if (s === 'pending' || s === 'accepted') {
      // 转人工中：建立 SSE 实时通道，并用较短间隔轮询兜底
      if (!transferWaitController) connectTransferStream()
      scheduleNextPoll(POLL_ACTIVE_MS)
    } else {
      // 无转人工：断开 SSE，拉长轮询间隔
      disconnectTransferStream()
      scheduleNextPoll(POLL_IDLE_MS)
    }
  } catch {
    // 静默失败，按较慢间隔重试
    scheduleNextPoll(POLL_IDLE_MS)
  }
}

// 自适应调度下次轮询（避免多个 timer 叠加）
function scheduleNextPoll(ms: number) {
  if (transferPollTimer) clearTimeout(transferPollTimer)
  transferPollTimer = setTimeout(() => checkTransfer(), ms)
}

watch(isOpen, async (val) => {
  console.log(`[AiCS] isOpen 变化: ${val}, 即将调用 ${val ? 'checkHealth+loadHistory+checkTransfer' : '(关闭)'}`)
  if (val) {
    checkHealth()
    await loadHistory()
    await checkTransfer()
  } else {
    disconnectTransferStream()
  }
})

watch(() => userStore.userInfo?.id, (newId, oldId) => {
  if (newId !== oldId) {
    currentSessionId = null
    messages.value = []
    if (isOpen.value) loadHistory()
  }
})

// --- Drag ---
function onDragStart(e: MouseEvent) {
  if (e.button !== 0 || isMobile.value) return
  isDragging.value = true
  hasMoved = false
  const target = isOpen.value
    ? (e.currentTarget as HTMLElement).closest('.ai-cs-window')
    : (e.currentTarget as HTMLElement)
  if (!target) return
  const rect = target.getBoundingClientRect()
  dragOffsetX = e.clientX - rect.left
  dragOffsetY = e.clientY - rect.top

  const onMouseMove = (ev: MouseEvent) => {
    hasMoved = true
    if (!isOpen.value) {
      posX.value = ev.clientX - dragOffsetX
      posY.value = ev.clientY - dragOffsetY
    } else {
      const winEl = document.querySelector('.ai-cs-window') as HTMLElement
      if (winEl) {
        const wRect = winEl.getBoundingClientRect()
        const dx = ev.clientX - (wRect.left + dragOffsetX)
        const dy = ev.clientY - (wRect.top + dragOffsetY)
        posX.value += dx
        posY.value += dy
      }
    }
  }

  const onMouseUp = () => {
    isDragging.value = false
    // 重置 hasMoved，避免微小鼠标移动导致下次 toggleOpen 被跳过
    setTimeout(() => { hasMoved = false }, 0)
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', onMouseUp)
    posX.value = Math.max(0, Math.min(posX.value, window.innerWidth - 60))
    posY.value = Math.max(0, Math.min(posY.value, window.innerHeight - 60))
  }

  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}

function onTouchStart(e: TouchEvent) {
  if (isMobile.value) return // mobile uses CSS positioning
  // Simulate drag for touch
  const touch = e.touches[0]
  const mouseEvent = new MouseEvent('mousedown', {
    clientX: touch.clientX,
    clientY: touch.clientY,
    button: 0
  })
  onDragStart(mouseEvent)
}

function toggleOpen() {
  if (hasMoved) return
  isOpen.value = !isOpen.value
  if (isOpen.value) {
    nextTick(() => scrollToBottom())
  }
}

// --- Chat ---
function scrollToBottom() {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

const renderMarkdown = (text: string): string => {
  if (!text) return ''
  return text
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="ai-chat-link">$1</a>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
}

function onMessageClick(e: MouseEvent) {
  const target = e.target as HTMLElement
  if (target.classList.contains('ai-chat-link')) {
    e.preventDefault()
    const href = target.getAttribute('href')
    if (href) {
      router.push(href)
    }
  }
}

async function handleSend() {
  const text = inputText.value.trim()
  if (!text || isLoading.value) return

  messages.value.push({ role: 'user', content: text, timestamp: Date.now() })
  inputText.value = ''
  isLoading.value = true
  scrollToBottom()

  const sessionId = await ensureSessionId()
  const token = userStore.token || undefined

  const aiMsg: AiAgentMessage = { role: 'assistant', content: '', timestamp: Date.now() }
  messages.value.push(aiMsg)
  const aiIdx = messages.value.length - 1
  let transferDetected = false

  currentController = streamAiAgentMessage(
    text,
    sessionId,
    token,
    (chunk: string) => {
      messages.value[aiIdx].content += chunk
      // 检测转人工标记：后端 transfer_tool 实际返回"转接单号: xxx"字样
      if (messages.value[aiIdx].content.includes('转接单号')) {
        transferDetected = true
      }
      // 检测人工通道标记：转人工期间后端返回 [HUMAN_TRANSFER] 前缀
      if (messages.value[aiIdx].content.includes('[HUMAN_TRANSFER]')) {
        messages.value[aiIdx].source = 'human'
        messages.value[aiIdx].content = messages.value[aiIdx].content.replace('[HUMAN_TRANSFER]', '').trim()
      }
      scrollToBottom()
    },
    (_sid: string, humanTransfer?: boolean) => {
      isLoading.value = false
      currentController = null
      if (humanTransfer) {
        // 转人工阻断：后端未产生 AI 回复，移除占位气泡，不补兜底文案。
        // 用户消息已由后端写入会话历史并通过 transfer-wait SSE 转发给人工客服。
        messages.value.splice(aiIdx, 1)
        checkTransfer()
        return
      }
      if (transferDetected) {
        // 显示转人工系统消息
        messages.value.push({
          role: 'assistant',
          content: '正在为您转接人工客服，请稍候...',
          timestamp: Date.now()
        })
        // 立即触发 SSE 连接建立 + 加快轮询，不再等用户开关聊天窗
        checkTransfer()
      } else if (!messages.value[aiIdx].content) {
        messages.value[aiIdx].content = '抱歉，我暂时无法回答这个问题。'
      }
      scrollToBottom()
    },
    (error: Error) => {
      isLoading.value = false
      currentController = null
      messages.value[aiIdx].content = `请求失败：${error.message}`
      scrollToBottom()
    }
  )
}

function sendQuick(q: string) {
  inputText.value = q
  handleSend()
}

// A4: 提交用户反馈
async function submitFeedback(msgIdx: number, rating: 'up' | 'down') {
  const msg = messages.value[msgIdx]
  if (!msg || msg.feedbackSubmitting) return

  // 如果已点相同的就取消
  const newRating = msg.feedback === rating ? undefined : rating
  msg.feedbackSubmitting = true

  try {
    const sid = await ensureSessionId()
    await submitAiFeedback({
      session_id: sid,
      rating: rating,
      message_content: msg.content,
      token: userStore.token || undefined
    })
    msg.feedback = newRating
    if (newRating) {
      ElMessage.success(rating === 'up' ? '感谢您的认可！' : '感谢反馈，我们会持续改进')
    }
  } catch {
    // 静默失败，用户无感知
  } finally {
    msg.feedbackSubmitting = false
  }
}

async function clearChat() {
  if (currentController) {
    currentController.abort()
    currentController = null
  }
  isLoading.value = false
  messages.value = []
  try {
    if (currentSessionId) {
      await clearAiAgentSession(currentSessionId)
    }
    ElMessage.success('对话已清空')
  } catch {
    // ignore
  }
}

onMounted(() => {
  // 启动转人工状态轮询（兜底感知，即使聊天窗未开也能检测到状态变化）
  // 首次延迟 3s 启动，避开页面加载高峰
  transferPollTimer = setTimeout(() => checkTransfer(), 3000)
})

onBeforeUnmount(() => {
  isDragging.value = false
  if (currentController) {
    currentController.abort()
    currentController = null
  }
  disconnectTransferStream()
  // 清理转人工轮询 timer
  if (transferPollTimer) {
    clearTimeout(transferPollTimer)
    transferPollTimer = null
  }
  window.removeEventListener('resize', onResize)
})
</script>

<style scoped lang="scss">
.ai-cs-container {
  position: fixed;
  z-index: 9999;
  pointer-events: none;
}

.ai-cs-fab {
  position: fixed;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--accent), var(--accent-dark));
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(78, 205, 196, 0.3);
  transition: transform 0.2s, box-shadow 0.2s;
  pointer-events: auto;
  user-select: none;

  &:hover {
    transform: scale(1.1);
    box-shadow: 0 6px 24px rgba(78, 205, 196, 0.4);

    .fab-tooltip {
      opacity: 1;
      transform: translateX(-100%) translateY(-50%) translateX(-12px);
    }
  }

  .fab-tooltip {
    position: absolute;
    right: 68px;
    top: 50%;
    transform: translateX(-100%) translateY(-50%) translateX(0);
    background: var(--text-primary);
    color: #fff;
    padding: 6px 12px;
    border-radius: var(--radius-sm);
    font-size: 13px;
    white-space: nowrap;
    opacity: 0;
    transition: all 0.2s;
    pointer-events: none;
  }
}

.ai-cs-window {
  position: fixed;
  width: 380px;
  height: 520px;
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  box-shadow: 0 8px 32px rgba(45, 42, 51, 0.15);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  pointer-events: auto;
  user-select: none;
}

/* Mobile: full screen */
.ai-cs-mobile {
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  bottom: 0 !important;
  width: 100% !important;
  height: 100% !important;
  border-radius: 0 !important;
}

.ai-cs-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: linear-gradient(135deg, var(--accent-dark), var(--accent));
  color: var(--text-inverse);
  cursor: move;
  flex-shrink: 0;

  .header-left {
    display: flex;
    align-items: center;
    gap: 10px;

    .ai-avatar {
      background: rgba(255, 255, 255, 0.2);
      color: #fff;
    }

    .header-title {
      font-size: 15px;
      font-weight: 600;
    }
  }

  .header-actions {
    display: flex;
    gap: 12px;

    .action-icon {
      cursor: pointer;
      opacity: 0.8;
      transition: opacity 0.2s;
      font-size: 18px;

      &:hover {
        opacity: 1;
      }
    }
  }
}

.ai-cs-unavailable {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 40px;
  color: var(--text-muted);

  p {
    font-size: 14px;
    margin: 0;
  }
}

.ai-cs-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  background: var(--bg-page);
  -webkit-overflow-scrolling: touch;
}

.welcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 16px 20px;

  p {
    margin: 12px 0 20px;
    font-size: 14px;
    color: var(--text-muted);
  }

  .quick-questions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: center;

    .quick-tag {
      padding: 6px 14px;
      background: var(--bg-card);
      border: 1px solid var(--border-light);
      border-radius: var(--radius-full);
      font-size: 13px;
      color: var(--text-secondary);
      cursor: pointer;
      transition: all var(--transition-fast);

      &:hover {
        border-color: var(--primary-light);
        color: var(--primary);
        background: var(--primary-bg);
      }
    }
  }
}

.msg-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 14px;

  &.user {
    justify-content: flex-end;
  }

  .msg-ai-avatar {
    flex-shrink: 0;
    background: var(--bg-card);
    color: #fff;
  }

  // 人工客服头像（区别于 AI）
  .msg-human-avatar {
    flex-shrink: 0;
    background: #e6a23c;
    color: #fff;
  }

  // 人工客服来源标签
  .msg-source-tag {
    font-size: 11px;
    color: #e6a23c;
    padding: 0 0 2px 4px;
    font-weight: 500;
  }

  // 人工客服气泡（暖色调，区别于 AI 的冷色调）
  .human-bubble {
    background: #fdf6ec !important;
    border: 1px solid #f5dab1;
    color: #7a5c2e;
  }

  // 转人工顶部提示条
  .transfer-banner {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    margin-bottom: 8px;
    background: linear-gradient(90deg, #fdf6ec, #fef0f0);
    border: 1px solid #f5dab1;
    border-radius: 8px;
    font-size: 12px;
    color: #e6a23c;
    text-align: center;
    justify-content: center;
    animation: pulse-banner 2s ease-in-out infinite;
  }

  @keyframes pulse-banner {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
  }

  .msg-bubble-wrapper {
    max-width: 75%;
    display: flex;
    flex-direction: column;
  }
}

// A4: 反馈按钮
.msg-feedback {
  display: flex;
  gap: 6px;
  padding: 4px 0 0 4px;
  opacity: 0;
  transition: opacity 0.2s;
}

.msg-row:hover .msg-feedback {
  opacity: 1;
}

.fb-btn {
  background: transparent;
  border: none;
  font-size: 14px;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
  transition: all 0.2s;
  opacity: 0.6;
  line-height: 1;

  &:hover:not(:disabled) {
    opacity: 1;
    background: var(--bg-deep);
  }

  &.active {
    opacity: 1;
    background: var(--bg-deep);
  }

  &:disabled {
    cursor: not-allowed;
    opacity: 0.3;
  }
}

.msg-bubble {
  max-width: 75%;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.6;
  word-break: break-word;

  .msg-text {
    :deep(pre) {
      background: #1e1e1e;
      color: #d4d4d4;
      padding: 10px;
      border-radius: 6px;
      overflow-x: auto;
      margin: 6px 0;
      font-size: 12px;
    }
    :deep(code) {
      background: var(--bg-deep);
      padding: 2px 5px;
      border-radius: 3px;
      font-size: 12px;
      color: var(--accent);
    }
    :deep(strong) {
      font-weight: 600;
    }
    :deep(a) {
      color: var(--primary);
      text-decoration: none;
      font-weight: 500;
      &:hover {
        text-decoration: underline;
        color: var(--primary-dark);
      }
    }
  }
}

.ai-bubble {
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-top-left-radius: 4px;
  color: var(--text-primary);
}

.user-bubble {
  background: var(--accent);
  color: var(--text-inverse);
  border-top-right-radius: 4px;
}

.typing-dots {
  display: flex;
  gap: 4px;
  padding: 4px 0;

  span {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--text-muted);
    animation: dotPulse 1.4s infinite ease-in-out both;
    &:nth-child(1) { animation-delay: 0s; }
    &:nth-child(2) { animation-delay: 0.2s; }
    &:nth-child(3) { animation-delay: 0.4s; }
  }
}

@keyframes dotPulse {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

.ai-cs-input {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 12px;
  border-top: 1px solid var(--border-light);
  background: var(--bg-card);
  flex-shrink: 0;

  :deep(.el-textarea__inner) {
    resize: none;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
  }

  .send-btn {
    height: 36px;
    width: 36px;
    border-radius: 8px;
    flex-shrink: 0;
    padding: 0;
  }
}

/* Mobile adjustments */
@media (max-width: 768px) {
  .ai-cs-fab {
    width: 50px;
    height: 50px;

    .el-icon {
      font-size: 24px;
    }

    .fab-tooltip {
      display: none;
    }
  }

  .msg-bubble {
    max-width: 85%;
  }

  .welcome {
    padding: 24px 16px 16px;

    .quick-questions {
      .quick-tag {
        padding: 8px 16px;
        font-size: 14px;
      }
    }
  }
}

// Transition
.ai-cs-pop-enter-active,
.ai-cs-pop-leave-active {
  transition: all 0.25s ease;
}
.ai-cs-pop-enter-from,
.ai-cs-pop-leave-to {
  opacity: 0;
  transform: scale(0.9) translateY(10px);
}

@media (max-width: 768px) {
  .ai-cs-pop-enter-from,
  .ai-cs-pop-leave-to {
    transform: translateY(100%);
  }
}
</style>
