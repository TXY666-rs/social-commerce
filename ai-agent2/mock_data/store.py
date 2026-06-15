"""Mock 数据存储层 —— 替代 Java 后端的业务数据

设计思路：
    重构后不再依赖 Java 微服务，所有业务数据（订单/退款/物流/投诉）
    存储在 Redis 中，由 seed.py 启动时预置演示数据。

    这样 Agent 的 tool 调用链路完全自洽，面试官克隆下来即可体验完整的
    智能客服场景（查订单、退款、催单、投诉等），无需启动任何 Java 服务。

数据结构（与原 Java 后端返回格式保持一致，确保 tool 层零改动兼容）：
    订单 order:   {id, productName, quantity, totalPrice, status, payTime,
                   deliveryTime, completeTime, trackingNumber, carrier,
                   receiverAddress, remark, sellerId, originalPrice}
    退款 refund:  {id, orderId, reason, amount, status, remark, type}
    投诉 complaint: {id, orderId, detail, type, status, result}
    物流 carrier: 嵌入 order.trackingNumber + order.carrier

Redis Key 设计：
    mock::orders::{user_id}        → JSON list of orders
    mock::refunds::{user_id}       → JSON list of refunds
    mock::complaints::{user_id}    → JSON list of complaints
    mock::seeded                   → "1" 标记已 seed（幂等）
"""

import json
import time
import threading
import structlog
from services.redis_client import get_redis

logger = structlog.get_logger(__name__)

ORDERS_KEY = "mock::orders::{user_id}"
REFUNDS_KEY = "mock::refunds::{user_id}"
COMPLAINTS_KEY = "mock::complaints::{user_id}"
PRODUCTS_KEY = "mock::products"           # 全局商品列表（所有用户共享商城）
USERS_KEY = "mock::users"                 # 全局用户列表
ADDRESSES_KEY = "mock::addresses::{user_id}"
SEEDED_FLAG = "mock::seeded"

# Seed 数据版本号：升级数据格式（如订单号格式变更）时递增。
# ensure_seeded 会比对 Redis 里记录的版本，不匹配则重新 seed 覆盖旧数据。
SEED_VERSION = "2"
SEEDED_VERSION_KEY = "mock::seeded_version"

_mock_lock = threading.Lock()


# ============================================================
# 内部读写 helper
# ============================================================

def _read_list(key: str) -> list:
    """从 Redis 读取 JSON list，不存在返回空 list"""
    r = get_redis()
    raw = r.get(key)
    if not raw:
        return []
    try:
        return json.loads(raw)
    except Exception:
        return []


def _write_list(key: str, data: list):
    """写入 JSON list 到 Redis"""
    r = get_redis()
    r.set(key, json.dumps(data, ensure_ascii=False))


# ============================================================
# 订单（Order）
# ============================================================

def query_orders(user_id: str, product_keyword: str = "") -> list:
    """查询用户订单列表。

    对应原 Java 接口: GET /api/order/my
    返回结构与 Java 后端一致（records 数组）。
    """
    orders = _read_list(ORDERS_KEY.format(user_id=user_id))
    if product_keyword:
        kw = product_keyword.lower()
        orders = [o for o in orders if kw in o.get("productName", "").lower()]
    return orders


def get_order_by_id(user_id: str, order_id: str) -> dict | None:
    """按订单 ID 查询单个订单"""
    for o in query_orders(user_id):
        if str(o.get("id")) == str(order_id):
            return o
    return None


def cancel_order(user_id: str, order_id: str) -> tuple[bool, str]:
    """取消订单。只有待支付(status=0)状态可取消。

    Returns:
        (success, message)
    """
    orders = _read_list(ORDERS_KEY.format(user_id=user_id))
    for o in orders:
        if str(o.get("id")) == str(order_id):
            if o.get("status") != 0:
                return False, f"当前订单状态为「{_status_name(o['status'])}」，无法取消，只有待支付订单可取消。"
            o["status"] = 4  # 已取消
            _write_list(ORDERS_KEY.format(user_id=user_id), orders)
            return True, "订单取消成功。"
    return False, "未找到该订单，请确认订单号。"


