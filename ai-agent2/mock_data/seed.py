"""Mock 演示数据 —— 启动时预置到 Redis

预置 2 个用户的订单数据，覆盖各种状态场景：
  - 待支付订单（可取消）
  - 已支付未发货（可催单、修改地址）
  - 已发货（可查物流）
  - 已完成（可申请退款，测试退货时效规则）
  - 退款中订单（可查退款进度）

每个订单的数据结构与原 Java 后端返回格式严格一致，
确保 orders_tool / logistics_tool / after_sale_tool 的解析逻辑零改动。
"""

import json
import structlog

logger = structlog.get_logger(__name__)


# 演示用户（与前端 demo 登录一致）
DEMO_USERS = {
    "1": "张三",   # 主 demo 用户
    "2": "李四",   # 备用
}

# 订单时间基准（相对当前时间的偏移天数，便于测试退货时效）
def _ts(days_ago: int = 0) -> str:
    """生成 N 天前的时间字符串"""
    import time
    t = time.time() - days_ago * 86400
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t))


# ============================================================
# 主 demo 用户 (user_id=1) 的订单 —— 覆盖全部状态
# ============================================================

ORDERS_USER_1 = [
    {
        "id": "order2026060100001",
        "productName": "Sony WH-1000XM5 降噪耳机",
        "quantity": 1,
        "totalPrice": 2399.00,
        "originalPrice": 2899.00,
        "status": 3,  # 已完成 —— 可测试退款（已过退货期）
        "payTime": _ts(30),
        "deliveryTime": _ts(29),
        "completeTime": _ts(25),
        "trackingNumber": "SF1029384756",
        "carrier": "顺丰速运",
        "receiverAddress": "北京市朝阳区建国路88号",
        "remark": "",
        "sellerId": 100,
    },
    {
        "id": "order2026061000002",
        "productName": "戴森 V12 无线吸尘器",
        "quantity": 1,
        "totalPrice": 3899.00,
        "originalPrice": 4299.00,
        "status": 3,  # 已完成 —— 可测试退款（7天内，符合退货时效）
        "payTime": _ts(5),
        "deliveryTime": _ts(4),
        "completeTime": _ts(2),   # 2天前确认收货，在 7 天退货期内
        "trackingNumber": "JD8847291034",
        "carrier": "京东物流",
        "receiverAddress": "北京市朝阳区建国路88号",
        "remark": "",
        "sellerId": 101,
    },
    {
        "id": "order2026061200003",
        "productName": "iPad Air 11英寸 + Apple Pencil",
        "quantity": 1,
        "totalPrice": 5599.00,
        "originalPrice": 5999.00,
        "status": 2,  # 已发货 —— 可查物流、催单
        "payTime": _ts(1),
        "deliveryTime": _ts(0),
        "completeTime": "",
        "trackingNumber": "YT7293840156",
        "carrier": "圆通速递",
        "receiverAddress": "北京市朝阳区建国路88号",
        "remark": "已揽收，正在发往分拨中心",
        "sellerId": 102,
    },
    {
        "id": "order2026061300004",
        "productName": "罗技 MX Master 3S 鼠标",
        "quantity": 2,
        "totalPrice": 798.00,
        "originalPrice": 898.00,
        "status": 1,  # 已支付未发货 —— 可催单、修改地址
        "payTime": _ts(0),
        "deliveryTime": "",
        "completeTime": "",
        "trackingNumber": "",
        "carrier": "",
        "receiverAddress": "北京市朝阳区建国路88号",
        "remark": "",
        "sellerId": 103,
    },
    {
        "id": "order2026061400005",
        "productName": "小米手环 8 Pro",
        "quantity": 1,
        "totalPrice": 399.00,
        "originalPrice": 449.00,
        "status": 0,  # 待支付 —— 可取消
        "payTime": "",
        "deliveryTime": "",
        "completeTime": "",
        "trackingNumber": "",
        "carrier": "",
        "receiverAddress": "北京市朝阳区建国路88号",
        "remark": "请尽快完成支付",
        "sellerId": 104,
    },
    {
        "id": "order2026060500006",
        "productName": "飞利浦电动牙刷 HX9911",
        "quantity": 1,
        "totalPrice": 899.00,
        "originalPrice": 999.00,
        "status": 5,  # 退款中 —— 可查退款进度
        "payTime": _ts(10),
        "deliveryTime": _ts(9),
        "completeTime": _ts(6),
        "trackingNumber": "ZT1029384756",
        "carrier": "中通快递",
        "receiverAddress": "北京市朝阳区建国路88号",
        "remark": "商品质量问题申请退款",
        "sellerId": 105,
    },
]

