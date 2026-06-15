"""运营统计 — Redis 计数 + 仪表盘数据聚合

每日维度（TTL 48h，过期自动清理）：
    conversations  总对话数
    faq_hits      FAQ 快捷回复命中数
    tool_calls    工具调用次数（按工具名）
    tool_errors   工具调用失败（按工具名）
    sentiment     情感分布（positive/neutral/negative）
    transfers     转人工次数
    feedback_up   好评数
    feedback_down 差评数

明细维度（TTL 72h）：
    stats:conv:{date}   每轮对话明细（user_id, tokens, duration）
    stats:tool:{date}   每次工具调用明细（name, duration, success）
    stats:daily:total_tokens:{date}  单日总 token 计数器

使用方式：
    await record_chat(...)             # 每次对话完成时调用
    await record_conversation_detail() # 对话完成后调用
    await record_tool_detail()         # 每次工具调用后调用
    await get_dashboard_stats()        # 管理后台查询
"""
import json
import time
from datetime import date, datetime
from services.redis_client import get_redis
import structlog

logger = structlog.get_logger(__name__)

STATS_TTL = 48 * 3600       # 每日统计保留 48h
DETAIL_TTL = 72 * 3600      # 明细数据保留 72h
ACTIVE_TTL = 30 * 60        # 活跃 Session 窗口 30min


def _today() -> str:
    return date.today().isoformat()

def _k(*parts: str) -> str:
    """构建 Redis key：stats:daily:{date}:..."""
    return "stats:daily:" + ":".join(parts)

def _active_k(sid: str) -> str:
    return f"stats:active:{sid}"


async def record_chat(
    session_id: str,
    is_faq: bool = False,
    agent_type: str = "unknown",
    tool_calls: list[str] | None = None,
    tool_errors: list[str] | None = None,
    sentiment: str = "neutral",
    transfer: bool = False,
    model_name: str = "",
) -> None:
    """每次对话完成后记录统计数据"""
    try:
        r = get_redis()
        today = _today()

        pipe = r.pipeline()
        pipe.incr(_k(today, "conversations"))

        if is_faq:
            pipe.incr(_k(today, "faq_hits"))

        for name in (tool_calls or []):
            pipe.incr(_k(today, "tool_calls", name))
        for name in (tool_errors or []):
            pipe.incr(_k(today, "tool_errors", name))

        if sentiment in ("positive", "neutral", "negative"):
            pipe.incr(_k(today, "sentiment", sentiment))

        if transfer:
            pipe.incr(_k(today, "transfers"))

        # 模型使用计数
        if model_name:
            pipe.incr(_k(today, "model_usage", model_name))

        # 活跃 Session
        pipe.setex(_active_k(session_id), ACTIVE_TTL, "1")

        # 收集所有需要设置 TTL 的 key
        ttl_keys = [
            _k(today, "conversations"),
            _k(today, "faq_hits"),
            _k(today, "transfers"),
            _k(today, "sentiment", "positive"),
            _k(today, "sentiment", "neutral"),
            _k(today, "sentiment", "negative"),
        ]
        for name in (tool_calls or []):
            ttl_keys.append(_k(today, "tool_calls", name))
        for name in (tool_errors or []):
            ttl_keys.append(_k(today, "tool_errors", name))
        if model_name:
            ttl_keys.append(_k(today, "model_usage", model_name))
        # EXPIRE 合并到 pipeline 中，避免 N 次独立往返
        for k in ttl_keys:
            pipe.expire(k, STATS_TTL)

        pipe.execute()

    except Exception:
        pass  # 统计数据收集失败不影响主流程


async def record_feedback(session_id: str, rating: str) -> None:
    """记录用户反馈（👍/👎）"""
    try:
        r = get_redis()
        today = _today()
        if rating == "up":
            r.incr(_k(today, "feedback_up"))
        elif rating == "down":
            r.incr(_k(today, "feedback_down"))
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════
# 明细记录
# ═══════════════════════════════════════════════════════════

async def record_conversation_detail(
    user_id: str,
    input_tokens: int,
    output_tokens: int,
    duration_ms: float,
    agent_type: str,
    model_name: str = "",
) -> None:
    """记录每轮对话的详细指标（token 消耗 + 耗时 + 模型）"""
    try:
        r = get_redis()
        today = _today()
        total = input_tokens + output_tokens
        record = json.dumps({
            "user_id": user_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total,
            "duration_ms": int(duration_ms),
            "agent": agent_type,
            "model": model_name,
            "time": datetime.now().strftime("%Y/%m/%d %H:%M"),
        }, ensure_ascii=False)
        ts = time.time()
        pipe = r.pipeline()
        pipe.zadd(f"stats:conv:{today}", {record: ts})
        pipe.expire(f"stats:conv:{today}", DETAIL_TTL)
        pipe.incrby(f"stats:daily:total_tokens:{today}", total)
        pipe.expire(f"stats:daily:total_tokens:{today}", DETAIL_TTL)
        pipe.execute()
    except Exception:
        pass


async def record_tool_detail(tool_name: str, duration_ms: float, success: bool) -> None:
    """记录每次工具调用的详细指标（耗时 + 成功/失败）

    注：此函数虽是 async 签名（兼容 asyncio.create_task），
    但内部全部使用同步 Redis 客户端，可直接在同步上下文中调用。
    """
    _sync_record_tool_detail(tool_name, duration_ms, success)


def record_tool_detail_sync(tool_name: str, duration_ms: float, success: bool) -> None:
    """同步版本 — 供 LangGraph 同步节点直接调用"""
    _sync_record_tool_detail(tool_name, duration_ms, success)


