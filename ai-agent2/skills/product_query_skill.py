"""商品查询 Skill — 搜索商品+优惠券

流程：
1. 识别意图（商品查询/优惠券）
2. 商品查询：复用 goods_tool._do_search 搜索商品 → 展示结果
3. 优惠券：复用 coupon_tool 的 Tool 函数
"""
import structlog

from skills.base import BaseSkill, ParamDef, SkillState
from agents.tools.constants import NOT_LOGGED_IN_MSG
from agents.tools.goods_tool import _do_search
from agents.tools.coupon_tool import get_available_coupons, get_my_coupons

logger = structlog.get_logger(__name__)


class ProductQuerySkill(BaseSkill):
    name = "product_query"
    description = "商品查询：搜索商品、查优惠券、领取优惠券"
    trigger_keywords = ["商品", "搜索", "找商品", "推荐", "有什么", "有什么好的",
                        "优惠券", "券", "打折", "领券", "我的券", "有什么券"]

    params = [
        ParamDef(
            name="keyword",
            ask_prompt="请问您想搜索什么商品？",
            extractor="raw",
            required=False,  # 可选，用户可能直接说"有什么优惠券"
            skip_on_trigger=True,  # 触发消息"有什么好的"不是搜索关键词
        ),
    ]

    def _detect_intent(self, message: str) -> str:
        """检测意图：product/coupon"""
        msg_lower = message.lower()
        coupon_keywords = ["优惠券", "券", "打折", "领券", "我的券", "有什么券"]
        if any(kw in msg_lower for kw in coupon_keywords):
            return "coupon"
        return "product"

    async def execute(self, state: SkillState, user_id: str) -> str:
        """执行商品查询"""
        intent = self._detect_intent(state.context.get("original_message", ""))

        if intent == "coupon":
            return await self._handle_coupon(state, user_id)
        else:
            return await self._handle_product(state, user_id)

    async def _handle_product(self, state: SkillState, user_id: str) -> str:
        """处理商品查询 — 复用 goods_tool._do_search"""
        keyword = state.collected.get("keyword", "")
        if not keyword:
            return "好的，想帮您找找看～请问您想搜索什么商品呢？"

        try:
            products, total = _do_search(keyword, "", 0, 0)
            if not products:
                return f"没找到与「{keyword}」相关的商品，换个关键词试试？"

            lines = [f"好的，为您找到 {total} 个相关商品：\n"]
            for i, p in enumerate(products[:5], 1):
                name = p.get("name", "未知商品")
                price = p.get("price", 0)
                sales = p.get("sales", 0)
                stock = p.get("stock", 0)
                lines.append(
                    f"【{i}】{name}\n"
                    f"   价格: ¥{price}  销量: {sales}  库存: {stock}"
                )

            if total > 5:
                lines.append(f"\n...还有 {total - 5} 个商品，可以告诉我更具体的需求。")

            return "\n".join(lines)
        except Exception as e:
            logger.error("search_products_failed", error=str(e))
            return "搜索商品时出现问题，请稍后重试。"

    async def _handle_coupon(self, state: SkillState, user_id: str) -> str:
        """处理优惠券查询 — 复用 coupon_tool 的 Tool 函数"""
        if not user_id:
            return NOT_LOGGED_IN_MSG.format(action="查看优惠券")

        keyword = state.collected.get("keyword", "")
        msg_lower = keyword.lower() if keyword else ""

        # 判断是查可领、查已领、还是领取
        if any(kw in msg_lower for kw in ["我的", "已领", "领取了"]):
            return get_my_coupons.invoke({"status": -1})
        elif any(kw in msg_lower for kw in ["领", "领取"]):
            return "请提供优惠券ID（纯数字），我来帮您领取。"
        else:
            return get_available_coupons.invoke({})
