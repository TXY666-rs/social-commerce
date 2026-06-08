"""管理端 API — 转人工队列管理 + 评估体系

提供给 social-admin 管理端前端调用的接口：
    GET  /admin/transfer/pending    — 拉取待处理的转接队列
    GET  /admin/transfer/{id}       — 查看转接工单详情 + 聊天记录
    POST /admin/transfer/{id}/accept   — 接听转接
    POST /admin/transfer/{id}/reply    — 人工回复用户
    POST /admin/transfer/{id}/complete — 完成转接
    POST /admin/eval/run             — 触发批量评估
    GET  /admin/eval/report          — 获取最新评估报告

人工回复的原理：
    人工回复的消息直接写入用户的 Redis 聊天历史（role="assistant"）。
    用户下次发消息时，Agent 会读到这条人工回复，然后基于上下文继续对话。
    这样人工和 Agent 可以无缝切换，用户感知不到中断。
"""

import json
import os
import time
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import structlog

from services.redis_client import get_redis
from memory.session_memory import SessionManager

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

# 评估报告存放路径（与 monitoring/eval/runner.py 默认输出一致）
_REPORT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "monitoring", "eval", "eval_report.json")

# 复用 SessionManager 写入 Agent 会话历史
_session_mgr = SessionManager()


class ReplyRequest(BaseModel):
    content: str
    agent_name: str = "人工客服"


# ============================================================
# Dashboard — 运营监控面板数据
# ============================================================

@router.get("/dashboard")
async def get_dashboard():
    """获取 AI 客服运营监控面板数据（供 social-admin 仪表盘调用）"""
    from monitoring.dashboard import get_dashboard_stats
    stats = await get_dashboard_stats()

    # 追加熔断器 / Token 预算 / 缓存统计
    try:
        from resilience.circuit_breaker import get_all_breakers
        stats["breakers"] = get_all_breakers()
    except Exception:
        stats["breakers"] = {}

    try:
        from cost.token_budget import get_all_budgets
        stats["budgets"] = get_all_budgets()
    except Exception:
        stats["budgets"] = {}

    try:
        from cost.cache import get_cache_stats
        stats["cache"] = get_cache_stats()
    except Exception:
        stats["cache"] = {}

    return stats


# ============================================================
# 拉取队列
# ============================================================

@router.get("/transfer/pending")
async def get_pending_transfers():
    """获取待处理的转接队列（供 social-admin 轮询）"""
    try:
        r = get_redis()
        raw_list = r.lrange("chat::transfer::queue", 0, -1)

        tickets = []
        for raw in raw_list:
            try:
                ticket = json.loads(raw)
                if ticket.get("status") == "pending":
                    tickets.append(ticket)
            except json.JSONDecodeError:
                continue

        return {
            "total": len(tickets),
            "tickets": tickets,
        }
    except Exception as e:
        logger.error("get_pending_transfers_failed", error=str(e))
        raise HTTPException(status_code=500, detail="获取队列失败")


# ============================================================
# 查看工单详情
# ============================================================