def _sync_record_tool_detail(tool_name: str, duration_ms: float, success: bool) -> None:
    try:
        r = get_redis()
        today = _today()
        record = json.dumps({
            "name": tool_name,
            "duration_ms": int(duration_ms),
            "success": success,
            "time": datetime.now().strftime("%H:%M:%S"),
        }, ensure_ascii=False)
        ts = time.time()
        pipe = r.pipeline()
        pipe.zadd(f"stats:tool:{today}", {record: ts})
        pipe.expire(f"stats:tool:{today}", DETAIL_TTL)
        pipe.execute()
    except Exception:
        pass


async def get_dashboard_stats() -> dict:
    """聚合仪表盘数据 — 返回给管理后台"""
    try:
        r = get_redis()
        today = _today()

        base = _k(today, "")

        # 批量获取计数器
        keys = [
            f"{base}conversations",
            f"{base}faq_hits",
            f"{base}transfers",
            f"{base}feedback_up",
            f"{base}feedback_down",
            f"{base}sentiment:positive",
            f"{base}sentiment:neutral",
            f"{base}sentiment:negative",
        ]
        vals = r.mget(keys)
        conversations = int(vals[0] or 0)
        faq_hits = int(vals[1] or 0)
        transfers = int(vals[2] or 0)
        feedback_up = int(vals[3] or 0)
        feedback_down = int(vals[4] or 0)
        pos = int(vals[5] or 0)
        neu = int(vals[6] or 0)
        neg = int(vals[7] or 0)

        # 工具调用统计
        tool_pattern = f"{base}tool_calls:*"
        tool_keys = list(r.scan_iter(match=tool_pattern, count=200))
        tools = []
        for tk in tool_keys:
            name = tk.rsplit(":", 1)[-1]
            calls = int(r.get(tk) or 0)
            err_key = _k(today, "tool_errors", name)
            errors = int(r.get(err_key) or 0)
            if calls > 0:
                tools.append({"name": name, "calls": calls, "errors": errors})
        tools.sort(key=lambda t: t["calls"], reverse=True)

        # 活跃 Session 数
        active_pattern = "stats:active:*"
        active_count = sum(1 for _ in r.scan_iter(match=active_pattern, count=500))

        # FAQ 命中率
        faq_rate = round(faq_hits / conversations * 100, 1) if conversations > 0 else 0

        # 情感分布
        sentiment_total = pos + neu + neg
        sentiment = {
            "positive": {"count": pos, "pct": round(pos / sentiment_total * 100, 1) if sentiment_total > 0 else 0},
            "neutral": {"count": neu, "pct": round(neu / sentiment_total * 100, 1) if sentiment_total > 0 else 0},
            "negative": {"count": neg, "pct": round(neg / sentiment_total * 100, 1) if sentiment_total > 0 else 0},
        }

        # 好评率
        fb_total = feedback_up + feedback_down
        feedback_rate = round(feedback_up / fb_total * 100, 1) if fb_total > 0 else 0

        # 单日总 Token 数
        total_tokens = int(r.get(f"stats:daily:total_tokens:{today}") or 0)

        # 对话明细（最新 50 条）
        conv_records = r.zrevrange(f"stats:conv:{today}", 0, 49)
        conversations_detail = [json.loads(rec) for rec in conv_records]

        # 工具调用明细（最新 100 条）
        tool_records = r.zrevrange(f"stats:tool:{today}", 0, 99)
        tool_details = [json.loads(rec) for rec in tool_records]

        # 工具调用汇总（成功/失败占比 + 总次数）
        tool_success = 0
        tool_fail = 0
        for td in tool_details:
            if td.get("success"):
                tool_success += 1
            else:
                tool_fail += 1
        tool_total = tool_success + tool_fail

        # 模型使用统计
        model_pattern = f"{base}model_usage:*"
        model_keys = list(r.scan_iter(match=model_pattern, count=50))
        model_usage = []
        for mk in model_keys:
            name = mk.rsplit(":", 1)[-1]
            count = int(r.get(mk) or 0)
            if count > 0:
                model_usage.append({"name": name, "count": count})
        model_usage.sort(key=lambda m: m["count"], reverse=True)

        # 当前 LLM 状态
        try:
            from resilience.llm_factory import get_llm_status
            llm_status = get_llm_status()
        except Exception:
            llm_status = {}

        return {
            "today": {
                "conversations": conversations,
                "faq_hits": faq_hits,
                "faq_rate": faq_rate,
                "transfers": transfers,
                "active_sessions": active_count,
                "total_tokens": total_tokens,
            },
            "sentiment": sentiment,
            "feedback": {
                "up": feedback_up,
                "down": feedback_down,
                "rate": feedback_rate,
            },
            "tools": tools[:10],
            "tool_summary": {
                "total": tool_total,
                "success": tool_success,
                "fail": tool_fail,
            },
            "model_usage": model_usage,
            "llm_status": llm_status,
            "conversations_detail": conversations_detail,
            "tool_details": tool_details,
        }
    except Exception as e:
        logger.error("get_dashboard_stats_failed", error=str(e))
        return {
            "today": {"conversations": 0, "faq_hits": 0, "faq_rate": 0, "transfers": 0, "active_sessions": 0, "total_tokens": 0},
            "sentiment": {"positive": {"count": 0, "pct": 0}, "neutral": {"count": 0, "pct": 0}, "negative": {"count": 0, "pct": 0}},
            "feedback": {"up": 0, "down": 0, "rate": 0},
            "tools": [],
            "tool_summary": {"total": 0, "success": 0, "fail": 0},
            "model_usage": [],
            "llm_status": {},
            "conversations_detail": [],
            "tool_details": [],
        }
