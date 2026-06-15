"""core/sentiment.py 单元测试

覆盖函数：
    - detect_sentiment():       关键词情感检测（三级分类）
    - get_escalation():         累计升级计算
    - build_sentiment_context(): Prompt 情感上下文构建
    - get_sentiment_count():    Redis 读取累计负面次数
    - save_sentiment_count():   Redis 保存累计负面次数

情感模型：
    三级分类：angry（强愤怒）→ negative（负面）→ neutral（中性）
    累计升级：连续 3 次 negative → 升级为 angry + 建议转人工
"""

import json
from unittest.mock import patch, MagicMock

import pytest

from core.sentiment import (
    detect_sentiment,
    get_escalation,
    build_sentiment_context,
    get_sentiment_count,
    save_sentiment_count,
    ANGRY_KEYWORDS,
    NEGATIVE_KEYWORDS,
    SENTIMENT_TTL,
)


# ============================================================
# 1. detect_sentiment() — 关键词情感检测
# ============================================================

class TestDetectSentiment:
    """测试关键词情感检测"""

    # ── angry 关键词（每个都测试）──

    @pytest.mark.parametrize("keyword", ANGRY_KEYWORDS, ids=ANGRY_KEYWORDS)
    def test_angry_keyword_detected(self, keyword):
        """每个强愤怒关键词都应被检测为 angry"""
        message = f"这个服务真是{keyword}，太差了"
        assert detect_sentiment(message) == "angry"

    def test_angry_keyword_alone(self):
        """单独的愤怒关键词也能检测"""
        assert detect_sentiment("骗子") == "angry"

    def test_angry_keyword_in_sentence(self):
        """关键词在完整句子中仍能被检测"""
        assert detect_sentiment("你们就是骗子，太过分了") == "angry"

    def test_angry_garbage(self):
        """'垃圾' 检测为 angry"""
        assert detect_sentiment("这个系统真是垃圾") == "angry"

    def test_angry_complaint(self):
        """'投诉你们' 检测为 angry"""
        assert detect_sentiment("我要投诉你们") == "angry"

    def test_angry_expose(self):
        """'曝光你们' 检测为 angry"""
        assert detect_sentiment("我要曝光你们") == "angry"

    # ── negative 关键词（每个都测试）──

    @pytest.mark.parametrize("keyword", NEGATIVE_KEYWORDS, ids=NEGATIVE_KEYWORDS)
    def test_negative_keyword_detected(self, keyword):
        """每个负面关键词都应被检测为 negative（前提是不包含 angry 关键词）"""
        # 确保测试的关键词本身不触发 angry
        message = f"我{keyword}了"
        result = detect_sentiment(message)
        # 结果应该是 negative 或 angry（如果该消息同时命中 angry）
        assert result in ("negative", "angry")

    def test_negative_refund(self):
        """'退款' 检测为 negative"""
        assert detect_sentiment("我想退款") == "negative"

    def test_negative_return(self):
        """'退货' 检测为 negative"""
        assert detect_sentiment("这个质量太差，我要退货") == "negative"

    def test_negative_slow(self):
        """'太慢' 检测为 negative"""
        assert detect_sentiment("物流太慢了") == "negative"

    def test_negative_disappointed(self):
        """'失望' 检测为 negative"""
        assert detect_sentiment("对你们的服务很失望") == "negative"

    def test_negative_not_received(self):
        """'没收到' 检测为 negative"""
        assert detect_sentiment("我的包裹还没收到") == "negative"

    def test_negative_unsatisfied(self):
        """'不满意' 检测为 negative"""
        assert detect_sentiment("对处理结果不满意") == "negative"

    # ── neutral（中性消息）──

    def test_neutral_greeting(self):
        """普通问候为 neutral"""
        assert detect_sentiment("你好") == "neutral"

    def test_neutral_order_query(self):
        """订单查询为 neutral"""
        assert detect_sentiment("帮我查一下订单状态") == "neutral"

    def test_neutral_product_question(self):
        """商品咨询为 neutral"""
        assert detect_sentiment("这个商品有什么颜色？") == "neutral"

    def test_neutral_thanks(self):
        """感谢为 neutral"""
        assert detect_sentiment("谢谢你，已经解决了") == "neutral"

    def test_neutral_address_update(self):
        """地址变更为 neutral"""
        assert detect_sentiment("我想修改收货地址") == "neutral"

    def test_neutral_empty(self):
        """空消息为 neutral"""
        assert detect_sentiment("") == "neutral"

    # ── 优先级：angry 优先于 negative ──

    def test_angry_takes_priority_over_negative(self):
        """同时包含 angry 和 negative 关键词时，angry 优先"""
        # "垃圾" 是 angry，"退款" 是 negative
        assert detect_sentiment("垃圾服务，我要退款") == "angry"

    def test_angry_wins_with_multiple_keywords(self):
        """多个关键词混合时 angry 优先"""
        assert detect_sentiment("我要投诉你们，退款太慢了") == "angry"

    # ── 大小写不敏感 ──

    def test_case_insensitivity_angry(self):
        """英文/混合关键词大小写不敏感（当前实现 .lower()）"""
        # 中文关键词本身无大小写，但检测函数做了 .lower()
        # 验证 .lower() 不影响中文关键词匹配
        assert detect_sentiment("骗子".upper()) == "angry" or detect_sentiment("骗子") == "angry"

    def test_lowercase_conversion(self):
        """消息先转小写再匹配"""
        # 中文不受 lower() 影响，确保正常
        assert detect_sentiment("我要投诉你们") == "angry"


