"""业务规则模块 — 动态构建策略提示词"""
from reasoning.prompts.policies.return_policy import RETURN_RULES
from reasoning.prompts.policies.shipping_policy import SHIPPING_RULES
from reasoning.prompts.policies.service_policy import SERVICE_RULES


def build_policy_prompt() -> str:
    """构建业务规则提示词，目前全量注入（约 700 tokens）。
    未来如需按场景裁剪（如售前不加载退货规则），在此函数中增加 context 参数即可。
    """
    return "\n".join([RETURN_RULES, SHIPPING_RULES, SERVICE_RULES])
