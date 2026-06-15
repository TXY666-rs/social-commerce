# 🤖 Social-Commerce · AI 智能客服平台

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12+-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/LangGraph-ReAct-orange?logo=langchain&logoColor=white" alt="LangGraph">
  <img src="https://img.shields.io/badge/FastAPI-0.110+-green?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Vue-3.4-4FC08D?logo=vuedotjs&logoColor=white" alt="Vue">
  <img src="https://img.shields.io/badge/Redis-7-red?logo=redis&logoColor=white" alt="Redis">
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
</p>

**一个完整的电商客服演示系统**——包含 AI 智能客服 Agent、用户端商城、管理后台三部分。基于 **LangGraph ReAct 引擎**，集成多 Skill 路由、LLM 降级熔断、转人工 Human-in-the-Loop、安全防护与质量评估体系。

> 🎯 业务数据全本地 Mock，**不依赖任何 Java/Go 后端**，Redis 启动即用。面试官/学习者克隆后零配置体验全链路智能客服。

---

## 📸 一眼看懂

```
用户端商城 (Vue3)                  管理后台 (Vue3)
    │                                  │
    │  "我的订单到哪了？"               │  查看转人工队列
    │  "这个要退款"                     │  人工回复用户
    │  "转人工"                         │  质量监控面板
    │                                  │
    ▼                                  ▼
┌─────────────────────────────────────────────────────┐
│              AI Agent (FastAPI :8000)                │
│  ┌──────────────────────────────────────────────┐   │
│  │  4 级路由链                                    │   │
│  │  Active Skill → FAQ 快路径 → Skill Trigger    │   │
│  │  → ReAct Agent（LangGraph）                   │   │
│  └────────────────────┬─────────────────────────┘   │
│                       ▼                             │
│  ┌──────────────────────────────────────────────┐   │
│  │  agent ↔ tools ↔ guard 自纠错循环             │   │
│  │  7 个 Skill · 14 个工具 · Self-Correction     │   │
│  └────────────────────┬─────────────────────────┘   │
│                       ▼                             │
│  ┌──────────────────────────────────────────────┐   │
│  │  本地 Mock 业务数据层                          │   │
│  │  订单 / 退款 / 物流 / 商品 / 用户 / 地址       │   │
│  │  （替代 Java 微服务，Redis 持久化）             │   │
│  └──────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────┘
                        ▼
              ┌──────────────────┐
              │    Redis 7       │
              │  记忆 · Skill    │
              │  状态 · 工单队列 │
              │  Mock 业务数据   │
              └──────────────────┘
```

---

## ✨ 核心能力

### Agent 架构
| 能力 | 实现 | 亮点 |
|------|------|------|
| **LangGraph ReAct 引擎** | `ai-agent2/graph/` | agent ↔ tools ↔ guard 自纠错循环 |
| **4 级混合路由** | `ai-agent2/skills/` | Active Skill → FAQ 快路径 → Skill Trigger → ReAct Agent |
| **7 个业务 Skill** | `ai-agent2/skills/` | 查订单、修改订单、退款/退货、退款进度、取消退款、投诉、转人工 |
| **14 个工具** | `ai-agent2/agents/tools/` | 操作本地 Mock 数据（订单/物流/退款/商品/投诉/地址） |
| **Self-Correction** | `ai-agent2/reasoning/` | guard 节点检测工具异常并注入纠错上下文 |

### 稳定性 & 安全
| 能力 | 实现 | 亮点 |
|------|------|------|
| **LLM 降级链** | `ai-agent2/resilience/` | 3 模型 fallback（主力→备用→兜底） |
| **Circuit Breaker** | `ai-agent2/resilience/` | 连续失败熔断，自动恢复 |
| **Token Budget** | `ai-agent2/cost/` | 上下文压缩 + 成本控制 + 结果缓存 |
| **安全防护** | `ai-agent2/core/security.py` | Prompt 注入检测 + PII 脱敏 + 输出合规过滤 |

### 转人工（Human-in-the-Loop）
| 能力 | 实现 | 亮点 |
|------|------|------|
| **转接队列** | Redis List + Pub/Sub | 优先级排序（愤怒用户优先） |
| **人工回复** | 写入 Agent 会话历史 | 回复后 Agent 自动读取上下文，无缝切换 |
| **实时 SSE 推送** | Redis Pub/Sub → SSE | 人工回复秒级推送到用户端 |
| **工单管理** | 管理后台 | 待接听→正在处理→已完成 全生命周期 |

