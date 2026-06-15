import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

// 初始化 demo token（重构后免登录，admin 直接用 demo 用户）
if (!localStorage.getItem('token')) {
  localStorage.setItem('token', '1')
  document.cookie = 'token=1; path=/; max-age=2592000'
}

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('@/layouts/AdminLayout.vue'),
    children: [
      {
        path: '',
        name: 'dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: '运营概览', icon: 'DataAnalysis' }
      },
      {
        path: 'quality',
        name: 'quality',
        component: () => import('@/views/QualityMonitor.vue'),
        meta: { title: '质量监控', icon: 'TrendCharts' }
      },
      {
        path: 'transfer',
        name: 'transfer',
        component: () => import('@/views/TransferManagement.vue'),
        meta: { title: '转人工管理', icon: 'ChatDotRound' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

export default router
