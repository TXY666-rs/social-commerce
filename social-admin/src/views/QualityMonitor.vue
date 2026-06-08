<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import {
  getEvalRealtime,
  getEvalTraces,
  getEvalReport,
  runEval,
  type EvalRealtimeData,
  type EvalTrace,
  type EvalReport,
} from '@/api/ai-agent'
import { ElMessage } from 'element-plus'

// ── 实时质量监控 ──
const realtimeData = ref<EvalRealtimeData | null>(null)
const realtimeLoading = ref(false)

// ── 请求链路 ──
const traces = ref<EvalTrace[]>([])
const tracesLoading = ref(false)

// ── 离线评估 ──
const evalReport = ref<EvalReport | null>(null)
const evalRunning = ref(false)
const showReportDialog = ref(false)

// ── 自动刷新 ──
const autoRefresh = ref(true)
let pollTimer: ReturnType<typeof setInterval> | null = null

const activeTab = ref('overview')

const routeSourceLabel: Record<string, string> = {
  keyword: '关键词匹配',
  llm: 'LLM路由',
  clarification: '澄清追问',
  faq: 'FAQ快捷回复',
  active_skill: '活跃Skill',
  skill: 'Skill触发',
  purchase_intent: '购买意向',
  unknown: '未知',
}

const routeColors: Record<string, string> = {
  keyword: '#4ECDC4',
  llm: '#667eea',
  clarification: '#E8C468',
  faq: '#B8E186',
  safety: '#E86A6A',
}

const agentColors: Record<string, string> = {
  orders_agent: '#4ECDC4',
  product_agent: '#667eea',
  after_sale_agent: '#E8C468',
  coupon_agent: '#B8E186',
  transfer_agent: '#E86A6A',
  unknown: '#6B7280',
}

const skillColors: Record<string, string> = {
  return_item: '#4ECDC4',
  cancel_refund: '#E86A6A',
  refund_status: '#667eea',
  modify_order: '#E8C468',
  complaint: '#FF8C42',
  product_query: '#B8E186',
  transfer_to_human: '#C084FC',
  track_order: '#60A5FA',
}

const skillLabel: Record<string, string> = {
  return_item: '退货退款',
  cancel_refund: '取消退款',
  refund_status: '退款进度查询',
  modify_order: '订单修改',
  complaint: '投诉',
  product_query: '商品/优惠券查询',
  transfer_to_human: '转人工',
  track_order: '订单/物流查询',
}

// ── 数据获取 ──
async function fetchRealtime() {
  realtimeLoading.value = true
  try {
    realtimeData.value = await getEvalRealtime()
  } catch {
    // 静默
  } finally {
    realtimeLoading.value = false
  }
}

async function fetchTraces() {
  tracesLoading.value = true
  try {
    traces.value = await getEvalTraces(30)
  } catch {
    // 静默
  } finally {
    tracesLoading.value = false
  }
}

