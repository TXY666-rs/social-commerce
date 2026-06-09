#!/bin/bash
set -e

echo "========================================"
echo "  Initializing social-commerce databases"
echo "========================================"

# --- 1. Create databases ---
DATABASES=(social_user social_order social_coupon social_product social_memory)

for db in "${DATABASES[@]}"; do
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    SELECT 'CREATE DATABASE $db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$db')\gexec
EOSQL
  echo "[OK] Database '$db' ready"
done

# --- 2. Load schemas ---

# user-service
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname social_user <<'EOSQL'
CREATE TABLE IF NOT EXISTS "user" (
    id              BIGINT,
    username        VARCHAR(50),
    nickname        VARCHAR(50),
    password        VARCHAR(100),
    email           VARCHAR(100),
    phone           VARCHAR(20),
    avatar          VARCHAR(255),
    gender          SMALLINT,
    birthday        DATE,
    signature       VARCHAR(255),
    status          SMALLINT,
    last_login_time TIMESTAMP,
    last_login_ip   VARCHAR(50),
    is_deleted      SMALLINT,
    create_time     TIMESTAMP,
    update_time     TIMESTAMP,
    online_status   SMALLINT,
    role            SMALLINT
);
EOSQL
echo "[OK] social_user schema loaded"

# order-service (order + address + complaint + refund)
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname social_order <<'EOSQL'
CREATE TABLE IF NOT EXISTS "order" (
    id               VARCHAR(20) NOT NULL PRIMARY KEY,
    user_id          BIGINT,
    product_id       BIGINT,
    quantity         INTEGER,
    total_price      NUMERIC(10, 2),
    status           SMALLINT,
    receiver_name    VARCHAR(50),
    receiver_phone   VARCHAR(20),
    receiver_address VARCHAR(255),
    pay_time         TIMESTAMP,
    delivery_time    TIMESTAMP,
    complete_time    TIMESTAMP,
    remark           VARCHAR(255),
    is_deleted       SMALLINT,
    create_time      TIMESTAMP,
    update_time      TIMESTAMP,
    seller_id        BIGINT,
    original_price   NUMERIC(10, 2),
    discount_amount  NUMERIC(10, 2),
    user_coupon_id   BIGINT,
    tracking_number  VARCHAR(100),
    delivery_remark  VARCHAR(500)
);
CREATE INDEX IF NOT EXISTS user_id_idx ON "order" (user_id);

CREATE TABLE IF NOT EXISTS address (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL,
    name        VARCHAR(50),
    phone       VARCHAR(20),
    province    VARCHAR(50),
    city        VARCHAR(50),
    district    VARCHAR(50),
    detail      VARCHAR(255),
    is_default  SMALLINT DEFAULT 0,
    is_deleted  SMALLINT DEFAULT 0,
    create_time TIMESTAMP,
    update_time TIMESTAMP
);

CREATE TABLE IF NOT EXISTS complaint (
    id          BIGSERIAL PRIMARY KEY,
    order_id    VARCHAR(20),
    user_id     BIGINT,
    type        SMALLINT,
    content     TEXT,
    status      SMALLINT DEFAULT 0,
    result      TEXT,
    create_time TIMESTAMP,
    update_time TIMESTAMP
);

CREATE TABLE IF NOT EXISTS refund (
    id           BIGSERIAL PRIMARY KEY,
    order_id     VARCHAR(20),
    user_id      BIGINT,
    type         SMALLINT,
    reason       VARCHAR(255),
    amount       NUMERIC(10, 2),
    status       SMALLINT DEFAULT 0,
    tracking_no  VARCHAR(100),
    create_time  TIMESTAMP,
    update_time  TIMESTAMP
);
EOSQL
echo "[OK] social_order schema loaded (order + address + complaint + refund)"

# coupon-service
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname social_coupon <<'EOSQL'
CREATE TABLE IF NOT EXISTS coupon (
    id           BIGSERIAL PRIMARY KEY,
    name         VARCHAR(100),
    type         SMALLINT,
    discount     NUMERIC(10, 2),
    min_amount   NUMERIC(10, 2),
    start_time   TIMESTAMP,
    end_time     TIMESTAMP,
    total_count  INTEGER,
    remain_count INTEGER,
    status       SMALLINT DEFAULT 1,
    seller_id    BIGINT,
    create_time  TIMESTAMP,
    update_time  TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_coupon (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT,
    coupon_id   BIGINT,
    status      SMALLINT DEFAULT 0,
    used_time   TIMESTAMP,
    create_time TIMESTAMP,
    update_time TIMESTAMP
);
EOSQL
echo "[OK] social_coupon schema loaded"

# product-service
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname social_product <<'EOSQL'
CREATE TABLE IF NOT EXISTS category (
    id          BIGSERIAL PRIMARY KEY,
    name        VARCHAR(50),
    parent_id   BIGINT DEFAULT 0,
    level       SMALLINT,
    sort        INTEGER DEFAULT 0,
    create_time TIMESTAMP,
    update_time TIMESTAMP
);

CREATE TABLE IF NOT EXISTS product (
    id          BIGSERIAL PRIMARY KEY,
    name        VARCHAR(200),
    description TEXT,
    price       NUMERIC(10, 2),
    stock       INTEGER DEFAULT 0,
    category_id BIGINT,
    seller_id   BIGINT,
    image       VARCHAR(500),
    images      VARCHAR(2000),
    status      SMALLINT DEFAULT 1,
    sales       INTEGER DEFAULT 0,
    is_deleted  SMALLINT DEFAULT 0,
    create_time TIMESTAMP,
    update_time TIMESTAMP
);
EOSQL
echo "[OK] social_product schema loaded (product + category)"

# memory-service
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname social_memory <<'EOSQL'
CREATE TABLE IF NOT EXISTS chat_history (
    id         BIGSERIAL PRIMARY KEY,
    user_id    VARCHAR(32) NOT NULL,
    session_id VARCHAR(64) NOT NULL,
    role       VARCHAR(20) NOT NULL,
    content    TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_chat_user_id ON chat_history(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_session_id ON chat_history(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_created ON chat_history(created_at DESC);

CREATE TABLE IF NOT EXISTS route_fallback_log (
    id          BIGSERIAL PRIMARY KEY,
    session_id  VARCHAR(64),
    user_id     BIGINT,
    message     TEXT,
    route_source VARCHAR(50),
    created_at  TIMESTAMP DEFAULT NOW()
);
EOSQL
echo "[OK] social_memory schema loaded (chat_history + route_fallback_log)"

echo ""
echo "========================================"
echo "  All databases initialized!"
echo "========================================"
