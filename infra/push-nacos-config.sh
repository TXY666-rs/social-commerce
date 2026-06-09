#!/bin/bash
# ============================================
# 将配置推送到 Nacos
# 用法: bash push-nacos-config.sh [nacos_host]
# 默认: nacos_host = localhost
# ============================================

NACOS_HOST=${1:-localhost}
NACOS_PORT=8848
NACOS_URL="http://${NACOS_HOST}:${NACOS_PORT}/nacos/v1/cs/configs"
GROUP="com.social"

CONFIGS=(
  "social-common.yaml"
  "social-gateway.yaml"
  "user-service.yaml"
  "product-service.yaml"
  "order-service.yaml"
  "coupon-service.yaml"
  "memory-service.yaml"
)

echo "Pushing ${#CONFIGS[@]} configs to Nacos at ${NACOS_HOST}:${NACOS_PORT} ..."
echo ""

i=0
for cfg in "${CONFIGS[@]}"; do
  i=$((i + 1))
  echo -n "[$i/${#CONFIGS[@]}] $cfg ... "
  result=$(curl -s -X POST "$NACOS_URL" \
    -d "dataId=$cfg" \
    -d "group=${GROUP}" \
    -d "type=yaml" \
    --data-urlencode "content@nacos-config/$cfg")
  echo "$result"
done

echo ""
echo "Done! 打开 Nacos 控制台确认: http://${NACOS_HOST}:${NACOS_PORT}/nacos"
echo "默认账号: nacos / nacos"