# ============================================================
# 2. get_escalation() — 累计升级计算
# ============================================================

class TestGetEscalation:
    """测试情感升级逻辑"""

    # ── angry → 直接加 3 并升级 ──

    def test_angry_always_escalates(self):
        """angry 情绪：无论之前计数多少，都加 3 并建议转人工"""
        level, count, escalate = get_escalation("angry", 0)
        assert level == "angry"
        assert count == 3
        assert escalate is True

    def test_angry_with_existing_count(self):
        """angry + 已有计数：累加 3"""
        level, count, escalate = get_escalation("angry", 5)
        assert level == "angry"
        assert count == 8
        assert escalate is True

    def test_angry_with_high_count(self):
        """angry + 高计数：仍然累加 3"""
        level, count, escalate = get_escalation("angry", 100)
        assert level == "angry"
        assert count == 103
        assert escalate is True

    # ── negative + count=0 → (negative, 1, False) ──

    def test_negative_from_zero(self):
        """negative + count=0 → (negative, 1, False)"""
        level, count, escalate = get_escalation("negative", 0)
        assert level == "negative"
        assert count == 1
        assert escalate is False

    # ── negative + count=1 → (negative, 2, False) ──

    def test_negative_from_one(self):
        """negative + count=1 → (negative, 2, False)"""
        level, count, escalate = get_escalation("negative", 1)
        assert level == "negative"
        assert count == 2
        assert escalate is False

    # ── negative + count=2 → (angry, 3, True) — 累计升级！──

    def test_negative_escalates_at_three(self):
        """negative + count=2 → (angry, 3, True) — 累计 3 次升级"""
        level, count, escalate = get_escalation("negative", 2)
        assert level == "angry"
        assert count == 3
        assert escalate is True

    def test_negative_above_threshold_stays_angry(self):
        """negative + count>2 → (angry, count+1, True)"""
        level, count, escalate = get_escalation("negative", 5)
        assert level == "angry"
        assert count == 6
        assert escalate is True

    # ── neutral → 衰减计数 ──

    def test_neutral_decays_count(self):
        """neutral：计数衰减 -1"""
        level, count, escalate = get_escalation("neutral", 3)
        assert level == "neutral"
        assert count == 2
        assert escalate is False

    def test_neutral_decays_from_one(self):
        """neutral + count=1 → (neutral, 0, False)"""
        level, count, escalate = get_escalation("neutral", 1)
        assert level == "neutral"
        assert count == 0
        assert escalate is False

    def test_neutral_at_zero_stays_zero(self):
        """neutral + count=0 → (neutral, 0, False) — 不会变成负数"""
        level, count, escalate = get_escalation("neutral", 0)
        assert level == "neutral"
        assert count == 0
        assert escalate is False


# ============================================================
# 3. build_sentiment_context() — Prompt 情感上下文构建
# ============================================================

class TestBuildSentimentContext:
    """测试情感上下文构建"""

    def test_angry_returns_apology_rules(self):
        """angry 级别返回包含道歉规则的上下文"""
        ctx = build_sentiment_context("angry", 5)
        assert "用户情绪警告" in ctx
        assert "道歉" in ctx or "诚恳" in ctx
        assert "人工客服" in ctx or "转接" in ctx
        assert "5" in ctx  # 累计次数

    def test_angry_context_contains_all_rules(self):
        """angry 上下文包含完整的 5 条规则"""
        ctx = build_sentiment_context("angry", 3)
        # 验证关键规则存在
        assert "最短路径" in ctx
        assert "严禁" in ctx or "禁止" in ctx or "激化" in ctx

    def test_negative_returns_softer_rules(self):
        """negative 级别返回较温和的上下文"""
        ctx = build_sentiment_context("negative", 2)
        assert "用户情绪提示" in ctx
        assert "理解" in ctx or "歉意" in ctx
        assert "2" in ctx  # 累计次数

    def test_negative_context_suggests_transfer(self):
        """negative 上下文也建议转人工"""
        ctx = build_sentiment_context("negative", 1)
        assert "人工" in ctx or "转人工" in ctx

    def test_neutral_returns_empty(self):
        """neutral 级别返回空字符串（不注入）"""
        ctx = build_sentiment_context("neutral", 0)
        assert ctx == ""

    def test_neutral_with_high_count_still_empty(self):
        """neutral 即使有高计数也返回空（不注入）"""
        ctx = build_sentiment_context("neutral", 10)
        assert ctx == ""


