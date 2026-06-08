-- =============================================
-- 数据库索引优化脚本
-- 适用于 PostgreSQL
-- =============================================

-- ========== 商品表 (product) ==========
CREATE INDEX IF NOT EXISTS idx_product_category ON product(category);
CREATE INDEX IF NOT EXISTS idx_product_status ON product(status);
CREATE INDEX IF NOT EXISTS idx_product_seller_id ON product(seller_id);
CREATE INDEX IF NOT EXISTS idx_product_create_time ON product(create_time DESC);
CREATE INDEX IF NOT EXISTS idx_product_status_create_time ON product(status, create_time DESC);

-- ========== 订单表 ("order") ==========
CREATE INDEX IF NOT EXISTS idx_order_user_id ON "order"(user_id);
CREATE INDEX IF NOT EXISTS idx_order_seller_id ON "order"(seller_id);
CREATE INDEX IF NOT EXISTS idx_order_product_id ON "order"(product_id);
CREATE INDEX IF NOT EXISTS idx_order_status ON "order"(status);
CREATE INDEX IF NOT EXISTS idx_order_create_time ON "order"(create_time DESC);
CREATE INDEX IF NOT EXISTS idx_order_user_id_status ON "order"(user_id, status);
CREATE INDEX IF NOT EXISTS idx_order_seller_id_status ON "order"(seller_id, status);

-- ========== 优惠券表 (coupon) ==========
CREATE INDEX IF NOT EXISTS idx_coupon_status ON coupon(status);
CREATE INDEX IF NOT EXISTS idx_coupon_end_time ON coupon(end_time);
CREATE INDEX IF NOT EXISTS idx_coupon_status_end_time ON coupon(status, end_time);

-- ========== 用户优惠券表 (user_coupon) ==========
CREATE INDEX IF NOT EXISTS idx_user_coupon_user_id ON user_coupon(user_id);
CREATE INDEX IF NOT EXISTS idx_user_coupon_coupon_id ON user_coupon(coupon_id);
CREATE INDEX IF NOT EXISTS idx_user_coupon_user_coupon ON user_coupon(user_id, coupon_id);
CREATE INDEX IF NOT EXISTS idx_user_coupon_status ON user_coupon(status);

-- ========== 分类表 (category) ==========
CREATE INDEX IF NOT EXISTS idx_category_status ON category(status);
CREATE INDEX IF NOT EXISTS idx_category_sort_order ON category(sort_order);
