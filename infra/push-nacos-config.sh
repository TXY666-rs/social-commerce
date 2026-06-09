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

echo "Pushing configs to Nacos at ${NACOS_HOST}:${NACOS_PORT} ..."

# social-common (共享配置)
echo -n "[1/2] social-common.yaml ... "
curl -s -X POST "$NACOS_URL" \
  -d "dataId=social-common.yaml" \
  -d "group=${GROUP}" \
  -d "type=yaml" \
  --data-urlencode "content@nacos-config/social-common.yaml" | head -1
echo ""

# social-gateway (网关路由)
echo -n "[2/2] social-gateway.yaml ... "
curl -s -X POST "$NACOS_URL" \
  -d "dataId=social-gateway.yaml" \
  -d "group=${GROUP}" \
  -d "type=yaml" \
  --data-urlencode "content@nacos-config/social-gateway.yaml" | head -1
echo ""

echo ""
echo "Done! 打开 Nacos 控制台确认: http://${NACOS_HOST}:${NACOS_PORT}/nacos"
echo "默认账号: nacos / nacos"
