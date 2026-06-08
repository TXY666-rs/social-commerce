"""实时质量监控 — 基于真实流量的 eval 数据采集与聚合

每次 /chat 请求完成后，eval 数据自动写入 Redis。
管理后台通过 get_eval_realtime_stats() 和 get_eval_traces() 查询。

存储结构（TTL 48-72h）：
    stats:eval:{date}              sorted set（score=timestamp），每次请求的完整 eval JSON
    stats:eval:route:{date}:{source}  路由来源计数器
    stats:eval:safety:{date}:{type}   安全事件计数器
    stats:eval:agent:{date}:{agent}   Agent 类型计数器
    stats:eval:sum_*:{date}           累计延迟/Token 计数器
"""
import json
import time
from datetime import date, datetime
from services.redis_client import get_redis
import structlog

logger = structlog.get_logger(__name__)

STATS_TTL = 48 * 3600       # 每日统计保留 48h
DETAIL_TTL = 72 * 3600      # 明细数据保留 72h


def _today() -> str:
    return date.today().isoformat()


async def record_eval_data(
    user_id: str,
    agent_type: str,
    route_source: str,
    latency: dict,
    token: dict,
    safety: dict,
    tools_called: list[str] | None = None,
    is_faq: bool = False,
    skill_name: str = "",
) -> None:
    """每次请求完成后记录 eval 数据到 Redis（供实时质量监控面板使用）"""
    try:
        r = get_redis()
        today = _today()
        ts = time.time()

        record = json.dumps({
            "user_id": user_id,
            "agent_type": agent_type,
            "route_source": route_source,
            "skill_name": skill_name,
            "routing_ms": latency.get("routing_ms", 0),
            "total_ms": latency.get("total_ms", 0),
            "input_tokens": token.get("input", 0),
            "output_tokens": token.get("output", 0),
            "tools_called": tools_called or [],
            "is_faq": is_faq,
            "time": datetime.now().strftime("%H:%M:%S"),
        }, ensure_ascii=False)

        pipe = r.pipeline()
        # eval 明细（sorted set，保留最近 500 条）
        pipe.zadd(f"stats:eval:{today}", {record: ts})
        pipe.zremrangebyrank(f"stats:eval:{today}", 0, -501)
        pipe.expire(f"stats:eval:{today}", DETAIL_TTL)

        # 路由来源计数
        pipe.incr(f"stats:eval:route:{today}:{route_source}")
        pipe.expire(f"stats:eval:route:{today}:{route_source}", STATS_TTL)

        # Agent 类型计数
        pipe.incr(f"stats:eval:agent:{today}:{agent_type}")
        pipe.expire(f"stats:eval:agent:{today}:{agent_type}", STATS_TTL)

        # Skill 命中计数（按具体 Skill 名称）
        if skill_name:
            pipe.incr(f"stats:eval:skill:{today}:{skill_name}")
            pipe.expire(f"stats:eval:skill:{today}:{skill_name}", STATS_TTL)

        # 安全事件计数
        for event_type, triggered in safety.items():
            if triggered:
                pipe.incr(f"stats:eval:safety:{today}:{event_type}")
                pipe.expire(f"stats:eval:safety:{today}:{event_type}", STATS_TTL)

        # 累计延迟和 Token
        pipe.incrby(f"stats:eval:sum_routing_ms:{today}", int(latency.get("routing_ms", 0)))
        pipe.incrby(f"stats:eval:sum_total_ms:{today}", int(latency.get("total_ms", 0)))
        pipe.incrby(f"stats:eval:sum_input_tokens:{today}", token.get("input", 0))
        pipe.incrby(f"stats:eval:sum_output_tokens:{today}", token.get("output", 0))
        pipe.expire(f"stats:eval:sum_routing_ms:{today}", STATS_TTL)
        pipe.expire(f"stats:eval:sum_total_ms:{today}", STATS_TTL)
        pipe.expire(f"stats:eval:sum_input_tokens:{today}", STATS_TTL)
        pipe.expire(f"stats:eval:sum_output_tokens:{today}", STATS_TTL)

        pipe.execute()

    except Exception:
        pass  # 统计数据收集失败不影响主流程


