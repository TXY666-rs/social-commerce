"""情感检测模块 — 轻量关键词匹配 + 累计负面计数 + Redis 持久化

三级分类：angry（强愤怒）→ negative（负面）→ neutral（中性）
累计升级：连续3次negative → 升级为angry + 建议转人工

本模块包含：
    - detect_sentiment(): 关键词情感检测
    - get_escalation(): 累计升级计算
    - build_sentiment_context(): Prompt 上下文构建
    - get_sentiment_count() / save_sentiment_count(): Redis 持久化
"""
import json
import structlog
from services.redis_client import get_redis

logger = structlog.get_logger(__name__)

SENTIMENT_TTL = 86400  # 24 小时

# ============================================================
# 关键词表
# ============================================================

# 强愤怒关键词 → 直接判定 angry（单次即触发转人工建议）
ANGRY_KEYWORDS = [
    "垃圾", "骗子", "骗钱", "黑心", "投诉你们", "举报", "差评",
    "气死", "气炸", "什么态度", "不解决我就", "曝光你们",
    "坑人", "无良", "黑店",
]

# 负面关键词 → 判定 negative
NEGATIVE_KEYWORDS = [
    "退款", "退货", "投诉", "差劲", "太慢", "不满意", "失望",
    "问题", "坏", "破损", "烂", "坑", "无语", "敷衍",
    "等多久", "怎么还", "还没到", "没收到", "不处理",
    "什么玩意", "啥玩意", "真是服了", "受不了",
]


# ============================================================
# 检测函数
# ============================================================

def detect_sentiment(message: str) -> str:
    """检测单条消息的情感。

    Returns:
        "angry"    - 强愤怒
        "negative" - 负面情绪
        "neutral"  - 中性
    """
    msg = message.lower()

    # Level 1: 强愤怒关键词（先匹配，优先级最高）
    for kw in ANGRY_KEYWORDS:
        if kw in msg:
            return "angry"

    # Level 2: 负面关键词
    for kw in NEGATIVE_KEYWORDS:
        if kw in msg:
            return "negative"

    return "neutral"


def get_escalation(current_sentiment: str, previous_count: int) -> tuple[str, int, bool]:
    """计算情感升级状态。

    Returns:
        (effective_level, new_count, should_escalate_to_human)
    """
    if current_sentiment == "angry":
        new_count = previous_count + 3
        return ("angry", new_count, True)

    if current_sentiment == "negative":
        new_count = previous_count + 1
        if new_count >= 3:
            return ("angry", new_count, True)
        return ("negative", new_count, False)

    # neutral: 衰减累计计数（但不过快归零，避免情绪反复横跳）
    new_count = max(0, previous_count - 1)
    return ("neutral", new_count, False)


def build_sentiment_context(level: str, cumulative: int) -> str:
    """构建情感感知上下文，注入 System Prompt。

    Returns:
        情感提示段落（neutral 时返回空字符串，不注入）。
    """
    if level == "angry":
        return f"""【用户情绪警告 — 累计负面 {cumulative} 次】
用户当前情绪激动，请务必遵守以下规则：
1. 开头先诚恳道歉和安抚（如"非常抱歉给您带来这么不好的体验"），再进入流程
2. 用最短路径解决用户的核心问题，减少追问和流程
3. 主动建议将问题转接人工客服以获得最优先处理
4. 严禁使用"根据规则""系统显示""这是正常的""请您理解"等可能激化情绪的措辞
5. 如果用户明确拒绝转人工，则快速帮用户完成当前操作，并在结尾再次表达歉意"""

    if level == "negative":
        return f"""【用户情绪提示 — 累计负面 {cumulative} 次】
用户可能有不满情绪，请注意：
1. 回复前先表达理解和歉意（如"确实让人不舒服，我马上帮您处理"）
2. 用最短路径解决用户的核心诉求，减少不必要的信息采集
3. 避免说"这是正常的""请您耐心等待"等可能激化情绪的话
4. 如果问题无法在当前能力范围内解决，主动建议转人工"""

    return ""  # neutral 不注入


# ============================================================
# Redis 持久化 — 累计负面计数
# ============================================================

def get_sentiment_count(session_id: str) -> int:
    """从 Redis 读取累计负面次数"""
    if not session_id:
        return 0
    try:
        r = get_redis()
        key = f"chat::ai::sentiment::{session_id}"
        raw = r.get(key)
        if raw:
            data = json.loads(raw)
            return data.get("cumulative_negative", 0)
    except Exception:
        pass
    return 0


def save_sentiment_count(session_id: str, count: int) -> None:
    """保存累计负面次数到 Redis"""
    if not session_id:
        return
    try:
        r = get_redis()
        key = f"chat::ai::sentiment::{session_id}"
        data = json.dumps({"cumulative_negative": count})
        r.setex(key, SENTIMENT_TTL, data)
    except Exception as e:
        logger.warning("save_sentiment_failed", error=str(e), session_id=session_id)


# ============================================================
# 异步版本 — 供 async 上下文使用（不阻塞事件循环）
# ============================================================

async def async_get_sentiment_count(session_id: str) -> int:
    """异步版本：从 Redis 读取累计负面次数"""
    if not session_id:
        return 0
    try:
        from services.redis_client import get_async_redis
        r = get_async_redis()
        key = f"chat::ai::sentiment::{session_id}"
        raw = await r.get(key)
        if raw:
            data = json.loads(raw)
            return data.get("cumulative_negative", 0)
    except Exception:
        pass
    return 0


async def async_save_sentiment_count(session_id: str, count: int) -> None:
    """异步版本：保存累计负面次数到 Redis"""
    if not session_id:
        return
    try:
        from services.redis_client import get_async_redis
        r = get_async_redis()
        key = f"chat::ai::sentiment::{session_id}"
        data = json.dumps({"cumulative_negative": count})
        await r.setex(key, SENTIMENT_TTL, data)
    except Exception as e:
        logger.warning("async_save_sentiment_failed", error=str(e), session_id=session_id)
