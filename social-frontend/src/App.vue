<script setup lang="ts">
import { computed } from 'vue'
import { RouterView, useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import AiCustomerService from '@/components/AiCustomerService.vue'
import {
  User,
  SwitchButton,
  ArrowDown,
  ShoppingBag,
  List,
  Present,
  Search,
  Location
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const appTitle = computed(() => {
  return import.meta.env.VITE_APP_TITLE || 'AI 商城'
})

const goToLogin = () => router.push('/login')
const goToRegister = () => router.push('/register')
const goToProfile = () => router.push('/profile')
const goToAddresses = () => router.push('/addresses')

const handleLogout = () => {
  userStore.logout()
  ElMessage.success('已退出登录')
}
</script>

<template>
  <div class="app-container">
    <!-- F4: 无障碍 — 跳过导航链接 -->
    <a href="#main-content" class="skip-to-content">跳到主要内容</a>

    <header v-if="!route.meta?.hideNav" class="app-header" role="banner">
      <div class="header-inner">
        <!-- 左侧 Logo + 导航 -->
        <div class="header-left">
          <div class="logo" @click="router.push('/shop')" @keydown.enter="router.push('/shop')" tabindex="0" role="link" aria-label="返回商城首页">
            <div class="logo-icon" aria-hidden="true">
              <el-icon :size="20" color="#fff"><ShoppingBag /></el-icon>
            </div>
            <span class="logo-text">{{ appTitle }}</span>
          </div>

          <nav class="main-nav" role="navigation" aria-label="主导航">
            <router-link
              to="/shop"
              class="nav-link"
              :class="{ active: route.path.startsWith('/shop') }"
              aria-current="page"
            >
              <span>商城</span>
            </router-link>
            <router-link
              v-if="userStore.isLoggedIn"
              to="/orders"
              class="nav-link"
              :class="{ active: route.path === '/orders' }"
            >
              <span>订单</span>
            </router-link>
            <router-link
              to="/activity"
              class="nav-link"
              :class="{ active: route.path === '/activity' || route.path === '/my-coupons' }"
            >
              <span>活动</span>
            </router-link>
          </nav>
        </div>

        <!-- 右侧 用户区 -->
        <div class="header-right">
          <div v-if="userStore.isLoggedIn" class="user-menu">
            <el-dropdown trigger="click" aria-label="用户菜单">
              <div class="user-trigger" tabindex="0" role="button" :aria-label="'当前用户: ' + (userStore.userInfo?.username || '用户')">
                <el-avatar :size="32" :src="userStore.userInfo?.avatar" class="user-avatar" aria-hidden="true">
                  <el-icon :size="15"><User /></el-icon>
                </el-avatar>
                <span class="user-name">{{ userStore.userInfo?.username || '用户' }}</span>
                <el-icon class="chevron" aria-hidden="true"><ArrowDown /></el-icon>
              </div>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="goToProfile">
                    <el-icon aria-hidden="true"><User /></el-icon> 个人中心
                  </el-dropdown-item>
                  <el-dropdown-item @click="goToAddresses">
                    <el-icon aria-hidden="true"><Location /></el-icon> 收货地址
                  </el-dropdown-item>
                  <el-dropdown-item divided @click="handleLogout">
                    <el-icon aria-hidden="true"><SwitchButton /></el-icon> 退出登录
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
          <div v-else class="auth-actions">
            <button class="btn-ghost" @click="goToLogin" aria-label="登录">登录</button>
            <button class="btn-accent" @click="goToRegister" aria-label="注册新账户">注册</button>
          </div>
        </div>
      </div>
    </header>

    <main id="main-content" class="app-main" role="main">
      <RouterView />
    </main>

    <AiCustomerService v-if="userStore.isLoggedIn" />
  </div>
</template>

<style scoped lang="scss">
.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

/* F4: 无障碍 — 跳过导航链接 */
.skip-to-content {
  position: absolute;
  top: -100px;
  left: 16px;
  background: var(--accent);
  color: #fff;
  padding: 8px 16px;
  border-radius: 0 0 8px 8px;
  z-index: 10000;
  font-size: 14px;
  text-decoration: none;
  transition: top 0.2s;

  &:focus {
    top: 0;
  }
}

/* ---- 导航栏 ---- */
.app-header {
  height: 72px;
  background: rgba(30, 36, 51, 0.92);
  backdrop-filter: blur(20px) saturate(1.4);
  -webkit-backdrop-filter: blur(20px) saturate(1.4);
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  z-index: 1000;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.15);
}

.header-inner {
  max-width: 1320px;
  margin: 0 auto;
  height: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 32px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 48px;
}

/* ---- Logo ---- */
.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  user-select: none;

  .logo-icon {
    width: 38px;
    height: 38px;
    border-radius: 10px;
    background: linear-gradient(135deg, var(--accent), var(--accent-dark));
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 12px rgba(78, 205, 196, 0.3);
    transition: transform var(--t-fast);
  }

  .logo-text {
    font-family: var(--font-display);
    font-size: 20px;
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: -0.3px;
  }

  &:hover .logo-icon {
    transform: scale(1.08);
  }
}