### 可观测 & 质量
| 能力 | 实现 | 亮点 |
|------|------|------|
| **运营监控面板** | `ai-agent2/monitoring/dashboard.py` | 对话量/FAQ 命中率/转人工率/情感分布 |
| **自动化评估** | `ai-agent2/monitoring/eval/` | 99 条测试用例 + LLM 评分 + 回归测试 |
| **结构化日志** | `structlog` | 全链路 trace_id |

---

## 🚀 快速启动

### 前置条件
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)（含 Docker Compose v2）
- LLM API Key（推荐阿里云 DashScope，国内直连）

### 3 步启动

```bash
# 1. 克隆项目
git clone git@github.com:TXY666-rs/social-commerce.git
cd social-commerce

# 2. 配置 LLM 密钥
cp ai-agent2/.env.example ai-agent2/.env
#    编辑 .env，填入 OPENAI_API_KEY
#    推荐模型：qwen-max / qwen-plus / qwen-turbo
#    也支持任何 OpenAI 兼容 API（MiniMax、DeepSeek 等）

# 3. 一键启动
docker compose up -d --build

# 4. 打开浏览器
#    用户端：http://localhost
#    管理后台：http://localhost:81
```

> 首次构建约 3-5 分钟（Docker 镜像构建），后续启动秒级。

---

## 🎮 体验场景

打开 http://localhost 登录（demo / 123456），点击右下角 💬 浮窗开始对话。系统预置 **6 个不同状态的订单**：

| 订单 | 状态 | 可体验 |
|------|------|--------|
| Sony WH-1000XM5 降噪耳机 | 已完成 | 查订单、申请退款（超期提示） |
| 戴森 V12 无线吸尘器 | 已完成 | 查订单、7 天内退款 |
| iPad Air 11 英寸 | 已发货 | 查物流、催单 |
| 罗技 MX Master 3S 鼠标 | 已支付 | 催发货、改地址 |
| 小米手环 8 Pro | 待支付 | 取消订单 |
| 飞利浦电动牙刷 | 退款中 | 查退款进度、取消退款 |

### 试试这些对话

| 你说 | 系统做什么 |
|------|-----------|
| 「查看我的订单」 | AI 调用 get_my_orders → 返回订单列表（含订单号+状态） |
| 「我的耳机到哪了」 | 意图识别 → track_logistics 查物流 |
| 「戴森吸尘器要退款」 | 退货时效校验（7 天内无理由） → request_refund |
| 「催一下 iPad」 | remind_delivery 工具 |
| 「取消小米手环的订单」 | cancel_order 工具 |
| 「转人工客服」 | 写入 Redis 转接队列 → 管理后台接单 → 人工回复 |
| 「你好」 | FAQ 快路径（不经过 LLM，零延迟） |

---

## 📁 项目结构

```
social-commerce/
├── docker-compose.yml              # 一键启动（Redis + Agent + 前端）
├── ARCHITECTURE.md                 # 架构设计详解（面试谈资）
│
├── ai-agent2/                      # 🔑 AI Agent 核心（Python/FastAPI）
│   ├── graph/                      #   LangGraph ReAct 引擎
│   ├── skills/                     #   7 个业务 Skill + 路由
│   ├── agents/tools/               #   14 个业务工具
│   ├── memory/                     #   3 层记忆 + Redis Pub/Sub
│   ├── resilience/                 #   LLM 降级链 + 熔断器
│   ├── reasoning/                  #   Self-Correction + Prompt 管理
│   ├── cost/                       #   Token Budget + 缓存
│   ├── core/                       #   安全防护 + 情感分析
│   ├── monitoring/                 #   运营面板 + 质量评估
│   ├── mock_data/                  #   本地 Mock 业务数据 + Seed
│   ├── api/                        #   FastAPI 路由 + 业务 Mock API
│   ├── middleware/                  #   认证 + Trace 中间件
│   └── tests/                      #   277 个单元测试
│
├── social-frontend/                # 🛒 用户端商城（Vue3 + Vite）
│   ├── src/views/
│   │   ├── Shop.vue                #   商城首页
│   │   ├── Orders.vue              #   我的订单（状态筛选+支付/取消/收货）
│   │   ├── ProductDetail.vue       #   商品详情
│   │   ├── Profile.vue             #   个人中心
│   │   └── AgentDemo.vue           #   AI 客服演示页
│   └── src/components/
│       └── AiCustomerService.vue   #   右侧浮窗 AI 客服（SSE 流式）
│
├── social-admin/                   # 📊 管理后台（Vue3 + Vite）
│   └── src/views/
│       ├── Dashboard.vue           #   运营监控面板
│       ├── TransferManagement.vue  #   转人工工单管理
│       └── QualityMonitor.vue      #   质量评估报告
│
└── infra/                          # 🏗️ 基础设施配置
    └── nacos-config/               #   Nacos 配置模板（可选）
```

