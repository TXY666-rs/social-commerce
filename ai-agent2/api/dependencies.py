"""API 依赖注入 — 全局单例的 getter/setter"""
from memory import SessionManager

_session_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    assert _session_manager is not None, "SessionManager 未初始化，请先调用 set_session_manager()"
    return _session_manager


def set_session_manager(sm: SessionManager):
    global _session_manager
    _session_manager = sm