# ============================================================
# 4. get_sentiment_count() / save_sentiment_count() — Redis 持久化
# ============================================================

class TestSentimentRedisPersistence:
    """测试情感计数的 Redis 持久化"""

    def test_save_and_get_count(self):
        """保存后能读取累计负面次数"""
        mock_r = MagicMock()
        mock_r.get.return_value = json.dumps({"cumulative_negative": 5})

        with patch("core.sentiment.get_redis", return_value=mock_r):
            count = get_sentiment_count("session_123")
            assert count == 5

    def test_get_count_returns_zero_when_no_data(self):
        """Redis 无数据时返回 0"""
        mock_r = MagicMock()
        mock_r.get.return_value = None

        with patch("core.sentiment.get_redis", return_value=mock_r):
            count = get_sentiment_count("session_456")
            assert count == 0

    def test_get_count_empty_session_id(self):
        """空 session_id 返回 0"""
        assert get_sentiment_count("") == 0
        assert get_sentiment_count(None) == 0

    def test_get_count_handles_redis_error(self):
        """Redis 异常时返回 0（不抛出）"""
        mock_r = MagicMock()
        mock_r.get.side_effect = ConnectionError("Redis 连接失败")

        with patch("core.sentiment.get_redis", return_value=mock_r):
            count = get_sentiment_count("session_789")
            assert count == 0

    def test_save_count_calls_setex(self):
        """save_sentiment_count 调用 Redis setex 并设置正确 TTL"""
        mock_r = MagicMock()

        with patch("core.sentiment.get_redis", return_value=mock_r):
            save_sentiment_count("session_abc", 7)
            mock_r.setex.assert_called_once()
            # 验证 key 格式
            call_args = mock_r.setex.call_args
            key = call_args[0][0]
            assert "session_abc" in key
            # 验证 TTL
            ttl = call_args[0][1]
            assert ttl == SENTIMENT_TTL
            # 验证 value 包含正确的计数
            value = json.loads(call_args[0][2])
            assert value["cumulative_negative"] == 7

    def test_save_count_empty_session_id_does_nothing(self):
        """空 session_id 不调用 Redis"""
        mock_r = MagicMock()

        with patch("core.sentiment.get_redis", return_value=mock_r):
            save_sentiment_count("", 5)
            mock_r.setex.assert_not_called()

    def test_save_count_none_session_id_does_nothing(self):
        """None session_id 不调用 Redis"""
        mock_r = MagicMock()

        with patch("core.sentiment.get_redis", return_value=mock_r):
            save_sentiment_count(None, 5)
            mock_r.setex.assert_not_called()

    def test_save_count_handles_redis_error(self):
        """Redis 写入异常时不抛出"""
        mock_r = MagicMock()
        mock_r.setex.side_effect = ConnectionError("Redis 写入失败")

        with patch("core.sentiment.get_redis", return_value=mock_r):
            # 不应抛出异常
            save_sentiment_count("session_err", 3)


# ============================================================
# 5. 关键词完整性校验
# ============================================================

class TestKeywordLists:
    """测试关键词列表的完整性"""

    def test_angry_keywords_not_empty(self):
        """强愤怒关键词列表不为空"""
        assert len(ANGRY_KEYWORDS) > 0

    def test_negative_keywords_not_empty(self):
        """负面关键词列表不为空"""
        assert len(NEGATIVE_KEYWORDS) > 0

    def test_no_overlap_between_angry_and_negative(self):
        """angry 和 negative 关键词列表不应有重复"""
        overlap = set(ANGRY_KEYWORDS) & set(NEGATIVE_KEYWORDS)
        assert len(overlap) == 0, f"关键词重复: {overlap}"

    def test_all_angry_keywords_detected(self):
        """确保每个 angry 关键词都能被 detect_sentiment 识别"""
        for kw in ANGRY_KEYWORDS:
            assert detect_sentiment(kw) == "angry", f"关键词 '{kw}' 未被识别为 angry"

    def test_all_negative_keywords_detected(self):
        """确保每个负面关键词都能被 detect_sentiment 识别（至少为 negative）"""
        for kw in NEGATIVE_KEYWORDS:
            result = detect_sentiment(kw)
            assert result in ("negative", "angry"), \
                f"关键词 '{kw}' 未被识别（结果={result}）"