---

## 🛠️ 本地开发（不用 Docker）

```bash
# 1. 启动 Redis
docker run -d --name redis -p 6379:6379 redis:7-alpine
# 或者连接已有 Redis，改 ai-agent2/.env 的 REDIS_HOST

# 2. 启动 AI Agent
cd ai-agent2
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
cp .env.example .env            # 填入 OPENAI_API_KEY + REDIS_HOST
uvicorn main:app --reload --port 8000

# 3. 启动前端（新开终端）
cd social-frontend
npm install
npm run dev                     # http://localhost:5173

# 4. 启动管理后台（可选，新开终端）
cd social-admin
npm install
npm run dev                     # http://localhost:5174
```

---

## 🔧 常用命令

```bash
# Docker 模式
docker compose up -d --build      # 启动全部
docker compose logs -f ai-agent   # 看 Agent 日志
docker compose restart ai-agent   # 重启 Agent
docker compose down               # 停止（保留 Redis 数据）
docker compose down -v            # 停止并清空 Redis

# 运行测试
cd ai-agent2 && pytest -q         # 277 个测试

# 清空转账工单（管理后台也能点按钮）
curl -X DELETE http://localhost:8000/admin/transfer/clear
```

---

## 🏗️ 设计理念

### 为什么不依赖 Java 微服务？

传统电商客服 Agent 需要对接订单服务、物流服务、退款服务等多个 Java 后端。本项目用 **Redis 存储的 Mock 数据层**完全替代，带来三个优势：

1. **零依赖启动**——面试官/学习者克隆即用，无需配 Java 环境
2. **数据可预测**——6 个预置订单覆盖全部状态，测试用例稳定
3. **架构可演示**——Tool 调用链路完整（查→改→退→催），展示真实 Agent 决策

Mock 数据的设计刻意**保留了与真实 Java 后端一致的数据结构**，Tool 和 Skill 代码对数据来源无感知——如果将来对接真实微服务，只需替换 `mock_data/` 层。

### 为什么转人工要自己写而不是用现成方案？

LangChain/LangGraph 生态中没有开箱即用的 Human-in-the-Loop 方案。本项目自研了基于 Redis Pub/Sub 的转人工机制：
- **工单队列**：带优先级排序（愤怒用户优先）、排队位置计算
- **SSE 实时推送**：管理员回复后用户端毫秒级收到，无需轮询
- **会话无缝切换**：人工回复写入 Agent 会话历史，AI 和人工共用上下文

详见 [ARCHITECTURE.md](./ARCHITECTURE.md) 第 9 节。

---

## 📚 技术栈

| 层 | 技术 |
|----|------|
| Agent 框架 | LangGraph + LangChain |
| LLM | 兼容 OpenAI 协议（Qwen / DeepSeek / MiniMax 等） |
| Web 框架 | FastAPI + Uvicorn |
| 流式输出 | SSE + Redis Pub/Sub |
| 记忆 / 缓存 / 队列 | Redis 7 |
| 前端 | Vue 3 + Vite + Element Plus + Pinia |
| 部署 | Docker Compose |
| 测试 | pytest（277 个测试用例） |
| 日志 | structlog（结构化，带 trace_id） |

---

## 📖 延伸阅读

- [ARCHITECTURE.md](./ARCHITECTURE.md) — 架构设计决策与面试谈资（为什么选 LangGraph、guard 节点的创新、4 级路由的权衡等）
- `ai-agent2/monitoring/eval/test_cases.json` — 99 条自动化测试用例
- `ai-agent2/.env.example` — 环境变量配置说明

---

## 📄 License

MIT
