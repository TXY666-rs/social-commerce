<script setup lang="ts">
import { ref } from 'vue'
import AiCustomerService from '@/components/AiCustomerService.vue'
import {
  ChatDotRound,
  Cpu,
  Connection,
  DataLine,
  Lock,
  MagicStick,
  Monitor,
} from '@element-plus/icons-vue'

// Agent 架构亮点（面试谈资）
const highlights = [
  {
    icon: Cpu,
    title: 'LangGraph ReAct 引擎',
    desc: 'agent ↔ tools ↔ guard 自纠错循环，工具调用失败自动修正策略',
  },
  {
    icon: Connection,
    title: '多 Skill 混合路由',
    desc: '4 级优先级路由链：Active Skill → FAQ → Skill Trigger → ReAct Agent',
  },
  {
    icon: DataLine,
    title: '3 层记忆体系',
    desc: '短期对话 + 窗口摘要 + Working Memory，Redis Pub/Sub 驱动 SSE 流式',
  },
  {
    icon: MagicStick,
    title: 'LLM 降级链 + 熔断',
    desc: '3 模型 fallback（max → plus → turbo）+ Circuit Breaker 熔断保护',
  },
  {
    icon: Lock,
    title: '安全防护',
    desc: 'Prompt 注入检测 + PII 脱敏（手机号/身份证/邮箱）+ 输出安全过滤',
  },
  {
    icon: Monitor,
    title: '可观测 + 质量评估',
    desc: 'Token Budget 成本控制 + Trace 链路追踪 + 自动化 Eval 测试用例',
  },
]

// 快捷体验话术
const quickPrompts = [
  '查看我的订单',
  '我的耳机到哪了',
  '我要退款戴森吸尘器',
  '帮我催一下 iPad 发货',
  '转人工客服',
]

const chatKey = ref(0)
function triggerPrompt(text: string) {
  // 通过自定义事件触发 AiCustomerService 发送（简化：用 localStorage 传递）
  localStorage.setItem('ai_quick_prompt', text)
  localStorage.removeItem('ai_quick_prompt')
  // 模拟点击聊天浮窗打开
  window.dispatchEvent(new CustomEvent('ai-open-chat', { detail: text }))
}
</script>

<template>
  <div class="demo-page">
    <!-- Hero 区 -->
    <header class="hero">
      <div class="hero-inner">
        <div class="badge">🤖 AI Agent 开发作品</div>
        <h1>AI 智能客服 Agent</h1>
        <p class="subtitle">
          基于 <strong>LangGraph</strong> 构建的生产级 ReAct Agent，
          集成多 Skill 路由、3 层记忆、LLM 降级链与自纠错引擎。
          点击右下角浮窗 <el-icon><ChatDotRound /></el-icon> 开始对话体验。
        </p>

        <div class="tech-stack">
          <span class="tech-tag">Python 3.12</span>
          <span class="tech-tag">LangGraph</span>
          <span class="tech-tag">LangChain</span>
          <span class="tech-tag">FastAPI</span>
          <span class="tech-tag">Redis</span>
          <span class="tech-tag">Qwen LLM</span>
        </div>

        <!-- 快捷体验 -->
        <div class="quick-prompts">
          <span class="quick-label">一键体验：</span>
          <button
            v-for="p in quickPrompts"
            :key="p"
            class="quick-btn"
            @click="triggerPrompt(p)"
          >
            {{ p }}
          </button>
        </div>
      </div>
    </header>

    <!-- 架构亮点 -->
    <section class="highlights">
      <h2 class="section-title">核心架构亮点</h2>
      <div class="highlights-grid">
        <div v-for="h in highlights" :key="h.title" class="highlight-card">
          <div class="card-icon">
            <el-icon :size="24"><component :is="h.icon" /></el-icon>
          </div>
          <h3>{{ h.title }}</h3>
          <p>{{ h.desc }}</p>
        </div>
      </div>
    </section>

    <!-- 内嵌聊天组件 -->
    <AiCustomerService :key="chatKey" />

    <footer class="demo-footer">
      <p>💡 这是一个聚焦 Agent 架构的演示项目，业务数据为本地 Mock（预置了 6 个不同状态的订单）</p>
    </footer>
  </div>
</template>

<style scoped lang="scss">
.demo-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #0f1419 0%, #1a1f2e 100%);
  color: #e8eaed;
}

/* Hero */
.hero {
  padding: 80px 32px 60px;
  text-align: center;
}
.hero-inner {
  max-width: 900px;
  margin: 0 auto;
}
.badge {
  display: inline-block;
  padding: 6px 16px;
  background: rgba(78, 205, 196, 0.15);
  border: 1px solid rgba(78, 205, 196, 0.3);
  border-radius: 999px;
  font-size: 13px;
  color: #4ecdc4;
  margin-bottom: 24px;
}
h1 {
  font-size: 42px;
  font-weight: 800;
  margin: 0 0 20px;
  background: linear-gradient(135deg, #4ecdc4, #44a8b3);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.subtitle {
  font-size: 17px;
  line-height: 1.7;
  color: #9aa0a6;
  max-width: 680px;
  margin: 0 auto 32px;
}
.subtitle strong { color: #4ecdc4; }

.tech-stack {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 10px;
  margin-bottom: 40px;
}
.tech-tag {
  padding: 6px 14px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
}

/* 快捷体验 */
.quick-prompts {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  align-items: center;
  gap: 10px;
}
.quick-label {
  font-size: 14px;
  color: #9aa0a6;
}
.quick-btn {
  padding: 8px 18px;
  background: rgba(78, 205, 196, 0.1);
  border: 1px solid rgba(78, 205, 196, 0.3);
  border-radius: 999px;
  color: #4ecdc4;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  &:hover {
    background: rgba(78, 205, 196, 0.2);
    transform: translateY(-1px);
  }
}

/* 架构亮点 */
.highlights {
  max-width: 1200px;
  margin: 0 auto;
  padding: 40px 32px 80px;
}
.section-title {
  font-size: 28px;
  font-weight: 700;
  text-align: center;
  margin-bottom: 40px;
  color: #e8eaed;
}
.highlights-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}
.highlight-card {
  padding: 28px 24px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  transition: all 0.3s;
  &:hover {
    background: rgba(78, 205, 196, 0.06);
    border-color: rgba(78, 205, 196, 0.2);
    transform: translateY(-2px);
  }
}
.card-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(78, 205, 196, 0.2), rgba(78, 205, 196, 0.05));
  display: flex;
  align-items: center;
  justify-content: center;
  color: #4ecdc4;
  margin-bottom: 16px;
}
.highlight-card h3 {
  font-size: 17px;
  font-weight: 600;
  margin: 0 0 8px;
  color: #e8eaed;
}
.highlight-card p {
  font-size: 14px;
  line-height: 1.6;
  color: #9aa0a6;
  margin: 0;
}

/* Footer */
.demo-footer {
  text-align: center;
  padding: 32px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  p {
    font-size: 13px;
    color: #5f6368;
    margin: 0;
  }
}

/* 移动端 */
@media (max-width: 768px) {
  .hero { padding: 48px 20px 40px; }
  h1 { font-size: 30px; }
  .subtitle { font-size: 15px; }
  .highlights { padding: 24px 16px 60px; }
}
</style>