async function fetchAll() {
  await Promise.all([fetchRealtime(), fetchTraces()])
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(() => {
    if (autoRefresh.value) fetchAll()
  }, 10000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function toggleAutoRefresh() {
  autoRefresh.value = !autoRefresh.value
  if (autoRefresh.value) {
    fetchAll()
    startPolling()
  } else {
    stopPolling()
  }
}

// ── 计算属性 ──
const routeEntries = computed(() => {
  if (!realtimeData.value) return []
  const total = Object.values(realtimeData.value.route_distribution).reduce((a, b) => a + b, 0)
  return Object.entries(realtimeData.value.route_distribution)
    .map(([name, count]) => ({
      name,
      count,
      pct: total > 0 ? (count / total * 100).toFixed(1) : '0',
      color: routeColors[name] || '#6B7280',
    }))
    .sort((a, b) => b.count - a.count)
})

const agentEntries = computed(() => {
  if (!realtimeData.value) return []
  const total = Object.values(realtimeData.value.agent_distribution).reduce((a, b) => a + b, 0)
  return Object.entries(realtimeData.value.agent_distribution)
    .map(([name, count]) => ({
      name,
      count,
      pct: total > 0 ? (count / total * 100).toFixed(1) : '0',
      color: agentColors[name] || '#6B7280',
    }))
    .sort((a, b) => b.count - a.count)
})

const skillEntries = computed(() => {
  if (!realtimeData.value?.skill_distribution) return []
  const dist = realtimeData.value.skill_distribution
  const total = Object.values(dist).reduce((a, b) => a + b, 0)
  return Object.entries(dist)
    .map(([name, count]) => ({
      name,
      count,
      pct: total > 0 ? (count / total * 100).toFixed(1) : '0',
      color: skillColors[name] || '#6B7280',
      label: skillLabel[name] || name,
    }))
    .sort((a, b) => b.count - a.count)
})

const skillTotal = computed(() => {
  return skillEntries.value.reduce((sum, e) => sum + e.count, 0)
})

const safetyEntries = computed(() => {
  if (!realtimeData.value) return []
  return Object.entries(realtimeData.value.safety_events)
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count)
})

// ── 离线评估 ──
async function handleRunEval() {
  evalRunning.value = true
  try {
    const res = await runEval()
    ElMessage.success(res.message || '评估完成')
    await loadEvalReport()
  } catch (e: any) {
    ElMessage.error(e.message || '评估失败')
  } finally {
    evalRunning.value = false
  }
}

async function loadEvalReport() {
  try {
    evalReport.value = await getEvalReport()
  } catch {
    evalReport.value = null
  }
}

function viewReport() {
  showReportDialog.value = true
  loadEvalReport()
}

// ── 工具函数 ──
function fmtNum(n: number): string {
  if (n >= 10000) return (n / 10000).toFixed(1) + 'w'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'k'
  return String(n)
}

function fmtMs(v: number): string {
  if (v === undefined || v === null) return '-'
  return Math.round(v) + 'ms'
}

function fmtTokens(input: number, output: number): string {
  if (!input && !output) return '-'
  return `${input} / ${output}`
}

const routeTagType = (source: string) => {
  if (source === 'keyword') return 'success'
  if (source === 'llm') return ''
  if (source === 'faq') return 'info'
  return 'warning'
}

onMounted(() => {
  fetchAll()
  startPolling()
  loadEvalReport()
})

onUnmounted(stopPolling)
</script>

<template>
  <div class="quality-page">
    <!-- 顶部操作栏 -->
    <div class="action-bar">
      <div class="action-left">
        <span class="page-desc">实时监控 AI 客服质量，每 10 秒自动刷新</span>
      </div>
      <div class="action-right">
        <el-switch v-model="autoRefresh" active-text="自动刷新" @change="toggleAutoRefresh" />
        <el-button @click="fetchAll" :loading="realtimeLoading || tracesLoading" size="small">手动刷新</el-button>
        <el-divider direction="vertical" />
        <el-button @click="handleRunEval" :loading="evalRunning" size="small" type="warning">
          运行离线评估
        </el-button>
        <el-button @click="viewReport" size="small" :disabled="!evalReport">查看评估报告</el-button>
      </div>
    </div>

    <!-- Tab 切换 -->
    <el-tabs v-model="activeTab" class="quality-tabs">
      <!-- ═══ Tab 1: 实时概览 ═══ -->
      <el-tab-pane label="实时概览" name="overview">
        <div v-if="realtimeData">
          <!-- 概览卡片 -->
          <el-row :gutter="16" class="overview-row">
            <el-col :span="4">
              <div class="stat-card">
                <div class="stat-label">今日请求</div>
                <div class="stat-value accent">{{ realtimeData.summary.total_requests }}</div>
              </div>
            </el-col>
            <el-col :span="4">
              <div class="stat-card">
                <div class="stat-label">平均路由耗时</div>
                <div class="stat-value">{{ realtimeData.summary.avg_routing_ms }}ms</div>
              </div>
            </el-col>
            <el-col :span="4">
              <div class="stat-card">
                <div class="stat-label">平均总耗时</div>
                <div class="stat-value">{{ realtimeData.summary.avg_total_ms }}ms</div>
              </div>
            </el-col>
            <el-col :span="4">
              <div class="stat-card">
                <div class="stat-label">输入 Token</div>
                <div class="stat-value info">{{ fmtNum(realtimeData.summary.total_input_tokens) }}</div>
              </div>
            </el-col>
            <el-col :span="4">
              <div class="stat-card">
                <div class="stat-label">输出 Token</div>
                <div class="stat-value info">{{ fmtNum(realtimeData.summary.total_output_tokens) }}</div>
              </div>
            </el-col>
            <el-col :span="4">
              <div class="stat-card token-card">
                <div class="stat-label">总 Token</div>
                <div class="stat-value token-big">{{ fmtNum(realtimeData.summary.total_tokens) }}</div>
              </div>
            </el-col>
          </el-row>

          <!-- 路由分布 + Agent 分布 + Skill 命中 + 安全事件 -->
          <el-row :gutter="16" style="margin-top: 16px;">
            <el-col :span="6">
              <el-card shadow="hover">
                <template #header><span>路由来源分布</span></template>
                <div class="dist-list" v-if="routeEntries.length">
                  <div v-for="item in routeEntries" :key="item.name" class="dist-item">
                    <div class="dist-left">
                      <span class="dist-dot" :style="{ background: item.color }"></span>
                      <span class="dist-name">{{ routeSourceLabel[item.name] || item.name }}</span>
                    </div>
                    <div class="dist-right">
                      <span class="dist-count">{{ item.count }}</span>
                      <span class="dist-pct">{{ item.pct }}%</span>
                    </div>
                  </div>
                </div>
                <div v-else class="empty-hint">暂无数据</div>
              </el-card>
            </el-col>

            <el-col :span="6">
              <el-card shadow="hover">
                <template #header><span>Agent 类型分布</span></template>
                <div class="dist-list" v-if="agentEntries.length">
                  <div v-for="item in agentEntries" :key="item.name" class="dist-item">
                    <div class="dist-left">
                      <span class="dist-dot" :style="{ background: item.color }"></span>
                      <span class="dist-name">{{ item.name }}</span>
                    </div>
                    <div class="dist-right">
                      <span class="dist-count">{{ item.count }}</span>
                      <span class="dist-pct">{{ item.pct }}%</span>
                    </div>
                  </div>
                </div>
                <div v-else class="empty-hint">暂无数据</div>
              </el-card>
            </el-col>

            <el-col :span="6">
              <el-card shadow="hover">
                <template #header>
                  <div class="card-header-with-badge">
                    <span>Skill 命中分布</span>
                    <el-tag v-if="skillTotal" size="small" type="info">{{ skillTotal }} 次</el-tag>
                  </div>
                </template>
                <div class="dist-list" v-if="skillEntries.length">
                  <div v-for="item in skillEntries" :key="item.name" class="dist-item">
                    <div class="dist-left">
                      <span class="dist-dot" :style="{ background: item.color }"></span>
                      <span class="dist-name">{{ item.label }}</span>
                    </div>
                    <div class="dist-right">
                      <span class="dist-count">{{ item.count }}</span>
                      <span class="dist-pct">{{ item.pct }}%</span>
                    </div>
                  </div>
                </div>
                <div v-else class="empty-hint">暂无 Skill 触发</div>
              </el-card>
            </el-col>

            <el-col :span="6">
              <el-card shadow="hover">
                <template #header><span>安全事件</span></template>
                <div class="dist-list" v-if="safetyEntries.length">
                  <div v-for="item in safetyEntries" :key="item.name" class="dist-item">
                    <div class="dist-left">
                      <span class="dist-dot danger"></span>
                      <span class="dist-name">{{ item.name }}</span>
                    </div>
                    <div class="dist-right">
                      <span class="dist-count danger">{{ item.count }}</span>
                    </div>
                  </div>
                </div>
                <div v-else class="empty-hint safe">无安全事件</div>
              </el-card>
            </el-col>
          </el-row>

          <!-- 最近请求明细 -->
          <el-card shadow="hover" style="margin-top: 16px;">
            <template #header>
              <span>最近请求明细 ({{ realtimeData.recent_requests.length }})</span>
            </template>
            <el-table :data="realtimeData.recent_requests" size="small" stripe max-height="400" style="width: 100%">
              <el-table-column prop="time" label="时间" width="80" />
              <el-table-column prop="user_id" label="用户" width="80" />
              <el-table-column label="路由来源" width="110">
                <template #default="{ row }">
                  <el-tag size="small" :type="routeTagType(row.route_source)">
                    {{ routeSourceLabel[row.route_source] || row.route_source }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="agent_type" label="Agent" width="120" />
              <el-table-column label="Skill" width="110">
                <template #default="{ row }">
                  <el-tag v-if="row.skill_name" size="small" :color="skillColors[row.skill_name]" style="color: #fff; border: none;">
                    {{ skillLabel[row.skill_name] || row.skill_name }}
                  </el-tag>
                  <span v-else class="text-ghost">-</span>
                </template>
              </el-table-column>
              <el-table-column label="路由耗时" width="90" align="right">
                <template #default="{ row }">{{ row.routing_ms }}ms</template>
              </el-table-column>
              <el-table-column label="总耗时" width="90" align="right" sortable sort-by="total_ms">
                <template #default="{ row }">{{ row.total_ms }}ms</template>
              </el-table-column>
              <el-table-column label="Token (入/出)" width="110" align="right">
                <template #default="{ row }">{{ row.input_tokens }} / {{ row.output_tokens }}</template>
              </el-table-column>
              <el-table-column label="工具调用" min-width="150">
                <template #default="{ row }">
                  <template v-if="row.tools_called?.length">
                    <el-tag v-for="t in row.tools_called" :key="t" size="small" type="info" class="tool-tag">{{ t }}</el-tag>
                  </template>
                  <span v-else class="text-ghost">-</span>
                </template>
              </el-table-column>
              <el-table-column label="FAQ" width="50" align="center">
                <template #default="{ row }">
                  <el-tag v-if="row.is_faq" size="small" type="success">FAQ</el-tag>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </div>

        <div v-else-if="!realtimeLoading">
          <el-card shadow="hover">
            <div class="empty-content">
              <span>📊 AI 客服服务未连接或暂无请求数据</span>
              <p class="sub">当用户发起对话后，实时质量数据会自动出现在这里</p>
            </div>
          </el-card>
        </div>
      </el-tab-pane>

      <!-- ═══ Tab 2: 请求链路 ═══ -->
      <el-tab-pane label="请求链路" name="traces">
        <div class="trace-list" v-if="traces.length">
          <div v-for="(trace, idx) in traces" :key="idx" class="trace-card">
            <div class="trace-header">
              <div class="trace-left">
                <span class="trace-time">{{ trace.time }}</span>
                <el-tag :type="routeTagType(trace.route_source)" size="small">
                  {{ routeSourceLabel[trace.route_source] || trace.route_source }}
                </el-tag>
                <el-tag type="info" size="small">{{ trace.agent_type }}</el-tag>
                <el-tag v-if="trace.skill_name" size="small" :color="skillColors[trace.skill_name]" style="color: #fff; border: none;">
                  {{ skillLabel[trace.skill_name] || trace.skill_name }}
                </el-tag>
                <el-tag v-if="trace.is_faq" type="success" size="small">FAQ</el-tag>
              </div>
              <div class="trace-right">
                <span class="trace-user">用户 #{{ trace.user_id }}</span>
              </div>
            </div>
            <div class="trace-grid">
              <div class="grid-cell">
                <div class="cell-label">路由耗时</div>
                <div class="cell-value">{{ fmtMs(trace.routing_ms) }}</div>
              </div>
              <div class="grid-cell">
                <div class="cell-label">总耗时</div>
                <div class="cell-value" :class="trace.total_ms > 3000 ? 'warn' : trace.total_ms > 1000 ? 'info' : ''">
                  {{ fmtMs(trace.total_ms) }}
                </div>
              </div>
              <div class="grid-cell">
                <div class="cell-label">Token (入/出)</div>
                <div class="cell-value mono">{{ fmtTokens(trace.input_tokens, trace.output_tokens) }}</div>
              </div>
              <div class="grid-cell wide">
                <div class="cell-label">工具调用</div>
                <div class="cell-value">
                  <template v-if="trace.tools_called?.length">
                    <el-tag v-for="tool in trace.tools_called" :key="tool" size="small" type="info" class="tool-tag">
                      {{ tool }}
                    </el-tag>
                  </template>
                  <span v-else class="no-tool">无</span>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div v-else-if="!tracesLoading">
          <el-card shadow="hover">
            <div class="empty-content">
              <p>暂无请求链路数据</p>
              <p class="sub">用户发起对话后，每次请求的完整链路会自动出现在这里</p>
            </div>
          </el-card>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 离线评估报告弹窗 -->
    <el-dialog v-model="showReportDialog" title="离线评估报告" width="800px" top="5vh">
      <div v-if="evalReport">
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="生成时间">{{ evalReport.generated_at }}</el-descriptions-item>
          <el-descriptions-item label="总用例数">{{ evalReport.summary.total }}</el-descriptions-item>
          <el-descriptions-item label="通过数">{{ evalReport.summary.passed }}</el-descriptions-item>
          <el-descriptions-item label="端到端准确率">
            <el-tag :type="evalReport.summary.accuracy >= 0.8 ? 'success' : 'warning'">
              {{ (evalReport.summary.accuracy * 100).toFixed(1) }}%
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="平均延迟">
            {{ evalReport.summary.avg_latency_ms.toFixed(0) }}ms
          </el-descriptions-item>
          <el-descriptions-item label="工具调用正确率">
            {{ (evalReport.summary.tool_call_accuracy * 100).toFixed(1) }}%
          </el-descriptions-item>
          <el-descriptions-item label="任务完成率">
            {{ (evalReport.summary.task_completion_rate * 100).toFixed(1) }}%
          </el-descriptions-item>
          <el-descriptions-item label="幻觉率">
            <el-tag :type="evalReport.summary.hallucination_rate <= 0.05 ? 'success' : 'danger'">
              {{ (evalReport.summary.hallucination_rate * 100).toFixed(1) }}%
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="Skill 命中率">
            <el-tag :type="(evalReport.summary.skill_accuracy ?? 0) >= 0.8 ? 'success' : 'warning'">
              {{ ((evalReport.summary.skill_accuracy ?? 0) * 100).toFixed(1) }}%
              ({{ evalReport.summary.skill_matched_count ?? 0 }}/{{ evalReport.summary.skill_total ?? 0 }})
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <!-- 按领域统计 -->
        <div v-if="Object.keys(evalReport.summary.by_domain || {}).length" style="margin-top: 16px;">
          <h4 style="margin-bottom: 8px;">按领域统计</h4>
          <el-table :data="Object.entries(evalReport.summary.by_domain).map(([domain, stats]: [string, any]) => ({ domain, ...stats }))" size="small" border>
            <el-table-column prop="domain" label="领域" width="120" />
            <el-table-column prop="total" label="用例数" width="80" />
            <el-table-column prop="passed" label="通过数" width="80" />
            <el-table-column label="准确率">
              <template #default="{ row }">
                <el-tag :type="row.accuracy >= 0.8 ? 'success' : row.accuracy >= 0.6 ? 'warning' : 'danger'" size="small">
                  {{ (row.accuracy * 100).toFixed(1) }}%
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <!-- 按 Skill 统计 -->
        <div v-if="Object.keys(evalReport.summary.by_skill || {}).length" style="margin-top: 16px;">
          <h4 style="margin-bottom: 8px;">按 Skill 统计</h4>
          <el-table :data="Object.entries(evalReport.summary.by_skill).map(([skill, stats]: [string, any]) => ({ skill, label: skillLabel[skill] || skill, ...stats }))" size="small" border>
            <el-table-column label="Skill" width="140">
              <template #default="{ row }">
                <el-tag size="small" :color="skillColors[row.skill]" style="color: #fff; border: none;">{{ row.label }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="total" label="用例数" width="80" />
            <el-table-column prop="matched" label="命中数" width="80" />
            <el-table-column label="命中率">
              <template #default="{ row }">
                <el-tag :type="row.accuracy >= 0.8 ? 'success' : row.accuracy >= 0.6 ? 'warning' : 'danger'" size="small">
                  {{ (row.accuracy * 100).toFixed(1) }}%
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <!-- 失败用例 -->
        <div style="margin-top: 16px;">
          <h4 style="margin-bottom: 8px;">失败用例 ({{ evalReport.details.filter(d => !d.passed).length }})</h4>
          <el-table :data="evalReport.details.filter(d => !d.passed)" size="small" border max-height="300">
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column prop="message" label="用户输入" min-width="200" show-overflow-tooltip />
            <el-table-column prop="domain" label="领域" width="80" />
            <el-table-column label="失败原因" min-width="150">
              <template #default="{ row }">
                <span v-if="row.expected_skill_name && !row.skill_matched">Skill 不匹配: 期望={{ row.expected_skill_name }}</span>
                <span v-else-if="row.keywords_missed?.length">缺少关键词: {{ row.keywords_missed.join(', ') }}</span>
                <span v-else-if="row.forbidden_found?.length">包含禁止词: {{ row.forbidden_found.join(', ') }}</span>
                <span v-else-if="row.error">{{ row.error }}</span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
      <div v-else class="empty-content">
        <p>暂无评估报告</p>
        <p class="sub">点击"运行离线评估"生成报告</p>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.quality-page {
  max-width: 1400px;
  margin: 0 auto;
}

.action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;

  .page-desc {
    font-size: 13px;
    color: var(--text-caption);
  }

  .action-right {
    display: flex;
    align-items: center;
    gap: 12px;
  }
}

.quality-tabs {
  :deep(.el-tabs__header) {
    margin-bottom: 16px;
  }
}

// ── 概览卡片 ──
.overview-row {
  .stat-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--r-lg);
    padding: 18px 20px;
    transition: box-shadow 0.2s;

    &:hover { box-shadow: 0 2px 12px rgba(0,0,0,0.06); }

    .stat-label {
      font-size: 13px;
      color: var(--text-caption);
      margin-bottom: 8px;
    }

    .stat-value {
      font-size: 26px;
      font-weight: 700;
      color: var(--text-primary);

      &.accent { color: var(--accent); }
      &.info { color: #4facfe; }
    }
  }

  .token-card {
    background: linear-gradient(135deg, #667eea10, #764ba210);

    .token-big {
      font-size: 30px;
      background: linear-gradient(135deg, #667eea, #764ba2);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
  }
}

// ── 分布列表 ──
.dist-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.dist-item {
  display: flex;
  justify-content: space-between;
  align-items: center;

  .dist-left {
    display: flex;
    align-items: center;
    gap: 8px;

    .dist-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      flex-shrink: 0;

      &.danger { background: var(--danger); }
    }

    .dist-name {
      font-size: 13px;
      color: var(--text-body);
    }
  }

  .dist-right {
    display: flex;
    align-items: center;
    gap: 8px;

    .dist-count {
      font-size: 15px;
      font-weight: 600;
      color: var(--text-primary);
      min-width: 30px;
      text-align: right;

      &.danger { color: var(--danger); }
    }

    .dist-pct {
      font-size: 12px;
      color: var(--text-ghost);
      min-width: 40px;
      text-align: right;
    }
  }
}

// ── 链路卡片 ──
.trace-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.trace-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  overflow: hidden;
  transition: box-shadow 0.2s;

  &:hover { box-shadow: var(--shadow-md); }
}

.trace-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border);

  .trace-left {
    display: flex;
    align-items: center;
    gap: 10px;

    .trace-time {
      font-family: 'JetBrains Mono', 'Fira Code', monospace;
      font-size: 13px;
      color: var(--accent);
      font-weight: 600;
    }
  }

  .trace-right {
    .trace-user {
      font-size: 12px;
      color: var(--text-ghost);
    }
  }
}

