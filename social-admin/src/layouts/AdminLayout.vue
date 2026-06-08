<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAdminStore } from '@/stores/admin'
import { ElMessage } from 'element-plus'
import {
  DataAnalysis,
  SwitchButton,
  Menu as MenuIcon,
  Expand,
  Fold,
  ChatDotRound,
  TrendCharts,
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const adminStore = useAdminStore()
const isCollapse = ref(false)

const menuItems = [
  { path: '/', icon: DataAnalysis, title: '运营概览' },
  { path: '/quality', icon: TrendCharts, title: '质量监控' },
  { path: '/transfer', icon: ChatDotRound, title: '转人工管理' },
]

const currentPath = computed(() => route.path)

const handleLogout = () => {
  adminStore.logout()
  ElMessage.success('已退出登录')
}

const toggleCollapse = () => {
  isCollapse.value = !isCollapse.value
}
</script>

<template>
  <div class="admin-layout">
    <!-- 侧边栏 -->
    <aside class="sidebar" :class="{ collapsed: isCollapse }">
      <div class="sidebar-header">
        <div class="sidebar-logo">
          <el-icon :size="22" color="#4ECDC4"><ShoppingBag /></el-icon>
          <span v-if="!isCollapse" class="sidebar-title">管理后台</span>
        </div>
      </div>
      <el-menu
        :default-active="currentPath"
        :collapse="isCollapse"
        router
        background-color="transparent"
        text-color="#A0A8AD"
        active-text-color="#4ECDC4"
        class="sidebar-menu"
      >
        <el-menu-item v-for="item in menuItems" :key="item.path" :index="item.path">
          <el-icon><component :is="item.icon" /></el-icon>
          <template #title>{{ item.title }}</template>
        </el-menu-item>
      </el-menu>
    </aside>

    <!-- 主内容区 -->
    <div class="main-area" :class="{ expanded: isCollapse }">
      <!-- 顶部栏 -->
      <header class="top-bar">
        <div class="top-bar-left">
          <el-icon class="collapse-btn" @click="toggleCollapse" :size="20">
            <component :is="isCollapse ? Expand : Fold" />
          </el-icon>
          <span class="page-title">{{ (route.meta.title as string) || '管理后台' }}</span>
        </div>
        <div class="top-bar-right">
          <el-dropdown>
            <div class="admin-info">
              <el-avatar :size="32" :src="adminStore.userInfo?.avatar" />
              <span class="admin-name">{{ adminStore.userInfo?.username || '管理员' }}</span>
              <el-icon><component :is="'ArrowDown'" /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="handleLogout">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <!-- 页面内容 -->
      <main class="content-area">
        <router-view />
      </main>
    </div>
  </div>
</template>

<style scoped lang="scss">
.admin-layout {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  width: 220px;
  background: var(--bg-deep);
  display: flex;
  flex-direction: column;
  transition: width 0.3s;
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  z-index: 100;
  border-right: 1px solid var(--border);

  &.collapsed {
    width: 64px;
  }

  .sidebar-header {
    height: 64px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-bottom: 1px solid var(--border);

    .sidebar-logo {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .sidebar-title {
      color: var(--text-primary);
      font-family: var(--font-display);
      font-size: 18px;
      font-weight: 700;
      white-space: nowrap;
      letter-spacing: -0.3px;
    }
  }

  .sidebar-menu {
    border-right: none;
    flex: 1;
    padding: 8px;

    :deep(.el-menu-item) {
      border-radius: var(--r-md);
      margin-bottom: 2px;
      height: 44px;
      line-height: 44px;

      &:hover {
        background-color: var(--bg-card) !important;
      }
      &.is-active {
        background-color: var(--accent-glow) !important;
        color: var(--accent) !important;
      }
    }
  }
}

.main-area {
  flex: 1;
  margin-left: 220px;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  transition: margin-left 0.3s;

  &.expanded {
    margin-left: 64px;
  }
}

.top-bar {
  height: 56px;
  background: var(--bg-deep);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.2);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
  position: sticky;
  top: 0;
  z-index: 99;
  border-bottom: 1px solid var(--border);

  .top-bar-left {
    display: flex;
    align-items: center;
    gap: 12px;

    .collapse-btn {
      cursor: pointer;
      color: var(--text-caption);
      transition: color var(--t-fast);
      &:hover { color: var(--accent); }
    }

    .page-title {
      font-family: var(--font-display);
      font-size: 16px;
      font-weight: 600;
      color: var(--text-primary);
    }
  }

  .top-bar-right {
    .admin-info {
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      padding: 6px 12px;
      border-radius: var(--r-full);
      transition: background var(--t-fast);
      &:hover { background: var(--bg-card); }

      .admin-name {
        font-size: 14px;
        color: var(--text-primary);
      }
    }
  }
}

.content-area {
  flex: 1;
  padding: 20px;
  background: var(--bg-page);
}
</style>