def remind_delivery(user_id: str, order_id: str) -> tuple[bool, str]:
    """催发货。已发货订单返回已发出提示。

    Returns:
        (success, message)
    """
    o = get_order_by_id(user_id, order_id)
    if not o:
        return False, "未找到该订单，请确认订单号。"
    if o.get("status") == 0:
        return False, "订单尚未支付，无法催单。"
    if o.get("status") >= 2:
        return True, "订单已发货，物流正在配送中，请耐心等待。"
    return True, "已为您催促商家发货，预计 24 小时内发出。"


def change_address(user_id: str, order_id: str, new_address: str) -> tuple[bool, str]:
    """修改收货地址。已发货订单不允许修改。

    Returns:
        (success, message)
    """
    orders = _read_list(ORDERS_KEY.format(user_id=user_id))
    for o in orders:
        if str(o.get("id")) == str(order_id):
            if o.get("status", 0) >= 2:
                return False, "订单已发货，无法修改收货地址。"
            o["receiverAddress"] = new_address
            _write_list(ORDERS_KEY.format(user_id=user_id), orders)
            return True, "收货地址修改成功。"
    return False, "未找到该订单，请确认订单号。"


# ============================================================
# 退款 / 退货（Refund）
# ============================================================

def submit_refund(user_id: str, order_id: str, reason: str, refund_type: str = "refund") -> tuple[bool, str, str]:
    """提交退款/退货申请。

    对应原 Java 接口: POST /api/refund | POST /api/return
    Args:
        refund_type: "refund" 仅退款 | "return" 退货退款
    Returns:
        (success, message, refund_id)
    """
    o = get_order_by_id(user_id, order_id)
    if not o:
        return False, "未找到该订单，请确认订单号。", ""

    # 同一订单已有进行中的退款则拒绝
    refunds = _read_list(REFUNDS_KEY.format(user_id=user_id))
    for rf in refunds:
        if str(rf.get("orderId")) == str(order_id) and rf.get("status") in (0, 1, 2):
            return False, "该订单已有进行中的退款申请，请勿重复提交。", ""

    refund_id = f"RF{int(time.time()) % 1000000}"
    amount = o.get("totalPrice", 0)
    refund = {
        "id": refund_id,
        "orderId": order_id,
        "productName": o.get("productName", ""),
        "reason": reason,
        "amount": amount,
        "status": 0,  # 待审核
        "type": refund_type,
        "remark": "",
        "createTime": _now_str(),
    }
    refunds.append(refund)
    _write_list(REFUNDS_KEY.format(user_id=user_id), refunds)

    # 同步更新订单状态为退款中
    _update_order_status(user_id, order_id, 5)

    action = "退货退款" if refund_type == "return" else "退款"
    return True, f"{action}申请已提交", refund_id


def get_refund_by_id(user_id: str, refund_id: str) -> dict | None:
    """按退款 ID 查询退款详情。对应 GET /api/refund/{id}"""
    for rf in _read_list(REFUNDS_KEY.format(user_id=user_id)):
        if str(rf.get("id")) == str(refund_id):
            return rf
    return None


def get_refund_by_order(user_id: str, order_id: str) -> dict | None:
    """按订单 ID 查询退款记录。对应 GET /api/refund/order/{orderId}"""
    for rf in _read_list(REFUNDS_KEY.format(user_id=user_id)):
        if str(rf.get("orderId")) == str(order_id):
            return rf
    return None


def cancel_refund(user_id: str, refund_id: str) -> tuple[bool, str]:
    """取消退款申请。对应 DELETE /api/refund/{id}"""
    refunds = _read_list(REFUNDS_KEY.format(user_id=user_id))
    for rf in refunds:
        if str(rf.get("id")) == str(refund_id):
            if rf.get("status") in (3, 4, 5):
                return False, "该退款申请已处理完毕，无法取消。"
            rf["status"] = 5  # 已取消
            _write_list(REFUNDS_KEY.format(user_id=user_id), refunds)
            return True, "退款申请已取消。"
    return False, "未找到该退款记录。"


