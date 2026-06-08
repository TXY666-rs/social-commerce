import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User, UserTokenVO } from '@/types'
import request from '@/utils/request'
import { setCookie, getCookie, removeCookie } from '@/utils/cookie'

const TOKEN_KEY = 'token'

export const useAdminStore = defineStore('admin', () => {
  const token = ref<string>('')
  const userInfo = ref<User | null>(null)
  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => userInfo.value?.role === 1)

  // 从 localStorage / cookie 初始化
  const initFromStorage = () => {
    const storedToken = getCookie(TOKEN_KEY) || localStorage.getItem(TOKEN_KEY)
    const storedUserInfo = localStorage.getItem('admin_userInfo')

    if (storedToken) {
      token.value = storedToken
    }

    if (storedUserInfo) {
      try {
        userInfo.value = JSON.parse(storedUserInfo)
      } catch (e) {
        console.error('解析管理员信息失败', e)
      }
    }
  }

  // 登录（仅管理员可登录后台）
  const login = async (username: string, password: string) => {
    try {
      const response: UserTokenVO = await request.post('/user/login', { username, password })

      if (response.token) {
        // 先获取用户信息判断是否是管理员
        token.value = response.token
        setCookie(TOKEN_KEY, response.token, { days: 7 })
        localStorage.setItem(TOKEN_KEY, response.token)

        // 请求用户详情以获取 role
        try {
          const userDetail: User = await request.get('/user/me')
          if (userDetail.role !== 1) {
            // 不是管理员，清除登录状态
            token.value = ''
            removeCookie(TOKEN_KEY)
            localStorage.removeItem(TOKEN_KEY)
            throw new Error('该账号不是管理员，无法登录后台')
          }
          userInfo.value = userDetail
          localStorage.setItem('admin_userInfo', JSON.stringify(userDetail))
        } catch (e: any) {
          token.value = ''
          removeCookie(TOKEN_KEY)
          localStorage.removeItem(TOKEN_KEY)
          throw e
        }

        return true
      }
      return false
    } catch (error) {
      console.error('管理员登录失败', error)
      throw error
    }
  }

  // 获取用户信息
  const getUserInfo = async () => {
    try {
      const response: User = await request.get('/user/me')
      userInfo.value = response
      localStorage.setItem('admin_userInfo', JSON.stringify(response))
      return response
    } catch (error) {
      console.error('获取管理员信息失败', error)
      throw error
    }
  }

  // 初始化
  initFromStorage()

  // 延迟导入 router 避免循环依赖
  let router: any = null
  const getRouter = async () => {
    if (!router) {
      const m = await import('@/router')
      router = m.default
    }
    return router
  }

  // 登出
  const logout = async () => {
    token.value = ''
    userInfo.value = null
    removeCookie(TOKEN_KEY)
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem('admin_userInfo')
    const r = await getRouter()
    r.push('/login')
  }

  return {
    token,
    userInfo,
    isLoggedIn,
    isAdmin,
    login,
    getUserInfo,
    logout
  }
})
