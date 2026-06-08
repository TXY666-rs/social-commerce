from typing import Optional
from fastapi import Header
from config.schemas import UserInfo
from services.auth import verify_token


async def resolve_user(
    x_user_id: Optional[str] = Header(None),
    x_user_role: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
    body_token: Optional[str] = None,
) -> UserInfo:
    if x_user_id:
        role_str = x_user_role or "USER"
        role = 1 if role_str == "ADMIN" else 0
        return UserInfo(id=int(x_user_id), role=role)

    token = None
    if authorization:
        token = authorization[7:] if authorization.startswith("Bearer ") else authorization
    if not token and body_token:
        token = body_token
    if not token:
        return None

    return await verify_token(token)
