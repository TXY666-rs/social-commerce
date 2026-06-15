"""FAQ 模块 — 仅保留问候和功能介绍（零误判风险）

政策FAQ已移除：覆盖场景与Agent重叠，误判率过高。
"""


def match_greeting(message: str) -> str | None:
    """匹配问候语 — 全等判断（避免"你好假啊"误触发）"""
    greetings = {"你好", "在吗", "你是谁", "hi", "hello", "嗨", "您好", "你好呀", "在不在"}
    msg = message.strip().lower()
    if msg in greetings:
        return "您好！我是智能客服助手，可以帮您查询订单、申请退款退货、查询物流、催单、投诉等。请问有什么可以帮您？"
    return None


def match_feature_query(message: str) -> str | None:
    """匹配功能询问 — 包含判断（功能关键词足够长，不易误触发）"""
    keywords = ["有什么功能", "你能做什么", "你能干嘛", "介绍一下功能", "功能列表", "有什么能力", "你能干什么"]
    for kw in keywords:
        if kw in message:
            return (
                "我可以帮您完成以下操作：\n"
                "【订单服务】\n"
                "1. 查询订单 / 取消订单\n"
                "2. 查询物流 / 催促配送\n"
                "【售后服务】\n"
                "3. 申请退款 / 退货\n"
                "4. 查询退款进度 / 取消退款\n"
                "5. 提交投诉\n"
                "6. 转人工客服\n\n"
                "有什么需要帮您处理的吗？"
            )
    return None