def cancel_refund_by_order(user_id: str, order_id: str) -> tuple[bool, str]:
    """按订单 ID 取消退款。对应 DELETE /api/refund/order/{orderId}"""
    refunds = _read_list(REFUNDS_KEY.format(user_id=user_id))
    for rf in refunds:
        if str(rf.get("orderId")) == str(order_id):
            if rf.get("status") in (3, 4, 5):
                return False, "该订单退款已处理完毕，无法取消。"
            rf["status"] = 5
            _write_list(REFUNDS_KEY.format(user_id=user_id), refunds)
            return True, "退款申请已取消。"
    return False, "该订单无退款记录。"


# ============================================================
# 投诉（Complaint）
# ============================================================

def submit_complaint(user_id: str, order_id: str, detail: str, complaint_type: str) -> tuple[bool, str]:
    """提交投诉。对应 POST /api/complaint"""
    complaints = _read_list(COMPLAINTS_KEY.format(user_id=user_id))
    complaint = {
        "id": f"CP{int(time.time()) % 1000000}",
        "orderId": order_id,
        "detail": detail,
        "type": complaint_type,
        "status": 0,
        "result": "",
        "createTime": _now_str(),
    }
    complaints.append(complaint)
    _write_list(COMPLAINTS_KEY.format(user_id=user_id), complaints)
    return True, "投诉已登记"


# ============================================================
# 商品（Product）—— 商城全局数据
# ============================================================

def query_products(category: str = "", keyword: str = "", page: int = 1, size: int = 10) -> dict:
    """查询商品列表（分页）。对应 GET /api/product/list

    Returns:
        {records, total, current, pages} 分页结构
    """
    products = _read_list(PRODUCTS_KEY)
    # 关键词筛选
    if keyword:
        kw = keyword.lower()
        products = [p for p in products if kw in p.get("name", "").lower() or kw in p.get("description", "").lower()]
    # 分类筛选
    if category:
        products = [p for p in products if category in (p.get("categories") or [])]
    # 只展示在售商品
    products = [p for p in products if p.get("status", 1) == 1]

    total = len(products)
    start = (page - 1) * size
    records = products[start:start + size]
    pages = (total + size - 1) // size
    return {"records": records, "total": total, "current": page, "pages": pages}


def get_product_by_id(product_id: str) -> dict | None:
    """按 ID 查询商品详情"""
    for p in _read_list(PRODUCTS_KEY):
        if str(p.get("id")) == str(product_id):
            # 浏览量 +1
            p["viewCount"] = p.get("viewCount", 0) + 1
            _write_list(PRODUCTS_KEY, _read_list(PRODUCTS_KEY))  # 持久化（简化：整体写回）
            return p
    return None


def get_products_by_category(category: str) -> list:
    """按分类查询商品"""
    return [p for p in _read_list(PRODUCTS_KEY)
            if category in (p.get("categories") or []) and p.get("status", 1) == 1]


