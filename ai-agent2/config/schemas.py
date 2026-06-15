from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    token: Optional[str] = None


class EvalInfo(BaseModel):
    """单次请求的实时评估信息"""
    route_confidence: str = ""       # high / medium / low
    route_reason: str = ""           # 路由决策原因
    safety: dict = {}                # {"injection": false, "pii": false, "leak": false}
    latency: dict = {}               # {"routing_ms": 85, "tool_ms": 320, "total_ms": 1205}
    token: dict = {}                 # {"input": 1200, "output": 350}


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    agent_type: str = ""             # 响应来源：skill / faq / agent
    tools_called: list[str] = []     # 调用的工具列表
    route_source: str = ""           # 路由来源
    skill_name: str = ""             # 触发的 Skill 名称（仅 Skill 路由时有值）
    eval: EvalInfo = EvalInfo()      # 单次请求评估信息
    messages: list[dict] = []        # 转人工模式时返回完整会话历史，供前端实时同步


class MessageHistory(BaseModel):
    role: str
    content: str
    timestamp: str


class UserInfo(BaseModel):
    id: int
    role: Optional[int] = 0


class FeedbackRequest(BaseModel):
    """用户反馈请求"""
    session_id: str
    message_id: Optional[str] = None
    rating: str  # "up" 或 "down"
    comment: Optional[str] = None
    message_content: Optional[str] = None
    token: Optional[str] = None
