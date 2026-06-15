"""Mock 业务 API —— 替代 Java 后端的电商接口

本模块为前端业务页面（商城/订单/商品/地址/登录）提供 mock 数据接口。
所有数据来自 mock_data 模块（Redis 存储）。

响应格式统一为 Java 后端的 {code, message, data} 结构，
前端 axios 拦截器据此解包。

路由前缀 /api，与前端 request.ts 的 baseURL 对齐。
"""

import json
import time
from fastapi import APIRouter, Request, Query
from config.logging_config import get_trace_id
import structlog

from mock_data import (
    # 订单
    query_orders, get_order_by_id, cancel_order, create_order, pay_order, complete_order,
    # 商品
    query_products, get_product_by_id, get_products_by_category, query_my_products, create_product,
    # 用户
    get_user_by_id, find_user_by_credentials, register_user, update_user,
    # 地址
    query_addresses, create_address, update_address, delete_address,
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api", tags=["mock-business"])

# 订单状态码 → 中文描述（前端 Orders.vue 展示用）
_ORDER_STATUS_DESC = {
    0: "待支付",
    1: "已支付",
    2: "已发货",
    3: "已完成",
    4: "已取消",
    5: "退款中",
    6: "已退款",
}


# ============================================================
# 响应 helper（模拟 Java Result 结构）
# ============================================================

def _ok(data=None, message="success"):
    return {"code": 200, "message": message, "data": data}


def _fail(message="failed", code=400):
    return {"code": code, "message": message, "data": None}


def _current_user_id(request: Request) -> str:
    """从请求头获取当前用户 ID（前端 axios 带 Authorization Bearer token）"""
    # 优先从 X-User-Id header（若 nginx 注入）
    uid = request.headers.get("X-User-Id")
    if uid:
        return uid
    # 从 Authorization Bearer token 解析（token 是纯数字 user_id 或 JWT）
    auth = request.headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else auth
    if not token:
        return "1"  # demo 用户兜底
    if token.isdigit():
        return token
    # JWT 解码（简化：取 payload 中的 userId）
    try:
        import base64
        parts = token.split(".")
        if len(parts) >= 2:
            payload_b64 = parts[1]
            # 补齐 base64 padding（标准公式：需补 (4 - len%4) % 4 个 =）
            payload_b64 += "=" * ((4 - len(payload_b64) % 4) % 4)
            data = json.loads(base64.urlsafe_b64decode(payload_b64))
            uid = data.get("userId") or data.get("sub") or data.get("id")
            return str(uid) if uid else "1"
    except Exception:
        pass
    return "1"


# ============================================================
# 用户模块 /api/user/*
# ============================================================

@router.post("/user/login")
async def user_login(request: Request):
    """用户登录"""
    body = await request.json()
    username = body.get("username", "")
    password = body.get("password", "")
    user = find_user_by_credentials(username, password)
    if not user:
        return _fail("用户名或密码错误", code=401)

    token = user["id"]  # 简化：用 user_id 作为 token
    return _ok({
        "token": token,
        "tokenPrefix": "Bearer ",
        "userId": user["id"],
        "username": user["username"],
        "nickname": user.get("nickname", ""),
        "avatar": user.get("avatar", ""),
        "role": user.get("role", 0),
        "expiresIn": 86400000,
    })


@router.post("/user/register")
async def user_register(request: Request):
    """用户注册"""
    body = await request.json()
    user = register_user(
        body.get("username", ""),
        body.get("password", ""),
        body.get("email", ""),
        body.get("phone", ""),
    )
    if not user:
        return _fail("用户名已存在")
    return _ok({"id": user["id"], "username": user["username"]})


@router.get("/user/me")
async def user_me(request: Request):
    """获取当前用户信息"""
    uid = _current_user_id(request)
    user = get_user_by_id(uid)
    if not user:
        return _fail("用户不存在", code=401)
    # 脱敏：不返回 password 字段
    safe = {k: v for k, v in user.items() if k != "password"}
    safe["id"] = safe.get("id")  # 保持 id 在外层（前端用 X-User-Id）
    return _ok(safe)


@router.put("/user/update")
async def user_update(request: Request):
    """更新用户信息"""
    uid = _current_user_id(request)
    body = await request.json()
    user = update_user(uid, body)
    if not user:
        return _fail("更新失败")
    safe = {k: v for k, v in user.items() if k != "password"}
    return _ok(safe)


@router.get("/user/check/username/{username}")
async def check_username(username: str):
    from mock_data.store import _read_list, USERS_KEY
    users = _read_list(USERS_KEY)
    exists = any(u.get("username") == username for u in users)
    return _ok(exists)


@router.get("/user/check/email/{email}")
async def check_email(email: str):
    from mock_data.store import _read_list, USERS_KEY
    users = _read_list(USERS_KEY)
    exists = any(u.get("email") == email for u in users)
    return _ok(exists)


# ============================================================
# 商品模块 /api/product/*
# ============================================================

@router.get("/product/list")
async def product_list(
    category: str = Query(""),
    keyword: str = Query(""),
    pageNum: int = Query(1),
    pageSize: int = Query(10),
):
    """商品列表（分页）"""
    result = query_products(category=category, keyword=keyword, page=pageNum, size=pageSize)
    return _ok(result)


@router.get("/product/categories")
async def product_categories():
    """获取所有商品分类"""
    from mock_data.store import _read_list, PRODUCTS_KEY
    products = _read_list(PRODUCTS_KEY)
    cats = set()
    for p in products:
        for c in (p.get("categories") or []):
            cats.add(c)
    return _ok(sorted(cats))


@router.get("/product/category/{category}")
async def products_by_category(category: str):
    """按分类查询商品"""
    return _ok(get_products_by_category(category))


@router.get("/product/my")
async def my_products(
    request: Request,
    pageNum: int = Query(1),
    pageSize: int = Query(10),
):
    """我的商品（卖家视角）"""
    uid = _current_user_id(request)
    return _ok(query_my_products(uid, pageNum, pageSize))


@router.get("/product/{product_id}")
async def product_detail(product_id: str):
    """商品详情"""
    product = get_product_by_id(product_id)
    if not product:
        return _fail("商品不存在", code=404)
    return _ok(product)


@router.post("/product/create")
async def product_create(request: Request):
    """创建商品"""
    uid = _current_user_id(request)
    body = await request.json()
    product = create_product(uid, body)
    return _ok(product)


# ============================================================
# 订单模块 /api/order/*
# ============================================================

@router.get("/order/my")
async def order_my(
    request: Request,
    status: int = Query(-1),
    pageNum: int = Query(1),
    pageSize: int = Query(10),
    product_keyword: str = Query(""),
):
    """我的订单列表（分页）"""
    uid = _current_user_id(request)
    orders = query_orders(uid, product_keyword)
    # 状态筛选
    if status >= 0:
        orders = [o for o in orders if o.get("status") == status]

    total = len(orders)
    start = (pageNum - 1) * pageSize
    records = orders[start:start + pageSize]
    # 为每个订单补全商品信息（前端列表展示需要）
    for o in records:
        if not o.get("productName"):
            product = get_product_by_id(o.get("productId", ""))
            if product:
                o["productName"] = product["name"]
                o["productImage"] = product.get("image", "")
        o["statusDesc"] = _ORDER_STATUS_DESC.get(o.get("status", -1), "未知")
    return _ok({
        "records": records, "total": total,
        "current": pageNum, "pages": (total + pageSize - 1) // pageSize,
    })


@router.get("/order/{order_id}")
async def order_detail(order_id: str, request: Request):
    """订单详情"""
    uid = _current_user_id(request)
    for o in query_orders(uid):
        if str(o.get("id")) == str(order_id):
            # 补全商品信息
            if not o.get("productName"):
                product = get_product_by_id(o.get("productId", ""))
                if product:
                    o["productName"] = product["name"]
                    o["productImage"] = product.get("image", "")
            # 补全状态描述（前端 badge 展示用）
            o["statusDesc"] = _ORDER_STATUS_DESC.get(o.get("status", -1), "未知")
            return _ok(o)
    return _fail("订单不存在", code=404)


@router.post("/order/create")
async def order_create(request: Request):
    """创建订单"""
    uid = _current_user_id(request)
    body = await request.json()
    order = create_order(
        uid,
        body.get("productId", ""),
        body.get("quantity", 1),
        body.get("receiverName", ""),
        body.get("receiverPhone", ""),
        body.get("receiverAddress", ""),
        body.get("remark", ""),
    )
    if not order:
        return _fail("商品不存在")
    return _ok(order)


@router.put("/order/cancel/{order_id}")
async def order_cancel(order_id: str, request: Request):
    """取消订单"""
    uid = _current_user_id(request)
    success, msg = cancel_order(uid, order_id)
    if not success:
        return _fail(msg)
    return _ok(msg)


@router.put("/order/pay/{order_id}")
async def order_pay(order_id: str, request: Request):
    """支付订单"""
    uid = _current_user_id(request)
    success = pay_order(uid, order_id)
    if not success:
        return _fail("支付失败，订单状态不符")
    return _ok("支付成功")


@router.put("/order/complete/{order_id}")
async def order_complete(order_id: str, request: Request):
    """确认收货"""
    uid = _current_user_id(request)
    success = complete_order(uid, order_id)
    if not success:
        return _fail("确认收货失败")
    return _ok("确认收货成功")


@router.put("/order/{order_id}/address")
async def order_change_address(order_id: str, request: Request):
    """修改收货地址"""
    uid = _current_user_id(request)
    body = await request.json()
    from mock_data import change_address
    success, msg = change_address(uid, order_id, body.get("address", ""))
    if not success:
        return _fail(msg)
    return _ok(msg)


# ============================================================
# 地址模块 /api/address/*
# ============================================================

@router.get("/address/list")
async def address_list(request: Request):
    """地址列表"""
    uid = _current_user_id(request)
    return _ok(query_addresses(uid))


@router.post("/address/create")
async def address_create(request: Request):
    """创建地址"""
    uid = _current_user_id(request)
    body = await request.json()
    addr = create_address(uid, body)
    return _ok(addr)


@router.put("/address/{addr_id}")
async def address_update(addr_id: int, request: Request):
    """更新地址"""
    uid = _current_user_id(request)
    body = await request.json()
    success = update_address(uid, addr_id, body)
    if not success:
        return _fail("地址不存在")
    return _ok(True)


@router.delete("/address/{addr_id}")
async def address_delete(addr_id: int, request: Request):
    """删除地址"""
    uid = _current_user_id(request)
    success = delete_address(uid, addr_id)
    if not success:
        return _fail("删除失败")
    return _ok(True)


@router.put("/address/default/{addr_id}")
async def address_set_default(addr_id: int, request: Request):
    """设置默认地址"""
    uid = _current_user_id(request)
    success = update_address(uid, addr_id, {"isDefault": 1})
    if not success:
        return _fail("设置失败")
    return _ok(True)


# ============================================================
# 上传模块 /api/upload/*（mock，返回固定图片 URL）
# ============================================================

@router.post("/upload/image")
async def upload_image(request: Request):
    """图片上传（mock —— 返回随机占位图）"""
    import random
    seed = random.randint(1, 10000)
    url = f"https://picsum.photos/seed/upload{seed}/400/400"
    return _ok({"url": url, "originalName": "uploaded.jpg"})


@router.post("/upload/images")
async def upload_images(request: Request):
    """多图上传（mock）"""
    import random
    urls = [f"https://picsum.photos/seed/upload{random.randint(1,10000)}/400/400"
            for _ in range(3)]
    return _ok(urls)