def query_my_products(user_id: str, page: int = 1, size: int = 10) -> dict:
    """查询用户自己发布的商品"""
    products = [p for p in _read_list(PRODUCTS_KEY) if str(p.get("sellerId")) == str(user_id)]
    total = len(products)
    start = (page - 1) * size
    return {"records": products[start:start + size], "total": total, "current": page, "pages": (total + size - 1) // size}


def create_product(user_id: str, data: dict) -> dict:
    """创建商品"""
    products = _read_list(PRODUCTS_KEY)
    product = {
        "id": str(int(time.time() * 1000)),
        "sellerId": user_id,
        "name": data.get("name", ""),
        "description": data.get("description", ""),
        "price": data.get("price", 0),
        "stock": data.get("stock", 0),
        "categories": data.get("categories", []),
        "deliveryTypes": data.get("deliveryTypes", [1]),
        "image": data.get("image", ""),
        "images": [data.get("image", "")] if data.get("image") else [],
        "status": 1,
        "viewCount": 0,
        "saleCount": 0,
        "createTime": _now_str(),
    }
    products.insert(0, product)
    _write_list(PRODUCTS_KEY, products)
    return product


# ============================================================
# 用户（User）
# ============================================================

def get_user_by_id(user_id: str) -> dict | None:
    """按 ID 查询用户信息。对应 GET /api/user/me"""
    for u in _read_list(USERS_KEY):
        if str(u.get("id")) == str(user_id):
            return u
    return None


def find_user_by_credentials(username: str, password: str) -> dict | None:
    """用户名+密码查找用户（登录用）"""
    for u in _read_list(USERS_KEY):
        if u.get("username") == username and u.get("password") == password:
            return u
    return None


def register_user(username: str, password: str, email: str, phone: str = "") -> dict | None:
    """注册新用户"""
    users = _read_list(USERS_KEY)
    # 检查用户名唯一
    if any(u.get("username") == username for u in users):
        return None
    user = {
        "id": str(int(time.time() * 1000)),
        "username": username,
        "password": password,
        "nickname": username,
        "email": email,
        "phone": phone,
        "avatar": "",
        "gender": 0,
        "role": 0,
        "status": 1,
        "createTime": _now_str(),
    }
    users.append(user)
    _write_list(USERS_KEY, users)
    return user


def update_user(user_id: str, data: dict) -> dict | None:
    """更新用户信息"""
    users = _read_list(USERS_KEY)
    for u in users:
        if str(u.get("id")) == str(user_id):
            for k in ("nickname", "email", "phone", "avatar", "gender", "birthday", "signature"):
                if k in data:
                    u[k] = data[k]
            _write_list(USERS_KEY, users)
            return u
    return None


# ============================================================
# 地址（Address）
# ============================================================

def query_addresses(user_id: str) -> list:
    """查询用户地址列表"""
    return _read_list(ADDRESSES_KEY.format(user_id=user_id))


def create_address(user_id: str, data: dict) -> dict:
    """创建地址"""
    addrs = _read_list(ADDRESSES_KEY.format(user_id=user_id))
    addr = {
        "id": int(time.time() * 1000) % 1000000,
        "receiverName": data.get("receiverName", ""),
        "receiverPhone": data.get("receiverPhone", ""),
        "province": data.get("province", ""),
        "city": data.get("city", ""),
        "district": data.get("district", ""),
        "detailAddress": data.get("detailAddress", ""),
        "isDefault": data.get("isDefault", 0),
    }
    # 如果设为默认，取消其它默认
    if addr["isDefault"] == 1:
        for a in addrs:
            a["isDefault"] = 0
    addrs.append(addr)
    _write_list(ADDRESSES_KEY.format(user_id=user_id), addrs)
    return addr


def update_address(user_id: str, addr_id: int, data: dict) -> bool:
    """更新地址"""
    addrs = _read_list(ADDRESSES_KEY.format(user_id=user_id))
    for a in addrs:
        if a.get("id") == addr_id:
            for k in ("receiverName", "receiverPhone", "province", "city", "district", "detailAddress", "isDefault"):
                if k in data:
                    a[k] = data[k]
            _write_list(ADDRESSES_KEY.format(user_id=user_id), addrs)
            return True
    return False


def delete_address(user_id: str, addr_id: int) -> bool:
    """删除地址"""
    addrs = _read_list(ADDRESSES_KEY.format(user_id=user_id))
    new_addrs = [a for a in addrs if a.get("id") != addr_id]
    _write_list(ADDRESSES_KEY.format(user_id=user_id), new_addrs)
    return len(new_addrs) < len(addrs)


# ============================================================
# 订单扩展（创建/支付/完成）—— 业务页面用
# ============================================================

def create_order(user_id: str, product_id: str, quantity: int,
                 receiver_name: str, receiver_phone: str,
                 receiver_address: str, remark: str = "") -> dict | None:
    """创建订单。对应 POST /api/order/create"""
    product = get_product_by_id(product_id)
    if not product:
        return None

    order = {
        "id": _gen_order_id(user_id),
        "userId": user_id,
        "productId": product_id,
        "productName": product.get("name", ""),
        "productImage": product.get("image", ""),
        "productPrice": product.get("price", 0),
        "quantity": quantity,
        "totalPrice": round(product.get("price", 0) * quantity, 2),
        "status": 0,  # 待支付
        "receiverName": receiver_name,
        "receiverPhone": receiver_phone,
        "receiverAddress": receiver_address,
        "remark": remark,
        "createTime": _now_str(),
    }
    orders = _read_list(ORDERS_KEY.format(user_id=user_id))
    orders.insert(0, order)
    _write_list(ORDERS_KEY.format(user_id=user_id), orders)

    # 商品销量 +1
    products = _read_list(PRODUCTS_KEY)
    for p in products:
        if str(p.get("id")) == str(product_id):
            p["saleCount"] = p.get("saleCount", 0) + quantity
    _write_list(PRODUCTS_KEY, products)

    return order


def pay_order(user_id: str, order_id: str) -> bool:
    """支付订单：状态 0→1"""
    return _update_order_status_with_check(user_id, order_id, 0, 1, payTime=True)


def complete_order(user_id: str, order_id: str) -> bool:
    """确认收货：状态 2→3"""
    return _update_order_status_with_check(user_id, order_id, 2, 3, completeTime=True)


def _update_order_status_with_check(user_id: str, order_id: str, expect_status: int,
                                     new_status: int, payTime: bool = False,
                                     completeTime: bool = False) -> bool:
    """带状态前置检查的订单状态更新"""
    orders = _read_list(ORDERS_KEY.format(user_id=user_id))
    for o in orders:
        if str(o.get("id")) == str(order_id):
            if o.get("status") != expect_status:
                return False
            o["status"] = new_status
            if payTime:
                o["payTime"] = _now_str()
            if completeTime:
                o["completeTime"] = _now_str()
            _write_list(ORDERS_KEY.format(user_id=user_id), orders)
            return True
    return False


# ============================================================
# 内部工具函数
# ============================================================

def _update_order_status(user_id: str, order_id: str, status: int):
    """更新订单状态"""
    orders = _read_list(ORDERS_KEY.format(user_id=user_id))
    for o in orders:
        if str(o.get("id")) == str(order_id):
            o["status"] = status
            break
    _write_list(ORDERS_KEY.format(user_id=user_id), orders)


def _status_name(status: int) -> str:
    """订单状态码 → 中文名（与 constants.ORDER_STATUS 一致）"""
    return {
        0: "待支付", 1: "已支付", 2: "已发货",
        3: "已完成", 4: "已取消", 5: "退款中", 6: "已退款",
    }.get(status, "未知")


def _now_str() -> str:
    """当前时间字符串（与 Java 后端格式一致）"""
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _gen_order_id(user_id: str) -> str:
    """生成订单号，格式：order + YYYYMMDD(8位) + 5位序号 = order + 13位数字。

    与 seed 数据及各 skill 的 order\\d{13} 正则保持一致。
    序号取当前用户当天已有订单数 +1（5 位补零），避免同一秒内重复。
    """
    date_part = time.strftime("%Y%m%d")
    prefix = f"order{date_part}"
    orders = _read_list(ORDERS_KEY.format(user_id=user_id))
    seq = sum(1 for o in orders if str(o.get("id", "")).startswith(prefix)) + 1
    return f"{prefix}{seq:05d}"


# ============================================================
# 初始化入口（幂等）
# ============================================================

def ensure_seeded():
    """确保 mock 数据已 seed（幂等，版本号变更时自动重 seed 覆盖旧数据）

    在应用启动时调用（main.py lifespan）。
    用锁防止并发首启动重复 seed。

    版本机制：Redis 里记录 SEED_VERSION，与当前代码版本比对；
    不匹配（含首次启动 / 数据格式升级）则重新 seed 覆盖。
    """
    from mock_data.seed import seed_all

    with _mock_lock:
        r = get_redis()
        if r.get(SEEDED_FLAG) and r.get(SEEDED_VERSION_KEY) == SEED_VERSION:
            logger.info("mock_data_already_seeded", version=SEED_VERSION)
            return
        try:
            seed_all(r)
            r.set(SEEDED_FLAG, "1")
            r.set(SEEDED_VERSION_KEY, SEED_VERSION)
            logger.info("mock_data_seeded_ok", version=SEED_VERSION)
        except Exception as e:
            logger.error("mock_data_seed_failed", error=str(e))