.trace-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr) 2fr;
  gap: 1px;
  background: var(--border);
}

.grid-cell {
  background: var(--bg-card);
  padding: 14px 20px;

  .cell-label {
    font-size: 11px;
    color: var(--text-ghost);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 6px;
  }

  .cell-value {
    font-size: 18px;
    font-weight: 700;
    color: var(--text-primary);

    &.mono {
      font-family: 'JetBrains Mono', 'Fira Code', monospace;
      font-size: 15px;
      font-weight: 600;
    }

    &.warn { color: var(--warning); }
    &.info { color: var(--accent); }
  }
}

// ── 通用 ──
.card-header-with-badge {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.tool-tag {
  margin-right: 4px;
  font-size: 11px;
}

.text-ghost {
  color: var(--text-ghost);
  font-size: 12px;
}

.no-tool {
  font-size: 13px;
  color: var(--text-ghost);
}

.empty-hint {
  text-align: center;
  padding: 24px;
  color: var(--text-ghost);
  font-size: 13px;

  &.safe { color: var(--lime); }
}

.empty-content {
  text-align: center;
  padding: 40px;
  color: var(--text-caption);
  font-size: 15px;

  .sub {
    font-size: 13px;
    color: var(--text-ghost);
    margin-top: 8px;
  }
}
</style>
