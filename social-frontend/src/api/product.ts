import request from '@/utils/request'
import type { Product, ProductListItem, Order, ProductQuery, OrderQuery, ProductCreate, ProductUpdate, OrderCreate, PageResult } from '@/types'

// ========== 文件上传API ==========

// 上传单张图片
export const uploadImage = (file: File, module: string = 'general'): Promise<{ url: string; originalName: string }> => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('module', module)
  return request.post('/upload/image', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

// 上传多张图片
export const uploadImages = (files: File[], module: string = 'general'): Promise<string[]> => {
  const formData = new FormData()
  files.forEach(file => formData.append('files', file))
  formData.append('module', module)
  return request.post('/upload/images', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

// ========== 商品相关API ==========

// 获取商品分类列表
export const getCategories = (): Promise<string[]> => {
  return request.get('/product/categories')
}

// 查询商品列表（后端返回 IPage<ProductListVO>，含 records/total 分页信息）
export const getProductList = (params: ProductQuery): Promise<PageResult<ProductListItem>> => {
  return request.get('/product/list', { params })
}

// 根据分类查询商品列表（后端带Redis缓存）
export const getProductsByCategory = (category: string): Promise<ProductListItem[]> => {
  return request.get(`/product/category/${encodeURIComponent(category)}`)
}

// 获取商品详情
export const getProductDetail = (id: string): Promise<Product> => {
  return request.get(`/product/${id}`)
}

// 发布商品
export const createProduct = (data: ProductCreate): Promise<Product> => {
  return request.post('/product/create', data)
}

// 更新商品
export const updateProduct = (id: string, data: ProductUpdate): Promise<Product> => {
  return request.put(`/product/update/${id}`, data)
}

// 删除商品
export const deleteProduct = (id: string): Promise<boolean> => {
  return request.delete(`/product/delete/${id}`)
}

// 上架/下架商品
export const toggleProductStatus = (id: string, status: number): Promise<boolean> => {
  return request.put(`/product/toggle-status/${id}`, null, { params: { status } })
}

// 获取我的商品
export const getMyProducts = (params: ProductQuery): Promise<PageResult<Product>> => {
  return request.get('/product/my', { params })
}

// ========== 订单相关API ==========

// 创建订单
export const createOrder = (data: OrderCreate): Promise<Order> => {
  return request.post('/order/create', data)
}

// 获取订单详情
export const getOrderDetail = (id: string): Promise<Order> => {
  return request.get(`/order/${id}`)
}

// 获取我的订单列表
export const getMyOrders = (params: OrderQuery): Promise<PageResult<Order>> => {
  return request.get('/order/my', { params })
}

// 取消订单（买家）
export const cancelOrder = (id: string): Promise<boolean> => {
  return request.put(`/order/cancel/${id}`)
}

// 支付订单
export const payOrder = (id: string): Promise<boolean> => {
  return request.put(`/order/pay/${id}`)
}

// 确认收货
export const completeOrder = (id: string): Promise<boolean> => {
  return request.put(`/order/complete/${id}`)
}
