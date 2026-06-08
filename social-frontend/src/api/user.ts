import request from '@/utils/request'
import type { User, LoginRequest, RegisterRequest, TokenVO } from '@/types'

// 用户登录
export const login = (data: LoginRequest): Promise<TokenVO> => {
  return request.post('/user/login', data)
}

// 用户注册
export const register = (data: RegisterRequest): Promise<void> => {
  return request.post('/user/register', data)
}

// 获取用户信息
export const getUserInfo = (): Promise<User> => {
  return request.get('/user/me')
}

// 更新用户信息
export const updateUserInfo = (data: Partial<User>): Promise<User> => {
  return request.put('/user/update', data)
}

// 检查用户名是否存在
export const checkUsernameExists = (username: string): Promise<boolean> => {
  return request.get(`/user/check/username/${username}`)
}

// 检查邮箱是否存在
export const checkEmailExists = (email: string): Promise<boolean> => {
  return request.get(`/user/check/email/${email}`)
}

// 检查手机号是否存在
export const checkPhoneExists = (phone: string): Promise<boolean> => {
  return request.get(`/user/check/phone/${phone}`)
}

// 搜索用户（按用户名/昵称模糊搜索）
export const searchUsers = (keyword: string): Promise<User[]> => {
  return request.get('/user/search', { params: { keyword } })
}