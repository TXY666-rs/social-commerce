/**
 * 图片URL处理工具
 * 统一处理商品图片、头像等URL的解析和拼接
 */

import type { Product } from '@/types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api'

/**
 * 获取商品的第一张图片完整URL
 * 优先使用后端返回的 images 列表，否则从 image 字段解析
 */
export function getProductImageUrl(product?: Product, fallback = ''): string {
  if (!product) return fallback
  // 优先使用后端已拼接好的 images 字段
  if (product.images && product.images.length > 0) {
    return product.images[0]
  }
  // 兼容：从 image 原始字段解析
  return resolveImageUrl(product.image, fallback)
}

/**
 * 获取商品的所有图片完整URL列表
 * 优先使用后端返回的 images 列表，否则从 image 字段解析
 */
export function getProductImageUrls(product?: Product): string[] {
  if (!product) return []
  if (product.images && product.images.length > 0) {
    return product.images
  }
  return resolveImageUrls(product.image)
}

/**
 * 解析单个图片URL（原始字符串）
 * 兼容完整URL（https://...）和相对路径（/upload/...）
 * 支持逗号分隔的多图字段，默认取第一张
 */
export function resolveImageUrl(url?: string, fallback = ''): string {
  if (!url) return fallback
  const firstUrl = url.split(',')[0]?.trim()
  if (!firstUrl) return fallback
  if (firstUrl.startsWith('http://') || firstUrl.startsWith('https://')) return firstUrl
  return `${API_BASE_URL}${firstUrl}`
}

/**
 * 将逗号分隔的图片字符串解析为完整URL数组
 */
export function resolveImageUrls(imageStr?: string): string[] {
  if (!imageStr) return []
  return imageStr
    .split(',')
    .map(u => u.trim())
    .filter(u => u)
    .map(u => {
      if (u.startsWith('http://') || u.startsWith('https://')) return u
      return `${API_BASE_URL}${u}`
    })
}

/**
 * 将URL数组合并为逗号分隔字符串（用于提交表单）
 */
export function joinImageUrls(urls: string[]): string {
  return urls.filter(u => u.trim()).join(',')
}

/**
 * 将逗号分隔的图片字符串拆分为原始URL数组（不做路径拼接，用于编辑回显）
 */
export function parseRawImages(imageStr?: string): string[] {
  if (!imageStr) return []
  return imageStr.split(',').filter(u => u.trim())
}
