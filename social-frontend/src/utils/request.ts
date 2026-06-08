import axios, { type AxiosInstance, type AxiosRequestConfig, type AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'
import { getCookie, removeCookie } from '@/utils/cookie'

function parseJsonSafely(data: string): any {
  try {
    const safeData = data.replace(/:\s*(-?\d{16,})/g, ':"$1"')
    return JSON.parse(safeData)
  } catch {
    return JSON.parse(data)
  }
}

// 防止重复跳转登录页
let isRedirecting = false

// 清除所有登录状态（cookie + localStorage + Pinia store）
async function clearAuthState() {
  // 清除 cookie（优先）
  removeCookie('token')
  // 清除 localStorage（降级迁移期保留）
  localStorage.removeItem('token')
  localStorage.removeItem('userInfo')
  // 动态导入清除 Pinia store 状态（避免循环依赖）
  try {
    const { useUserStore } = await import('@/stores/user')
    const userStore = useUserStore()
    if (userStore) {
      userStore.$reset?.() || (() => {
        userStore.token = ''
        userStore.userInfo = null
      })()
    }
  } catch {
    // store 未初始化时忽略
  }
}

// 创建axios实例
const request: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:9000/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  },
  transformResponse: [(data) => {
    if (typeof data === 'string') {
      return parseJsonSafely(data)
    }
    return data
  }]
})

// 请求拦截器
request.interceptors.request.use(
  (config: any) => {
    // Cookie 优先读取 token（SameSite=Strict 防 CSRF），localStorage 降级
    const token = getCookie('token') || localStorage.getItem('token')
    if (token) {
      // 确保 headers 对象存在（新版 axios 中 config.headers 可能为 undefined）
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
    
    // 根据后端返回的格式处理
    if (res.code === 200 || res.code === 0) {
      return res.data || res
    } else {
      // 业务错误
      ElMessage.error(res.message || '请求失败')
      return Promise.reject(new Error(res.message || '请求失败'))
    }
  },
  (error: any) => {
    // HTTP错误
    if (error.response) {
      switch (error.response.status) {
        case 401:
          // 如果该请求标记了跳过全局认证处理，只抛错不触发登出（如页面初始化加载）
          if (error.config?.skipAuthRedirect) {
            break
          }
          ElMessage.error('未授权，请重新登录')
          // 防止重复跳转：如果已在登录页或正在跳转中，不再处理
          if (!isRedirecting && window.location.pathname !== '/login') {
            isRedirecting = true
            clearAuthState()
            router.push('/login').finally(() => {
              isRedirecting = false
            })
          }
          break
        case 403:
          if (error.config?.skipAuthRedirect) {
            break
          }
          ElMessage.error('拒绝访问，请重新登录')
          if (!isRedirecting && window.location.pathname !== '/login') {
            isRedirecting = true
            clearAuthState()
            router.push('/login').finally(() => {
              isRedirecting = false
            })
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