@router.get("/transfer/{transfer_id}")
async def get_transfer_detail(transfer_id: str):
    """查看转接工单详情 + 最近聊天记录"""
    try:
        r = get_redis()
        raw = r.get(f"chat::transfer::ticket::{transfer_id}")
        if not raw:
            raise HTTPException(status_code=404, detail="工单不存在")

        ticket = json.loads(raw)

        # 获取用户的聊天历史（从 Agent 会话存储读取）
        user_id = ticket.get("user_id", "")
        session_id = f"user_{user_id}"
        messages = _session_mgr.get_history(session_id)[-10:]

        return {
            "ticket": ticket,
            "recent_messages": messages,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_transfer_detail_failed", error=str(e))
        raise HTTPException(status_code=500, detail="获取工单详情失败")


# ============================================================
# 接听转接
# ============================================================

@router.post("/transfer/{transfer_id}/accept")
async def accept_transfer(transfer_id: str):
    """人工坐席接听转接"""
    try:
        r = get_redis()
        raw = r.get(f"chat::transfer::ticket::{transfer_id}")
        if not raw:
            raise HTTPException(status_code=404, detail="工单不存在")

        ticket = json.loads(raw)
        ticket["status"] = "accepted"
        ticket["accepted_at"] = time.time()

        r.setex(f"chat::transfer::ticket::{transfer_id}",
                1800, json.dumps(ticket, ensure_ascii=False))

        user_id = ticket.get("user_id", "")
        session_id = f"user_{user_id}"
        r.setex(f"chat::transfer::{session_id}", 3600, "accepted")

        # 向用户发送系统消息（写入 Agent 会话历史）
        _session_mgr.add_message(session_id, "assistant",
                                 "人工客服已接入，请问有什么可以帮您？")

        logger.info("transfer_accepted", transfer_id=transfer_id, user_id=user_id)

        return {"status": "ok", "message": "已接听"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("accept_transfer_failed", error=str(e))
        raise HTTPException(status_code=500, detail="接听失败")


# ============================================================
# 人工回复
# ============================================================

@router.post("/transfer/{transfer_id}/reply")
async def reply_to_user(transfer_id: str, request: ReplyRequest):
    """人工回复用户消息

    原理：直接写入用户的 Redis 聊天历史（role="assistant"）。
    用户下次发消息时，Agent 会读到这条人工回复。
    """
    try:
        r = get_redis()
        raw = r.get(f"chat::transfer::ticket::{transfer_id}")
        if not raw:
            raise HTTPException(status_code=404, detail="工单不存在")

        ticket = json.loads(raw)
        user_id = ticket.get("user_id", "")
        session_id = f"user_{user_id}"

        human_reply = {
            "role": "assistant",
            "content": request.content,
            "timestamp": time.time(),
            "source": "human_agent",
            "agent_name": request.agent_name,
        }
        r.rpush(f"chat::history::{session_id}", json.dumps(human_reply, ensure_ascii=False))

        # 同步写入 Agent 会话历史（下次对话 Agent 能读到）
        _session_mgr.add_message(session_id, "assistant", request.content)

        logger.info("human_reply_sent",
                     transfer_id=transfer_id,
                     user_id=user_id,
                     agent_name=request.agent_name,
                     content_len=len(request.content))

        return {
            "status": "ok",
            "message": "回复已发送",
            "session_id": session_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("reply_to_user_failed", error=str(e))
        raise HTTPException(status_code=500, detail="回复失败")


# ============================================================
# 完成转接
# ============================================================

@router.post("/transfer/{transfer_id}/complete")
async def complete_transfer(transfer_id: str):
    """完成转接（人工坐席处理完毕）"""
    try:
        r = get_redis()
        raw = r.get(f"chat::transfer::ticket::{transfer_id}")
        if not raw:
            raise HTTPException(status_code=404, detail="工单不存在")

        ticket = json.loads(raw)
        ticket["status"] = "completed"
        ticket["completed_at"] = time.time()

        r.setex(f"chat::transfer::ticket::{transfer_id}",
                1800, json.dumps(ticket, ensure_ascii=False))

        user_id = ticket.get("user_id", "")
        session_id = f"user_{user_id}"
        r.setex(f"chat::transfer::{session_id}", 3600, "completed")

        # 写入 Agent 会话历史
        _session_mgr.add_message(session_id, "assistant",
                                 "人工客服已结束本次服务。如需帮助，您可以继续向我提问。")

        logger.info("transfer_completed", transfer_id=transfer_id, user_id=user_id)

        return {"status": "ok", "message": "转接已完成"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("complete_transfer_failed", error=str(e))
        raise HTTPException(status_code=500, detail="完成转接失败")


# ============================================================
# 评估体系 — 批量测评 + 报告查询
# ============================================================

@router.post("/eval/run")
async def run_eval(
    domain: str = Query(None, description="按领域筛选: order/product/after_sale/coupon/safety/faq"),
    difficulty: str = Query(None, description="按难度筛选: easy/medium/hard"),
    token: str = Query(None, description="认证 token（避免 401）"),
    eval_user_id: str = Query("1", description="评估使用的用户ID，该用户需有订单数据"),
):
    """触发批量评估（内部调用 /chat 接口跑 test_cases.json）

    同步执行并返回完整报告，适合小规模数据集（<200 条）。
    大规模场景可改为后台任务 + 轮询。
    """
    from monitoring.eval.runner import run_evaluation

    logger.info("eval_run_triggered", domain=domain, difficulty=difficulty, eval_user_id=eval_user_id)

    try:
        result = await run_evaluation(
            domain=domain,
            difficulty=difficulty,
            report_path=_REPORT_PATH,
            auth_token=token,
            eval_user_id=eval_user_id,
        )
        return {
            "status": "ok",
            "message": f"评估完成，共 {result.get('total', 0)} 条",
            "result": result,
        }
    except Exception as e:
        logger.error("eval_run_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"评估执行失败: {str(e)}")


@router.get("/eval/report")
async def get_eval_report():
    """获取最新评估报告（由 /admin/eval/run 生成）"""
    if not os.path.exists(_REPORT_PATH):
        raise HTTPException(status_code=404, detail="暂无评估报告，请先运行评估")

    try:
        with open(_REPORT_PATH, "r", encoding="utf-8") as f:
            report = json.load(f)
        return report
    except Exception as e:
        logger.error("get_eval_report_failed", error=str(e))
        raise HTTPException(status_code=500, detail="读取报告失败")


# ============================================================
# 实时质量监控 — 基于真实流量的 eval 数据聚合
# ============================================================

@router.get("/eval/realtime")
async def get_eval_realtime():
    """获取实时质量监控数据（基于真实用户请求的 eval 采集）

    每次 /chat 请求完成后，eval 数据自动写入 Redis。
    本接口聚合今日数据，返回路由分布、延迟、Token、安全事件等。
    """
    from monitoring.realtime import get_eval_realtime_stats
    return await get_eval_realtime_stats()


@router.get("/eval/traces")
async def get_eval_traces(limit: int = Query(30, description="返回条数")):
    """获取最近 N 条请求链路明细（供链路拆解页面使用）

    每条记录包含：用户、路由来源、Agent类型、延迟、Token、工具调用等。
    """
    from monitoring.realtime import get_eval_traces
    return await get_eval_traces(limit=min(limit, 100))
