def build_dialog_context(messages: list, max_turns: int = 3) -> str:
    """从消息列表构建对话进度上下文。

    提取最近 max_turns 轮用户-助手对话，格式化为可读摘要。
    少于 2 条用户消息时不构建（上下文不足）。

    Args:
        messages: 消息列表（dict 或 LangChain Message 对象）
        max_turns: 最大提取轮数

    Returns:
        对话进度提示段落（空字符串 = 历史不足，不注入）
    """
    turns = _extract_recent_turns(messages, max_turns)

    if len(turns) < 2:
        return ""

    lines = ["【对话进度提示】"]
    lines.append("以下是最近几轮对话的关键信息，请基于此判断用户当前需求，避免重复询问已确认的内容：")

    for i, turn in enumerate(turns):
        user_text = turn.get("user", "")[:100]
        assistant_text = turn.get("assistant", "")[:100]
        lines.append(f"- 第{i+1}轮 用户：{user_text}")
        if assistant_text:
            lines.append(f"  第{i+1}轮 客服：{assistant_text}")

    lines.append("\n注意：如果用户的问题在上文已经明确过（如已确认要退哪一单），请直接基于已有信息继续，不要重新询问。")

    return "\n".join(lines)


def _extract_recent_turns(messages: list, max_turns: int = 3) -> list[dict]:
    """从消息列表中提取最近的用户-助手对话轮次。"""
    turns = []
    current_turn = {}

    for msg in messages:
        role, content = _parse_message(msg)
        if not content:
            continue

        if role == "user":
            if current_turn:
                turns.append(current_turn)
            current_turn = {"user": content}
        elif role == "assistant" and current_turn:
            current_turn["assistant"] = content

    if current_turn and current_turn.get("user"):
        turns.append(current_turn)

    return turns[-max_turns:]


def _parse_message(msg) -> tuple[str, str]:
    """解析消息，返回 (role, content)。"""
    if isinstance(msg, dict):
        return msg.get("role", ""), msg.get("content", "")
    if hasattr(msg, "type") and hasattr(msg, "content"):
        role = "user" if msg.type == "human" else "assistant"
        return role, msg.content
    return "", str(msg)
