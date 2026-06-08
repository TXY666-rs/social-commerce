// 用户相关类型
export interface User {
  id: string
  username: string
  nickname?: string
  email: string
  phone?: string
  avatar?: string
  gender?: number
  birthday?: string
  signature?: string
  status?: number
  role?: number  // 0-普通用户 1-管理员
  lastLoginTime?: string
  lastLoginIp?: string
  createTime?: string
}

// API响应类型
export interface ApiResponse<T = any> {
  code: number
  message: string
  data?: T
}

// 登录请求
export interface LoginRequest {
  username: string
  password: string
}

// 注册请求
export interface RegisterRequest {
  username: string
  password: string
  email: string
  phone?: string
}

// Token返回
export interface TokenVO {
  token: string
  tokenPrefix: string
  userId: string
  username: string
  nickname?: string
  avatar?: string
  expiresIn: number
}

// ========== 商品相关类型 ==========

// 商品列表项（与后端 ProductListVO 对齐，用于列表查询接口）
export interface ProductListItem {
  id: string
  name: string
  description?: string
  price: number
  categories?: string[]
  image?: string
  images?: string[]
  status: number
  viewCount: number
  saleCount: number
}

// 商品（完整信息，用于详情/我的商品等接口）
export interface Product {
  id: string
  name: string
  description?: string
  price: number
  stock: number
  category?: string          // 逗号分隔的分类（兼容旧数据）
  categories?: string[]      // 分类列表
  deliveryType?: string      // 逗号分隔的配送方式（兼容旧数据）
  deliveryTypes?: number[]   // 配送方式 (1:快递发货)
  image?: string
  images?: string[]           // 后端已拼接的完整图片URL列表
  sellerId: string
  sellerNickname?: string
  status: number
  viewCount: number
  saleCount: number
  createTime?: string
  updateTime?: string
}

// 订单
export interface Order {
  id: string
  userId: string
  productId: string
  sellerId?: string
  sellerNickname?: string
  productName?: string
  productImage?: string
  productPrice?: number
  quantity: number
  totalPrice: number
  status: number
  statusDesc?: string
  receiverName: string
  receiverPhone: string
  receiverAddress: string
  deliveryType?: number       // 配送方式 (1:快递发货)
  deliveryTypeDesc?: string   // 配送方式描述
  trackingNumber?: string     // 快递单号
  deliveryRemark?: string     // 发货备注/自提地址
  payTime?: string
  deliveryTime?: string
  completeTime?: string
  remark?: string
  createTime?: string
}

// 商品查询参数
export interface ProductQuery {
  category?: string
  keyword?: string
  status?: number
  pageNum?: number
  pageSize?: number
}

// 订单查询参数
export interface OrderQuery {
  status?: number
  pageNum?: number
  pageSize?: number
}

// 创建商品参数
export interface ProductCreate {
  name: string
  description?: string
  price: number
  stock: number
  categories?: string[]
  deliveryTypes?: number[]   // 配送方式 (1:快递发货, 2:上门自提)
  image?: string
}

// 更新商品参数
export interface ProductUpdate {
  name?: string
  description?: string
  price?: number
  stock?: number
  categories?: string[]
  deliveryTypes?: number[]
  image?: string
  status?: number
}

// 创建订单参数
export interface OrderCreate {
  productId: string     // Long 精度超出 JS Number 范围，用 string 传输
  quantity: number
  receiverName: string
  receiverPhone: string
  receiverAddress: string
  remark?: string
}

// 发货参数
export interface DeliverOrderDTO {
  trackingNumber?: string     // 快递单号
  deliveryRemark?: string     // 发货备注/自提地址
}

// 收货地址
export interface Address {
  id?: number
  receiverName: string
  receiverPhone: string
  province?: string
  city?: string
  district?: string
  detailAddress: string
  isDefault?: number
}

// 分页结果
export interface PageResult<T> {
  records: T[]
  total: number
  size: number
  current: number
  pages: number
}

// ========== 知识库相关类型 ==========

// OSS 文件 VO（后端返回）
export interface AliOssFileVO {
  id: string
  fileName: string
  createTime: string
  updateTime: string
}

// 文件列表接口返回（后端不返回 total，用数组接收）
export interface FileListResult {
  records: AliOssFileVO[]
  total?: number
}