# user_id=1 的退款记录（对应订单 006）
REFUNDS_USER_1 = [
    {
        "id": "RF482910",
        "orderId": "order2026060500006",
        "productName": "飞利浦电动牙刷 HX9911",
        "reason": "商品质量问题，充电后无法开机",
        "amount": 899.00,
        "status": 2,  # 退款中
        "type": "refund",
        "remark": "商家已同意退款，等待财务打款",
        "createTime": _ts(4),
    },
]

# user_id=1 的投诉记录
COMPLAINTS_USER_1 = [
    {
        "id": "CP382910",
        "orderId": "order2026060500006",
        "detail": "牙刷用了三天就坏了，质量太差",
        "type": "product",  # 商品问题
        "status": 1,  # 已处理
        "result": "已安排退款，补偿 50 元优惠券",
        "createTime": _ts(4),
    },
]


# ============================================================
# 用户 2 的少量订单（便于测试多用户场景）
# ============================================================

ORDERS_USER_2 = [
    {
        "id": "order2026061100007",
        "productName": " Kindle Paperwhite 电子书阅读器",
        "quantity": 1,
        "totalPrice": 1099.00,
        "originalPrice": 1199.00,
        "status": 3,  # 已完成
        "payTime": _ts(4),
        "deliveryTime": _ts(3),
        "completeTime": _ts(1),
        "trackingNumber": "SF9928374651",
        "carrier": "顺丰速运",
        "receiverAddress": "上海市浦东新区张江路100号",
        "remark": "",
        "sellerId": 106,
    },
]


# ============================================================
# Seed 入口
# ============================================================

def seed_all(r) -> None:
    """将全部演示数据写入 Redis

    Args:
        r: 已连接的 redis.Redis 实例（decode_responses=True）
    """
    # 全局商品（商城首页展示）
    _seed_products(r)

    # 全局用户（登录用）
    _seed_users(r)

    # 用户业务数据
    _seed_user(r, "1", ORDERS_USER_1, REFUNDS_USER_1, COMPLAINTS_USER_1)
    _seed_addresses(r, "1")
    _seed_user(r, "2", ORDERS_USER_2, [], [])

    logger.info("mock_data_seeded",
                users=2,
                orders=len(ORDERS_USER_1) + len(ORDERS_USER_2),
                refunds=len(REFUNDS_USER_1),
                complaints=len(COMPLAINTS_USER_1),
                products=len(PRODUCTS),
                addresses=len(ADDRESSES_USER_1))


def _seed_user(r, user_id: str, orders: list, refunds: list, complaints: list):
    """写入单个用户的全量数据"""
    if orders:
        r.set(f"mock::orders::{user_id}", json.dumps(orders, ensure_ascii=False))
    if refunds:
        r.set(f"mock::refunds::{user_id}", json.dumps(refunds, ensure_ascii=False))
    if complaints:
        r.set(f"mock::complaints::{user_id}", json.dumps(complaints, ensure_ascii=False))


# ============================================================
# 商品数据（商城全局）—— 覆盖订单中引用的商品
# ============================================================

