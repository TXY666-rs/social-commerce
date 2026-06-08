import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User } from '@/types'
import request from '@/utils/request'
import { setCookie, getCookie, removeCookie } from '@/utils/cookie'

const TOKEN_KEY = 'token'
const USER_INFO_KEY = 'userInfo'

/**
 * 安全读取 token：Cookie 优先 → localStorage 降级
 * Cookie 支持 SameSite=Strict 防 CSRF，且未来可配合后端 httpOnly 加固
 */
function readToken(): string | null {
  return getCookie(TOKEN_KEY) || localStorage.getItem(TOKEN_KEY)
}

function saveToken(value: string): void {
  setCookie(TOKEN_KEY, value, { days: 7 })
  // 降级：迁移期间保留 localStorage 副本，待后端统一 httpOnly 后移除
  localStorage.setItem(TOKEN_KEY, value)
}

function clearToken(): void {
  removeCookie(TOKEN_KEY)
  localStorage.removeItem(TOKEN_KEY)
}

function saveUserInfo(info: User): void {
  localStorage.setItem(USER_INFO_KEY, JSON.stringify(info))
}

export const useUserStore = defineStore('user', () => {
  const token = ref<string>('')
  const userInfo = ref<User | null>(null)
  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => userInfo.value?.role === 1)

  // 从 Cookie / localStorage 初始化
  const initFromStorage = () => {
    const storedToken = readToken()
    const storedUserInfo = localStorage.getItem(USER_INFO_KEY)
    
    if (storedToken) {
      token.value = storedToken
    }
    
    if (storedUserInfo) {
      try {
        userInfo.value = JSON.parse(storedUserInfo)
      } catch (e) {
        console.error('解析用户信息失败', e)
      }
    }
  }

  // 登录
  const login = async (username: string, password: string) => {
    try {
      const response = await request.post('/user/login', { username, password })
      
      if (response.token) {
        token.value = response.token
        saveToken(response.token)
        
        // 优先使用登录接口返回的用户信息，避免额外请求 /user/me
        if (response.userId || response.username) {
          userInfo.value = {
            id: response.userId,
            username: response.username,
            nickname: response.nickname || '',
            avatar: response.avatar || '',
            email: '',
            gender: undefined,
            role: response.role,
          }
          saveUserInfo(userInfo.value)
        } else {
          // 登录返回中没有用户信息，尝试请求 /user/me（失败不阻断登录）
          try {
            await getUserInfo()
          } catch (e) {
            console.error('获取用户信息失败，但不影响登录', e)
          }
        }
        return true
      }
      return false
    } catch (error) {
      console.error('登录失败', error)
      throw error
    }
  }

  // 注册
  const register = async (username: string, password: string, email: string, phone?: string) => {
    try {
      await request.post('/user/register', { username, password, email, phone })
      return true
    } catch (error) {
      console.error('注册失败', error)
      throw error
    }
  }

  // 获取用户信息
  const getUserInfo = async () => {
    try {
      const response = await request.get('/user/me')
      userInfo.value = response
      saveUserInfo(response)
      return response
    } catch (error) {
      console.error('获取用户信息失败', error)
      throw error
    }
  }

  // 更新用户信息
  const updateUserInfo = async (userData: Partial<User>) => {
    try {
      const response = await request.put('/user/update', userData)
      userInfo.value = { ...userInfo.value, ...response }
      saveUserInfo(userInfo.value)
      return response
    } catch (error) {
      console.error('更新用户信息失败', error)
      throw error
    }
  }

  // 登出
  const logout = () => {
    token.value = ''
    userInfo.value = null
    clearToken()
    localStorage.removeItem(USER_INFO_KEY)
    localStorage.removeItem('ai_session_id') // 清理旧的匿名会话残留
    // 使用 router push 跳转登录页
    import('@/router').then(m => m.default.push('/login'))
  }

  // 初始化
  initFromStorage()

  return {
    token,
    userInfo,
    isLoggedIn,
    isAdmin,
    login,
    register,
    getUserInfo,
    updateUserInfo,
    logout
  }
})