/* ---- 导航链接 ---- */
.main-nav {
  display: flex;
  align-items: center;
  gap: 4px;
}

.nav-link {
  position: relative;
  padding: 8px 18px;
  color: var(--text-caption);
  text-decoration: none;
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 500;
  letter-spacing: 0.3px;
  border-radius: var(--r-md);
  transition: all var(--t-fast);

  &:hover {
    color: var(--text-primary);
    background: rgba(255, 255, 255, 0.05);
  }

  &.active {
    color: var(--accent);
    font-weight: 600;

    &::after {
      content: '';
      position: absolute;
      bottom: -1px;
      left: 50%;
      transform: translateX(-50%);
      width: 20px;
      height: 2px;
      background: var(--accent);
      border-radius: 1px;
      box-shadow: 0 0 8px var(--accent-glow2);
    }
  }
}

/* ---- 认证按钮 ---- */
.auth-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.btn-ghost {
  padding: 9px 22px;
  border: 1px solid var(--border-light);
  background: transparent;
  color: var(--text-caption);
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border-radius: var(--r-full);
  transition: all var(--t-fast);

  &:hover {
    color: var(--text-primary);
    border-color: var(--text-ghost);
    background: rgba(255, 255, 255, 0.04);
  }
}

.btn-accent {
  padding: 9px 24px;
  border: none;
  background: var(--accent);
  color: var(--text-inverse);
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  border-radius: var(--r-full);
  transition: all var(--t-fast);

  &:hover {
    background: var(--accent-dark);
    transform: translateY(-1px);
    box-shadow: 0 4px 16px rgba(78, 205, 196, 0.3);
  }
}

/* ---- 用户菜单 ---- */
.user-trigger {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  padding: 5px 12px 5px 5px;
  border-radius: var(--r-full);
  transition: background var(--t-fast);

  &:hover {
    background: rgba(255, 255, 255, 0.06);
  }

  .user-avatar {
    background: var(--bg-card);
    color: var(--accent);
    border: 2px solid var(--border);
  }

  .user-name {
    font-family: var(--font-display);
    font-size: 14px;
    font-weight: 500;
    color: var(--text-primary);
    max-width: 100px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .chevron {
    font-size: 12px;
    color: var(--text-ghost);
  }
}

/* ---- Main ---- */
.app-main {
  flex: 1;
  background: var(--bg-page);
}

/* ---- 移动端 ---- */
@media (max-width: 768px) {
  .header-inner {
    padding: 0 16px;
  }

  .header-left {
    gap: 16px;
  }

  .logo .logo-text {
    display: none;
  }

  .nav-link span {
    display: none;
  }

  .user-trigger .user-name {
    display: none;
  }
}
</style>