PRODUCTS = [
    {
        "id": "P1001",
        "name": "Sony WH-1000XM5 降噪耳机",
        "description": "行业顶级主动降噪，30小时续航，LDAC高清音质。沉浸式音乐体验。",
        "price": 2399.00,
        "stock": 50,
        "categories": ["数码", "耳机"],
        "deliveryTypes": [1],
        "image": "https://picsum.photos/seed/sony/400/400",
        "images": ["https://picsum.photos/seed/sony/400/400"],
        "sellerId": "100",
        "sellerNickname": "索尼官方旗舰店",
        "status": 1,
        "viewCount": 1280,
        "saleCount": 156,
    },
    {
        "id": "P1002",
        "name": "戴森 V12 无线吸尘器",
        "description": "激光探测灰尘，强劲吸力，60分钟续航。家居清洁利器。",
        "price": 3899.00,
        "stock": 30,
        "categories": ["家电", "清洁"],
        "deliveryTypes": [1],
        "image": "https://picsum.photos/seed/dyson/400/400",
        "images": ["https://picsum.photos/seed/dyson/400/400"],
        "sellerId": "101",
        "sellerNickname": "戴森官方旗舰店",
        "status": 1,
        "viewCount": 890,
        "saleCount": 78,
    },
    {
        "id": "P1003",
        "name": "iPad Air 11英寸 + Apple Pencil",
        "description": "M2芯片，Liquid Retina显示屏，支持Apple Pencil Pro。创作生产力工具。",
        "price": 5599.00,
        "stock": 25,
        "categories": ["数码", "平板"],
        "deliveryTypes": [1],
        "image": "https://picsum.photos/seed/ipad/400/400",
        "images": ["https://picsum.photos/seed/ipad/400/400"],
        "sellerId": "102",
        "sellerNickname": "Apple 授权店",
        "status": 1,
        "viewCount": 2100,
        "saleCount": 234,
    },
    {
        "id": "P1004",
        "name": "罗技 MX Master 3S 鼠标",
        "description": "静音点击，MagSpeed滚轮，多设备无缝切换。办公效率神器。",
        "price": 399.00,
        "stock": 100,
        "categories": ["数码", "外设"],
        "deliveryTypes": [1],
        "image": "https://picsum.photos/seed/logitech/400/400",
        "images": ["https://picsum.photos/seed/logitech/400/400"],
        "sellerId": "103",
        "sellerNickname": "罗技旗舰店",
        "status": 1,
        "viewCount": 1560,
        "saleCount": 312,
    },
    {
        "id": "P1005",
        "name": "小米手环 8 Pro",
        "description": "1.74英寸AMOLED大屏，150+运动模式，14天续航。健康管家。",
        "price": 399.00,
        "stock": 200,
        "categories": ["数码", "穿戴"],
        "deliveryTypes": [1],
        "image": "https://picsum.photos/seed/miband/400/400",
        "images": ["https://picsum.photos/seed/miband/400/400"],
        "sellerId": "104",
        "sellerNickname": "小米官方旗舰店",
        "status": 1,
        "viewCount": 3400,
        "saleCount": 890,
    },
    {
        "id": "P1006",
        "name": "飞利浦电动牙刷 HX9911",
        "description": "声波震动，5种清洁模式，智能APP连接。口腔护理专家。",
        "price": 899.00,
        "stock": 80,
        "categories": ["个护", "口腔"],
        "deliveryTypes": [1],
        "image": "https://picsum.photos/seed/philips/400/400",
        "images": ["https://picsum.photos/seed/philips/400/400"],
        "sellerId": "105",
        "sellerNickname": "飞利浦旗舰店",
        "status": 1,
        "viewCount": 670,
        "saleCount": 145,
    },
    {
        "id": "P1007",
        "name": " Kindle Paperwhite 电子书阅读器",
        "description": "6.8英寸防眩光屏，防水设计，10周续航。沉浸阅读体验。",
        "price": 1099.00,
        "stock": 40,
        "categories": ["数码", "阅读"],
        "deliveryTypes": [1],
        "image": "https://picsum.photos/seed/kindle/400/400",
        "images": ["https://picsum.photos/seed/kindle/400/400"],
        "sellerId": "106",
        "sellerNickname": "Amazon 官方店",
        "status": 1,
        "viewCount": 980,
        "saleCount": 167,
    },
]


# ============================================================
# 用户数据（登录用）
# ============================================================

USERS = [
    {
        "id": "1",
        "username": "demo",
        "password": "123456",
        "nickname": "张三",
        "email": "demo@example.com",
        "phone": "138****5678",
        "avatar": "",
        "gender": 1,
        "birthday": "1995-06-15",
        "signature": "热爱数码产品",
        "status": 1,
        "role": 0,
        "createTime": _ts(60),
    },
    {
        "id": "2",
        "username": "lisi",
        "password": "123456",
        "nickname": "李四",
        "email": "lisi@example.com",
        "phone": "139****1234",
        "avatar": "",
        "gender": 2,
        "status": 1,
        "role": 0,
        "createTime": _ts(30),
    },
]


# ============================================================
# 地址数据（user_id=1）
# ============================================================

ADDRESSES_USER_1 = [
    {
        "id": 1001,
        "receiverName": "张三",
        "receiverPhone": "138****5678",
        "province": "北京市",
        "city": "北京市",
        "district": "朝阳区",
        "detailAddress": "建国路88号 SOHO 现代城 A座 1801",
        "isDefault": 1,
    },
    {
        "id": 1002,
        "receiverName": "张三",
        "receiverPhone": "138****5678",
        "province": "北京市",
        "city": "北京市",
        "district": "海淀区",
        "detailAddress": "中关村大街1号 海龙大厦 5层",
        "isDefault": 0,
    },
]


# ============================================================
# 商品 / 用户 / 地址 seed 函数
# ============================================================

def _seed_products(r):
    """写入商品数据"""
    r.set("mock::products", json.dumps(PRODUCTS, ensure_ascii=False))


def _seed_users(r):
    """写入用户数据"""
    r.set("mock::users", json.dumps(USERS, ensure_ascii=False))


def _seed_addresses(r, user_id: str):
    """写入用户地址数据"""
    r.set(f"mock::addresses::{user_id}", json.dumps(ADDRESSES_USER_1, ensure_ascii=False))
