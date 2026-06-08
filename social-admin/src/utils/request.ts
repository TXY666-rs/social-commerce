import axios, { type AxiosInstance, type AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'
import { getCookie } from '@/utils/cookie'

// 防止重复跳转登录页
let isRedirecting = false

// 清除所有登录状态（与 social-frontend 统一）
function clearAuthState() {
  localStorage.removeItem('token')
  localStorage.removeItem('admin_userInfo')
}

// 安全读取 token：Cookie 优先 → localStorage 降级（与 social-frontend 完全一致）
function readToken(): string | null {
  return getCookie('token') || localStorage.getItem('token')
}

// 创建 axios 实例
const request: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:9000/api',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
request.interceptors.request.use(
  (config: any) => {
    const token = readToken()
    if (token) {
      if (!config.headers) {
        config.headers = {}
      }
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error: any) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  (response: AxiosResponse) => {
    const res = response.data
    if (res.code === 200 || res.code === 0) {
      return res.data !== undefined ? res.data : res
    } else {
      ElMessage.error(res.message || '请求失败')
      return Promise.reject(new Error(res.message || '请求失败'))
    }
  },
  (error: any) => {
    if (error.response) {
      switch (error.response.status) {
        case 401:
          if (!error.config?.skipAuthRedirect) {
            ElMessage.error('未授权，请重新登录')
            if (!isRedirecting && window.location.pathname !== '/login') {
              isRedirecting = true
              clearAuthState()
              router.push('/login').finally(() => {
                isRedirecting = false
              })
            }
          }
          break
        case 403:
          if (!error.config?.skipAuthRedirect) {
            ElMessage.error('权限不足，请联系超级管理员')
          }
          break
        case 404:
          ElMessage.error('请求的资源不存在')
          break
        case 500:
          ElMessage.error('服务器内部错误')
          break
        default:
          ElMessage.error(error.response.data?.message || '请求失败')
      }
    } else if (error.request) {
      ElMessage.error('网络错误，请检查网络连接')
    } else {
      ElMessage.error('请求配置错误')
    }
    return Promise.reject(error)
  }
)

export default request
