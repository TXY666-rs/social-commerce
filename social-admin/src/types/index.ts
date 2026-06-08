// ========== 用户相关类型 ==========

export interface User {
  id: number
  username: string
  nickname?: string
  email?: string
  phone?: string
  avatar?: string
  status?: number
  role?: number
  createTime?: string
}

export interface UserTokenVO {
  token: string
  tokenPrefix: string
  userId: number
  username: string
  nickname?: string
  avatar?: string
  expiresIn: number
  role?: number
}

// ========== 通用类型 ==========

export interface ApiResponse<T = any> {
  code: number
  message: string
  data?: T
  timestamp?: number
}

export interface PageResult<T> {
  records: T[]
  total: number
  size: number
  current: number
  pages: number
}
