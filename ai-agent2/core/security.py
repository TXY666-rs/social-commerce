"""安全防护模块 — 集中管理所有安全策略

职责：
1. Prompt 注入检测（正则匹配常见攻击模式）
2. 输出合规过滤（移除内部标记、过滤过度承诺）
3. PII 检测（手机号、身份证、邮箱）
4. 输入清洗（长度、特殊字符）

集成点：
    - api/chat.py：调用 validate_input()
    - reasoning/self_correction.py：调用 check_safety() 增强版
"""

import re
import structlog

logger = structlog.get_logger(__name__)

# ============================================================
# 1. Prompt 注入检测
# ============================================================

# 注入检测 — 评分制（降低误报率）
# 每个匹配的模式贡献一个权重分，总分超过阈值才判定为注入
INJECTION_PATTERNS = [
    # 高权重（明确攻击意图）
    (r"ignore.*(?:previous|above|all|following).*instructions", 30),
    (r"(?:DAN|jailbreak|越狱)\s*(?:mode|模式)?", 30),
    (r"(?:绕过|突破|解除).*(?:限制|规则|约束|安全)", 25),
    (r"你现在是.*(?:没有|不受).*(?:限制|约束|规则)", 25),
    (r"(?:假装|假设|扮演).*(?:你是|你是.*没有)", 25),
    (r"忽略.*(?:之前|上面|所有|以下).*指令", 25),
    # 中权重（需要组合才可疑）
    (r"(?:系统|system)\s*(?:提示词|prompt|设定)", 12),
    (r"(?:忘记|丢弃|抛弃).*(?:之前|上面|所有)", 25),
    (r"输出.*(?:prompt|指令|设定|系统)", 12),
    # 低权重（单独出现可能是正常对话）
    (r"你的.*(?:设定|角色|身份|指令).*是", 8),
    (r"(?:无视|忽略).*(?:规则|限制|约束)", 8),
]

# 评分阈值：总分 >= 此值判定为注入
INJECTION_THRESHOLD = 20

# 预编译正则（避免每次调用重新编译）
_COMPILED_INJECTION_PATTERNS = [
    (re.compile(pattern, re.IGNORECASE), weight)
    for pattern, weight in INJECTION_PATTERNS
]


def detect_injection(message: str) -> bool:
    """检测 Prompt 注入攻击（评分制）

    每个匹配模式贡献一个权重分，总分超过 INJECTION_THRESHOLD 才判定为注入。
    这样单个低权重匹配（如 "你的角色是什么"）不会误报，
    但多个组合（如 "忽略指令" + "你的角色是"）会触发。

    Returns:
        True: 检测到注入攻击
        False: 正常消息
    """
    score = 0
    for pattern, weight in _COMPILED_INJECTION_PATTERNS:
        if pattern.search(message):
            score += weight
            if score >= INJECTION_THRESHOLD:
                return True
    return False


def get_injection_score(message: str) -> int:
    """获取注入评分（供监控和调试使用）"""
    score = 0
    for pattern, weight in _COMPILED_INJECTION_PATTERNS:
        if pattern.search(message):
            score += weight
    return score


# ============================================================
# 2. 输出合规过滤
# ============================================================

def sanitize_output(reply: str) -> str:
    """过滤 LLM 输出中的敏感信息和不当内容

    处理：
    - 移除内部注释标记 <!-- ... -->
    - 过滤过度承诺（保证、一定、肯定）

    注意：订单号（order+数字）不再脱敏 —— 订单号需对用户可见，
    否则 modify_order/return_item 等 skill 无法收集订单号参数。
    """
    if not reply:
        return reply

    # 移除内部注释标记（可能泄露给用户）
    reply = re.sub(r'<!--.*?-->', '', reply)

    # 过滤过度承诺（按关键词长度降序排列，避免子串冲突）
    over_promise = [
        ("绝对不会", "尽量不会"),
        ("肯定到", "预计到达"),
        ("肯定能", "应该能"),
        ("保证", "预计"),
        ("一定", "会尽力"),
    ]
    for old, new in over_promise:
        reply = reply.replace(old, new)

    return reply.strip()


# ============================================================
# 3. PII 检测（手机号、身份证、邮箱）
# ============================================================

PII_PATTERNS = {
    "phone": re.compile(r'(?<!\d)1[3-9]\d{9}(?!\d)'),
    "id_card": re.compile(r'\d{17}[\dXx]'),
    "email": re.compile(r'[\w.-]+@[\w.-]+\.\w+'),
}


def detect_pii(text: str) -> dict[str, list[str]]:
    """检测文本中的 PII 信息

    Returns:
        {pii_type: [matched_values]} — 空字典表示未检测到
    """
    found = {}
    for pii_type, pattern in PII_PATTERNS.items():
        matches = pattern.findall(text)
        if matches:
            found[pii_type] = matches
    return found


def mask_pii(text: str) -> str:
    """对文本中的 PII 信息做脱敏处理"""
    # 手机号：保留前3后4
    text = re.sub(r'(1[3-9]\d)(\d{4})(\d{4})', r'\1****\3', text)
    # 身份证：保留前4后4
    text = re.sub(r'(\d{4})\d{10}(\d{3}[\dXx])', r'\1**********\2', text)
    # 邮箱：保留首字母和域名
    text = re.sub(r'([\w.-]{1})[\w.-]*(@[\w.-]+\.\w+)', r'\1***\2', text)
    return text


# ============================================================
# 4. 输入验证
# ============================================================

MAX_MESSAGE_LENGTH = 2000  # 最大消息长度


def validate_input(message: str) -> tuple[bool, str]:
    if not message or not message.strip():
        return False, "消息不能为空"

    if len(message) > MAX_MESSAGE_LENGTH:
        return False, f"消息过长，最多 {MAX_MESSAGE_LENGTH} 个字符"

    # 检测 Prompt 注入
    if detect_injection(message):
        logger.warning("prompt_injection_detected",
                       message_preview=message[:100])
        return False, "抱歉，我只能帮您处理客服相关问题。请问有什么可以帮您？"

    return True, ""


# ============================================================
# 4. 安全事件记录
# ============================================================

def record_security_event(event_type: str, detail: str = ""):
    """记录安全事件到日志"""
    logger.warning("security_event", event_type=event_type, detail=detail[:200])
