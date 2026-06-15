from typing import Optional
from fastapi import Header
from config.schemas import UserInfo
from services.auth import verify_token, DEMO_USER_ID, DEMO_USER_ROLE


async def resolve_user(
    x_user_id: Optional[str] = Header(None),
    x_user_role: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
    body_token: Optional[str] = None,
) -> UserInfo:
    """解析当前请求的用户身份

    优先级（重构后不再强依赖 Java Gateway）：
      1. X-User-Id header（Gateway 注入，若存在直接信任）
      2. JWT Token（本地解码，见 services/auth.verify_token）
      3. 兜底：返回 demo 用户（user_id=1），保证无登录态也能体验 Agent
    """
    if x_user_id:
        role_str = x_user_role or "USER"
        role = 1 if role_str == "ADMIN" else 0
        return UserInfo(id=int(x_user_id), role=role)

    token = None
    if authorization:
        token = authorization[7:] if authorization.startswith("Bearer ") else authorization
    if not token and body_token:
        token = body_token[7:] if body_token.startswith("Bearer ") else body_token

    if token:
        user = await verify_token(token)
        if user:
            return user

    # 兜底：无认证信息时返回 demo 用户（极简前端场景）
    return UserInfo(id=DEMO_USER_ID, role=DEMO_USER_ROLE)