async def get_eval_realtime_stats() -> dict:
    """聚合实时质量监控数据 — 返回给管理后台"""
    try:
        r = get_redis()
        today = _today()

        # 今日 eval 明细总数
        total_requests = r.zcard(f"stats:eval:{today}") or 0

        # 累计值
        sum_routing_ms = int(r.get(f"stats:eval:sum_routing_ms:{today}") or 0)
        sum_total_ms = int(r.get(f"stats:eval:sum_total_ms:{today}") or 0)
        sum_input_tokens = int(r.get(f"stats:eval:sum_input_tokens:{today}") or 0)
        sum_output_tokens = int(r.get(f"stats:eval:sum_output_tokens:{today}") or 0)

        avg_routing_ms = round(sum_routing_ms / total_requests) if total_requests > 0 else 0
        avg_total_ms = round(sum_total_ms / total_requests) if total_requests > 0 else 0

        # 路由来源分布
        route_pattern = f"stats:eval:route:{today}:*"
        route_dist = {}
        for key in r.scan_iter(match=route_pattern, count=20):
            source = key.rsplit(":", 1)[-1]
            count = int(r.get(key) or 0)
            if count > 0:
                route_dist[source] = count

        # Agent 类型分布
        agent_pattern = f"stats:eval:agent:{today}:*"
        agent_dist = {}
        for key in r.scan_iter(match=agent_pattern, count=20):
            agent = key.rsplit(":", 1)[-1]
            count = int(r.get(key) or 0)
            if count > 0:
                agent_dist[agent] = count

        # Skill 命中分布
        skill_pattern = f"stats:eval:skill:{today}:*"
        skill_dist = {}
        for key in r.scan_iter(match=skill_pattern, count=20):
            skill_name = key.rsplit(":", 1)[-1]
            count = int(r.get(key) or 0)
            if count > 0:
                skill_dist[skill_name] = count

        # 安全事件统计
        safety_pattern = f"stats:eval:safety:{today}:*"
        safety_events = {}
        for key in r.scan_iter(match=safety_pattern, count=20):
            event_type = key.rsplit(":", 1)[-1]
            count = int(r.get(key) or 0)
            if count > 0:
                safety_events[event_type] = count

        # 最近 20 条请求明细
        recent_raw = r.zrevrange(f"stats:eval:{today}", 0, 19)
        recent_requests = [json.loads(rec) for rec in recent_raw]

        return {
            "summary": {
                "total_requests": total_requests,
                "avg_routing_ms": avg_routing_ms,
                "avg_total_ms": avg_total_ms,
                "total_input_tokens": sum_input_tokens,
                "total_output_tokens": sum_output_tokens,
                "total_tokens": sum_input_tokens + sum_output_tokens,
            },
            "route_distribution": route_dist,
            "agent_distribution": agent_dist,
            "skill_distribution": skill_dist,
            "safety_events": safety_events,
            "recent_requests": recent_requests,
        }

    except Exception as e:
        logger.error("get_eval_realtime_stats_failed", error=str(e))
        return {
            "summary": {
                "total_requests": 0,
                "avg_routing_ms": 0,
                "avg_total_ms": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_tokens": 0,
            },
            "route_distribution": {},
            "agent_distribution": {},
            "skill_distribution": {},
            "safety_events": {},
            "recent_requests": [],
        }


async def get_eval_traces(limit: int = 30) -> list[dict]:
    """获取最近 N 条请求链路明细（供链路拆解页面使用）"""
    try:
        r = get_redis()
        today = _today()
        raw = r.zrevrange(f"stats:eval:{today}", 0, limit - 1)
        return [json.loads(rec) for rec in raw]
    except Exception:
        return []
