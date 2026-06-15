import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/shop'
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/Login.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/Register.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/shop',
      name: 'shop',
      component: () => import('@/views/Shop.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/shop/:id',
      name: 'product-detail',
      component: () => import('@/views/ProductDetail.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/orders',
      name: 'orders',
      component: () => import('@/views/Orders.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/my-products',
      name: 'my-products',
      component: () => import('@/views/MyProducts.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/profile',
      name: 'profile',
      component: () => import('@/views/Profile.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/addresses',
      name: 'addresses',
      component: () => import('@/views/Addresses.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/admin/knowledge',
      name: 'knowledge-base',
      component: () => import('@/views/admin/KnowledgeBase.vue'),
      meta: { requiresAuth: true, requiresAdmin: true }
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/views/NotFound.vue'),
    },
  ],
})

// 路由守卫
router.beforeEach((to, from, next) => {
  // 检查用户是否已登录（通过 Pinia store，内部已 Cookie 优先）
  const isLoggedIn = useUserStore().isLoggedIn
  
  if (to.meta.requiresAuth && !isLoggedIn) {
    // 需要登录但未登录，跳转到登录页
    next({ path: '/login', query: { redirect: to.fullPath } })
  } else if ((to.path === '/login' || to.path === '/register') && isLoggedIn) {
    // 已登录但访问登录/注册页，跳转到首页
    next('/')
  } else if (to.meta.requiresAdmin) {
    // 需要管理员权限，检查用户角色
    const userInfoStr = localStorage.getItem('userInfo')
    let role = 0
    if (userInfoStr) {
      try {
        const userInfo = JSON.parse(userInfoStr)
        role = userInfo.role ?? 0
      } catch {
        // 解析失败，视为普通用户
      }
    }
    if (role !== 1) {
      // 非管理员，跳转到首页
      next('/')
    } else {
      next()
    }
  } else {
    next()
  }
})

export default router
