<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { getAiAgentDashboard, switchLlm, resetLlm, type AiAgentDashboard } from '@/api/ai-agent'
import { ElMessage, ElMessageBox } from 'element-plus'

const data = ref<AiAgentDashboard | null>(null)
const loading = ref(false)
const switchingModel = ref(false)

const fetchData = async () => {
  loading.value = true
  try {
    data.value = await getAiAgentDashboard()
  } catch {
    data.value = null
  } finally {
    loading.value = false
  }
}

const toolSuccessRate = computed(() => {
  if (!data.value) return 0
  const s = data.value.tool_summary
  return s.total > 0 ? Math.round(s.success / s.total * 100) : 0
})

const toolFailRate = computed(() => 100 - toolSuccessRate.value)

const totalToolCalls = computed(() => {
  if (!data.value) return 0
  return data.value.tools.reduce((sum, t) => sum + t.calls, 0)
})

const llmStatus = computed(() => data.value?.llm_status ?? null)
const modelUsage = computed(() => data.value?.model_usage ?? [])

const svgPie = computed(() => {
  if (!data.value) return ''
  const s = data.value.tool_summary
  if (s.total === 0) return circle(50, 0)
  const angle = (s.success / s.total) * 360
  if (s.fail === 0) return circle(50, 1)
  if (s.success === 0) return circle(50, 0)
  return piePath(angle)
})

function circle(r: number, isSuccess: number) {
  const c = isSuccess ? '#4ECDC4' : '#F56C6C'
  return `<circle cx="50" cy="50" r="40" fill="none" stroke="${c}" stroke-width="12" stroke-dasharray="251.2" stroke-dashoffset="0" />`
}

function piePath(angle: number) {
  const rad = (angle - 90) * Math.PI / 180
  const x = 50 + 40 * Math.cos(rad)
  const y = 50 + 40 * Math.sin(rad)
  const large = angle > 180 ? 1 : 0
  return `<circle cx="50" cy="50" r="40" fill="none" stroke="#4ECDC4" stroke-width="12" stroke-dasharray="251.2" stroke-dashoffset="0" clip-path="url(#clip)" />
    <circle cx="50" cy="50" r="40" fill="none" stroke="#F56C6C" stroke-width="12" stroke-dasharray="251.2" stroke-dashoffset="0" />
    <clipPath id="clip"><path d="M50,10 A40,40 0 ${large},1 ${x},${y} L50,50 Z" /></clipPath>`
}

function fmtNum(n: number): string {
  if (n >= 10000) return (n / 10000).toFixed(1) + 'w'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'k'
  return String(n)
}

async function handleSwitchModel(level: number) {
  if (!llmStatus.value) return
  const target = llmStatus.value.models[level]
  if (!target || target.active) return
  try {
    await ElMessageBox.confirm(
      `确定切换到 ${target.name} 吗？`,
      '手动切换模型',
      { confirmButtonText: '切换', cancelButtonText: '取消', type: 'warning' }
    )
    switchingModel.value = true
    await switchLlm(level)
    ElMessage.success(`已切换到 ${target.name}`)
    await fetchData()
  } catch {
    // 用户取消或切换失败
  } finally {
    switchingModel.value = false
  }
}

async function handleResetModel() {
  try {
    switchingModel.value = true
    await resetLlm()
    ElMessage.success('已重置到主力模型')
    await fetchData()
  } catch {
    ElMessage.error('重置失败')
  } finally {
    switchingModel.value = false
  }
}

function formatFallbackTime(seconds: number | null): string {
  if (seconds === null) return '-'
  if (seconds < 60) return `${Math.round(seconds)}秒前`
  if (seconds < 3600) return `${Math.round(seconds / 60)}分钟前`
  return `${(seconds / 3600).toFixed(1)}小时前`
}

onMounted(fetchData)
</script>

