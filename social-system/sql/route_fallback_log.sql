-- 路由降级日志表
-- 记录 AI Agent 路由未命中时的降级情况，用于驱动关键词表迭代优化

CREATE TABLE IF NOT EXISTS route_fallback_log (
    id              BIGSERIAL PRIMARY KEY,
    message         VARCHAR(500),           -- 原始用户消息
    keyword_result  VARCHAR(50),            -- 关键词命中的领域（NULL=未命中）
    keyword_score   INT DEFAULT 0,          -- 关键词最高分
    llm_result      VARCHAR(50),            -- LLM 返回的领域（NULL=失败）
    llm_error       VARCHAR(200),           -- LLM 错误信息
    user_choice     VARCHAR(50),            -- 用户选择的领域（回填）
    created_at      TIMESTAMP DEFAULT NOW() -- 创建时间
);

-- 按时间查询降级日志
CREATE INDEX IF NOT EXISTS idx_route_fallback_created_at ON route_fallback_log(created_at);

-- 按用户选择分布统计
CREATE INDEX IF NOT EXISTS idx_route_fallback_user_choice ON route_fallback_log(user_choice);

COMMENT ON TABLE route_fallback_log IS 'AI Agent 路由降级日志';
COMMENT ON COLUMN route_fallback_log.message IS '原始用户消息';
COMMENT ON COLUMN route_fallback_log.keyword_result IS '关键词命中的领域（NULL=未命中）';
COMMENT ON COLUMN route_fallback_log.keyword_score IS '关键词最高分';
COMMENT ON COLUMN route_fallback_log.llm_result IS 'LLM 返回的领域（NULL=失败）';
COMMENT ON COLUMN route_fallback_log.llm_error IS 'LLM 错误信息';
COMMENT ON COLUMN route_fallback_log.user_choice IS '用户选择的领域（回填）';
