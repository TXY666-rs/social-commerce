"""认证服务 —— 本地 Token 解析（重构后不再依赖 Java user-service）

原实现通过 Spring Gateway 的 /api/user/me 验证 JWT。
重构后改为本地解析：支持两种模式
  1. 标准数字 token：直接作为 demo user_id（用于极简前端，无需真实 JWT）
  2. JWT 格式 token：本地解码 payload 提取 user_id（不验签，信任 gateway 已验证）

这样既保留了对外接口兼容性（上层 chat.py / admin.py 零改动），
又彻底解耦了 Java 依赖。
"""

import base64
import json
import structlog
from config.schemas import UserInfo
from typing import Optional

logger = structlog.get_logger(__name__)

# Demo 默认用户（前端无登录态时使用，对应 mock_data 中 user_id=1 的数据）
DEMO_USER_ID = 1
DEMO_USER_ROLE = 0


async def verify_token(token: str) -> Optional[UserInfo]:
    """本地解析 Token 获取用户信息

    Args:
        token: Token 字符串，支持：
               - "demo" / 空 → 返回 demo 用户
               - 纯数字 → 直接作为 user_id
               - JWT 格式（xxx.yyy.zzz）→ 解码 payload 取 sub/userId/id
    Returns:
        UserInfo 对象，解析失败返回 None
    """
    if not token or token == "demo":
        return UserInfo(id=DEMO_USER_ID, role=DEMO_USER_ROLE)

    # 纯数字 token：直接作为 user_id（极简前端模式）
    if token.isdigit():
        return UserInfo(id=int(token), role=DEMO_USER_ROLE)

    # JWT 格式：解码 payload（不验签，信任已验证）
    try:
        parts = token.split(".")
        if len(parts) >= 2:
            # JWT payload 是第 2 段，base64url 编码
            payload_b64 = parts[1]
            # 补齐 base64 padding（标准公式：需补 (4 - len%4) % 4 个 =）
            payload_b64 += "=" * ((4 - len(payload_b64) % 4) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
            user_id = payload.get("userId") or payload.get("user_id") or payload.get("sub") or payload.get("id")
            if user_id and str(user_id).isdigit():
                role = 1 if payload.get("role") in ("ADMIN", 1, "1") else 0
                return UserInfo(id=int(user_id), role=role)
    except Exception as e:
        logger.warning("verify_token_parse_failed", error=str(e))

    return None