<template>
  <div class="dashboard-page" v-loading="loading">
    <div v-if="data">

      <!-- 概览卡片 + 当前模型 -->
      <el-row :gutter="16" class="overview-row">
        <el-col :span="4">
          <div class="stat-card" @click="fetchData">
            <div class="stat-label">今日对话</div>
            <div class="stat-value accent">{{ data.today.conversations }}</div>
          </div>
        </el-col>
        <el-col :span="4">
          <div class="stat-card">
            <div class="stat-label">FAQ命中率</div>
            <div class="stat-value">{{ data.today.faq_rate }}%</div>
          </div>
        </el-col>
        <el-col :span="4">
          <div class="stat-card">
            <div class="stat-label">活跃Session</div>
            <div class="stat-value info">{{ data.today.active_sessions }}</div>
          </div>
        </el-col>
        <el-col :span="4">
          <div class="stat-card">
            <div class="stat-label">转人工</div>
            <div class="stat-value warn">{{ data.today.transfers }}</div>
          </div>
        </el-col>
        <el-col :span="4">
          <div class="stat-card token-card">
            <div class="stat-label">今日总 Token 消耗</div>
            <div class="stat-value token-big">{{ fmtNum(data.today.total_tokens) }}</div>
            <div class="stat-sub">{{ data.today.total_tokens.toLocaleString() }} tokens</div>
          </div>
        </el-col>
        <el-col :span="4">
          <div class="stat-card model-card" v-if="llmStatus">
            <div class="stat-label">当前模型</div>
            <div class="stat-value model-name">
              <span class="health-dot" :class="llmStatus.is_healthy ? 'ok' : 'warn'"></span>
              {{ llmStatus.current_model }}
            </div>
            <div class="stat-sub" v-if="!llmStatus.is_healthy">
              降级 Level {{ llmStatus.fallback_level }} / {{ llmStatus.total_models }}
            </div>
            <div class="stat-sub" v-else>正常运行</div>
          </div>
          <div class="stat-card model-card" v-else>
            <div class="stat-label">当前模型</div>
            <div class="stat-value model-name" style="font-size: 18px; color: var(--text-ghost)">-</div>
          </div>
        </el-col>
      </el-row>

      <!-- LLM 模型链状态 -->
      <el-row :gutter="16" style="margin-top: 16px;" v-if="llmStatus && llmStatus.models.length > 0">
        <el-col :span="16">
          <el-card shadow="hover" class="llm-chain-card">
            <template #header>
              <div class="llm-header">
                <span>LLM 模型链</span>
                <el-tag size="small" :type="llmStatus.is_healthy ? 'success' : 'warning'" class="llm-health-tag">
                  {{ llmStatus.is_healthy ? '健康' : `降级中 · ${formatFallbackTime(llmStatus.seconds_since_fallback)}` }}
                </el-tag>
              </div>
            </template>
            <div class="llm-chain" v-loading="switchingModel">
              <div
                v-for="m in llmStatus.models"
                :key="m.level"
                class="llm-node"
                :class="{ active: m.active }"
                @click="handleSwitchModel(m.level)"
              >
                <div class="llm-node-header">
                  <span class="llm-level">Level {{ m.level }}</span>
                  <el-tag v-if="m.active" size="small" type="success" effect="dark">当前</el-tag>
                </div>
                <div class="llm-model-name">{{ m.name }}</div>
              </div>
              <div class="llm-arrow" v-for="i in llmStatus.models.length - 1" :key="'arrow-' + i">
                <span class="arrow-icon">&#10140;</span>
              </div>
            </div>
            <div class="llm-actions" v-if="!llmStatus.is_healthy">
              <el-button size="small" type="primary" @click="handleResetModel">
                重置到主力模型
              </el-button>
            </div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="hover" class="llm-usage-card">
            <template #header><span>模型调用分布</span></template>
            <div v-if="modelUsage.length > 0" class="model-usage-list">
              <div v-for="mu in modelUsage" :key="mu.name" class="model-usage-item">
                <span class="mu-name">{{ mu.name }}</span>
                <el-progress
                  :percentage="Math.round(mu.count / modelUsage.reduce((s, x) => s + x.count, 0) * 100)"
                  :stroke-width="14"
                  :text-inside="true"
                  :format="() => mu.count + ' 次'"
                />
              </div>
            </div>
            <div v-else class="model-usage-empty">暂无数据</div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 工具调用汇总 -->
      <el-row :gutter="16" style="margin-top: 16px;">
        <el-col :span="12">
          <el-card shadow="hover">
            <template #header><span>工具调用成功 / 失败</span></template>
            <div class="pie-row">
              <div class="pie-chart">
                <svg viewBox="0 0 100 100" width="120" height="120">
                  <circle cx="50" cy="50" r="35" fill="none" stroke="#4ECDC4" stroke-width="12"
                    :stroke-dasharray="toolSuccessRate * 2.2 + ' ' + (220 - toolSuccessRate * 2.2)"
                    stroke-dashoffset="55" transform="rotate(-90 50 50)" stroke-linecap="butt" />
                  <circle cx="50" cy="50" r="35" fill="none" stroke="#F56C6C" stroke-width="12"
                    :stroke-dasharray="toolFailRate * 2.2 + ' ' + (220 - toolFailRate * 2.2)"
                    :stroke-dashoffset="55 - toolSuccessRate * 2.2"
                    transform="rotate(-90 50 50)" stroke-linecap="butt" />
                </svg>
                <div class="pie-center">
                  <div class="pie-num">{{ data.tool_summary.total }}</div>
                  <div class="pie-label">总调用</div>
                </div>
              </div>
              <div class="pie-legend">
                <div class="legend-item">
                  <span class="legend-dot s"></span>
                  <span>成功 {{ data.tool_summary.success }} ({{ toolSuccessRate }}%)</span>
                </div>
                <div class="legend-item">
                  <span class="legend-dot f"></span>
                  <span>失败 {{ data.tool_summary.fail }} ({{ toolFailRate }}%)</span>
                </div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card shadow="hover">
            <template #header><span>工具调用次数汇总</span></template>
            <div class="tool-total">
              <div class="big-num">{{ totalToolCalls }}</div>
              <div class="big-label">总调用次数</div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 对话明细表格 -->
      <el-card shadow="hover" style="margin-top: 16px;">
        <template #header><span>对话明细</span></template>
        <div class="scroll-table">
          <el-table :data="data.conversations_detail" size="small" stripe max-height="400" style="width: 100%">
            <el-table-column prop="user_id" label="用户ID" width="100" />
            <el-table-column prop="input_tokens" label="输入Token" width="100" align="right" sortable />
            <el-table-column prop="output_tokens" label="输出Token" width="100" align="right" sortable />
            <el-table-column prop="total_tokens" label="总Token" width="90" align="right" sortable />
            <el-table-column label="耗时" width="100" align="right" sortable>
              <template #default="{ row }">{{ row.duration_ms }}ms</template>
            </el-table-column>
            <el-table-column prop="agent" label="Agent" width="80" />
            <el-table-column label="模型" width="130">
              <template #default="{ row }">
                <el-tag v-if="row.model" size="small" type="info">{{ row.model }}</el-tag>
                <span v-else class="text-ghost">-</span>
              </template>
            </el-table-column>
            <el-table-column prop="time" label="请求时间" min-width="150" />
          </el-table>
        </div>
      </el-card>

      <!-- 工具调用明细表格 -->
      <el-card shadow="hover" style="margin-top: 16px;">
        <template #header><span>工具调用明细</span></template>
        <div class="scroll-table">
          <el-table :data="data.tool_details" size="small" stripe max-height="300" style="width: 100%">
            <el-table-column prop="name" label="工具名称" min-width="160">
              <template #default="{ row }">
                <code class="tool-name">{{ row.name }}</code>
              </template>
            </el-table-column>
            <el-table-column label="耗时" width="110" align="right" sortable>
              <template #default="{ row }">{{ row.duration_ms }}ms</template>
            </el-table-column>
            <el-table-column label="结果" width="80" align="center">
              <template #default="{ row }">
                <el-tag :type="row.success ? 'success' : 'danger'" size="small">{{ row.success ? '成功' : '失败' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="time" label="时间" width="100" />
          </el-table>
        </div>
      </el-card>
    </div>

    <div v-else-if="!loading">
      <el-card shadow="hover">
        <div class="ai-unavailable">
          <span>🔌 AI 客服服务未连接（请启动 ai-agent）</span>
        </div>
      </el-card>
    </div>
  </div>
</template>

<style scoped lang="scss">
.dashboard-page {
  max-width: 1400px;
  margin: 0 auto;
}

.overview-row {
  .stat-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 18px 20px;
    cursor: default;
    transition: box-shadow 0.2s;

    &:hover { box-shadow: 0 2px 12px rgba(0,0,0,0.06); }

    .stat-label {
      font-size: 13px;
      color: var(--text-caption);
      margin-bottom: 8px;
    }

    .stat-value {
      font-size: 28px;
      font-weight: 700;
      color: var(--text-primary);

      &.accent { color: var(--accent); }
      &.info { color: #4facfe; }
      &.warn { color: var(--warning); }
    }

    .stat-sub {
      font-size: 12px;
      color: var(--text-ghost);
      margin-top: 4px;
    }
  }

  .token-card {
    background: linear-gradient(135deg, #667eea10, #764ba210);

    .token-big {
      font-size: 32px;
      background: linear-gradient(135deg, #667eea, #764ba2);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
  }

  .model-card {
    .model-name {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 20px;
    }

    .health-dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      flex-shrink: 0;

      &.ok {
        background: #4ECDC4;
        box-shadow: 0 0 6px #4ECDC488;
      }
      &.warn {
        background: #F56C6C;
        box-shadow: 0 0 6px #F56C6C88;
        animation: pulse 1.5s ease-in-out infinite;
      }
    }
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

// LLM 模型链
.llm-chain-card {
  .llm-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .llm-health-tag {
    margin-left: 12px;
  }
}

.llm-chain {
  display: flex;
  align-items: center;
  padding: 16px 0;
  overflow-x: auto;
}

.llm-node {
  flex: 1;
  min-width: 160px;
  background: #f8f9fb;
  border: 2px solid #e4e7ed;
  border-radius: 12px;
  padding: 16px 18px;
  cursor: pointer;
  transition: all 0.25s;
  text-align: center;

  &:hover {
    border-color: #4facfe;
    box-shadow: 0 2px 12px rgba(79, 172, 254, 0.12);
  }

  &.active {
    border-color: #4ECDC4;
    background: linear-gradient(135deg, #4ECDC412, #4ECDC408);
    box-shadow: 0 2px 16px rgba(78, 205, 196, 0.15);
  }

  .llm-node-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
  }

  .llm-level {
    font-size: 11px;
    color: #909399;
    font-weight: 500;
    letter-spacing: 0.5px;
  }

  .llm-model-name {
    font-size: 16px;
    font-weight: 600;
    color: #303133;
    word-break: break-all;
  }
}

.llm-arrow {
  flex-shrink: 0;
  padding: 0 10px;
  color: #c0c4cc;
  font-size: 18px;
  line-height: 1;
}

.llm-actions {
  margin-top: 12px;
  text-align: right;
}

// 模型调用分布
.llm-usage-card {
  .model-usage-list {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .model-usage-item {
    .mu-name {
      display: block;
      font-size: 13px;
      color: #606266;
      margin-bottom: 4px;
      font-weight: 500;
    }
  }

  .model-usage-empty {
    text-align: center;
    padding: 24px 0;
    color: #c0c4cc;
    font-size: 13px;
  }
}

.text-ghost {
  color: #c0c4cc;
}

.pie-row {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 8px 0;
}

.pie-chart {
  position: relative;
  flex-shrink: 0;

  .pie-center {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    text-align: center;

    .pie-num {
      font-size: 20px;
      font-weight: 700;
      color: var(--text-primary);
    }
    .pie-label {
      font-size: 11px;
      color: var(--text-caption);
    }
  }
}

.pie-legend {
  .legend-item {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
    font-size: 13px;
    color: var(--text-secondary);
  }
  .legend-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;

    &.s { background: #4ECDC4; }
    &.f { background: #F56C6C; }
  }
}

.tool-total {
  text-align: center;
  padding: 20px 0;

  .big-num {
    font-size: 48px;
    font-weight: 700;
    color: var(--accent);
    line-height: 1;
  }
  .big-label {
    font-size: 13px;
    color: var(--text-caption);
    margin-top: 8px;
  }
}

.scroll-table {
  .tool-name {
    font-size: 12px;
    color: var(--text-secondary);
    background: var(--bg-deep);
    padding: 2px 6px;
    border-radius: 3px;
  }
}

.ai-unavailable {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px;
  color: var(--text-caption);
  font-size: 14px;
}
</style>
