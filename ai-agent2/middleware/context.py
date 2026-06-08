"""请求上下文管理 — 基于 contextvars 的协程安全实现

替代 services/auth.py 中的全局字典方案。

为什么用 contextvars：
    - 全局字典 + threading.Lock 在高并发下有竞态风险
    - contextvars 是 Python 原生的协程上下文管理，天然适配 asyncio
    - 每个协程有独立的上下文副本，无需加锁
    - FastAPI/LangChain/OpenTelemetry 都用 contextvars

本模块提供：
    - set_request_context / clear_request_context：请求生命周期管理
    - get_token / get_user_id / get_session_id：上下文读取
    - _get_user_id / _get_token：工具层私有接口（向后兼容）
    - _auth_headers：构建后端 API 认证头
"""

import contextvars

# ── 请求级上下文变量 ──
_token_var: contextvars.ContextVar[str] = contextvars.ContextVar('_ai_token', default='')
_user_id_var: contextvars.ContextVar[str] = contextvars.ContextVar('_ai_user_id', default='')
_session_id_var: contextvars.ContextVar[str] = contextvars.ContextVar('_ai_session_id', default='')


# ============================================================
# 请求生命周期
# ============================================================

def set_request_context(session_id: str = "", token: str = "", user_id: str = ""):
    """设置当前请求的上下文（在请求入口调用）"""
    if session_id:
        _session_id_var.set(session_id)
    if token:
        _token_var.set(token)
    if user_id:
        _user_id_var.set(user_id)


def clear_request_context(session_id: str = ""):
    """清理请求上下文（在请求结束时调用）"""
    _token_var.set('')
    _user_id_var.set('')
    _session_id_var.set('')


# ============================================================
# 上下文读取（公开接口）
# ============================================================

def get_token() -> str:
    """获取当前请求的 token"""
    return _token_var.get('')


def get_user_id() -> str:
    """获取当前请求的 user_id"""
    return _user_id_var.get('')


def get_session_id() -> str:
    """获取当前请求的 session_id"""
    return _session_id_var.get('')


# ============================================================
# 工具层接口（向后兼容 services.auth 的私有函数名）
#
# 工具函数中直接调用 _get_user_id() / _get_token() / _auth_headers()
# ============================================================

def _get_user_id(session_id: str = "") -> str:
    """获取当前用户 ID（工具层调用）"""
    return _user_id_var.get('')


def _get_token(session_id: str = "") -> str:
    """获取当前请求的 JWT token（工具层调用）"""
    return _token_var.get('')


def _auth_headers(session_id: str = "") -> dict:
    """构建后端 API 认证头

    优先使用 JWT token（Bearer），如果没有则使用 X-User-Id。
    用于工具函数调用 Spring 后端 API 时携带认证信息。
    """
    token = _token_var.get('')
    user_id = _user_id_var.get('')

    if token:
        return {"Authorization": f"Bearer {token}"}
    if user_id:
        return {"X-User-Id": user_id}
    return {}
