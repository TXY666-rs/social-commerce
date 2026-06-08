"""认证服务 — JWT Token 验证

通过 Spring Gateway 验证 JWT Token 并获取用户信息。

注意：请求上下文管理（token/user_id/session_id 的存取）已迁移到
      middleware/context.py（基于 contextvars，协程安全）。
"""

import httpx
import structlog
from config import settings
from config.schemas import UserInfo
from typing import Optional

logger = structlog.get_logger(__name__)


async def verify_token(token: str) -> Optional[UserInfo]:
    """通过 Spring Gateway 验证 JWT Token 并获取用户信息

    Args:
        token: JWT Token 字符串

    Returns:
        UserInfo 对象（包含 id 和 role），验证失败返回 None
    """
    if not token:
        return None
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            url = f"{settings.SPRING_GATEWAY_URL}/api/user/me"
            logger.info("verify_token_request", url=url)
            resp = await client.get(
                url,
                headers={"Authorization": f"Bearer {token}"}
            )
            logger.info("verify_token_response", status_code=resp.status_code)
            if resp.status_code == 200:
                data = resp.json()
                user_data = data.get("data", data)
                if isinstance(user_data, dict):
                    user_id = user_data.get("X-User-Id") or user_data.get("id") or user_data.get("userId")
                    if user_id:
                        logger.info("user_resolved", user_id=user_id)
                        return UserInfo(
                            id=int(user_id),
                            role=user_data.get("role", 0),
                        )
    except Exception as e:
        logger.error("verify_token_exception", error=str(e))
    return None
