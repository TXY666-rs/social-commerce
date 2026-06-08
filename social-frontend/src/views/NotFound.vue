<template>
  <div class="not-found-page">
    <div class="nf-inner">
      <div class="nf-code">404</div>
      <h2 class="nf-title">页面未找到</h2>
      <p class="nf-desc">抱歉，您访问的页面不存在或已被移除</p>
      <div class="nf-actions">
        <button class="btn-accent" @click="goHome">返回首页</button>
        <button class="btn-ghost" @click="goBack">返回上一页</button>
      </div>
    </div>
    <div class="nf-glow"></div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
const router = useRouter()
const goHome = () => router.push('/')
const goBack = () => router.back()
</script>

<style scoped lang="scss">
.not-found-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: var(--bg-deep);
  position: relative;
  overflow: hidden;
}

.nf-inner {
  text-align: center;
  position: relative;
  z-index: 2;
  animation: fadeUp 0.7s var(--ease-out) both;
}

.nf-code {
  font-family: var(--font-display);
  font-size: clamp(100px, 15vw, 160px);
  font-weight: 800;
  color: var(--text-primary);
  line-height: 1;
  letter-spacing: -4px;
  opacity: 0.06;
  margin-bottom: -20px;
}

.nf-title {
  font-family: var(--font-display);
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 12px;
}

.nf-desc {
  font-size: 15px;
  color: var(--text-caption);
  margin-bottom: 40px;
}

.nf-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.btn-accent {
  padding: 11px 32px;
  border: none;
  background: var(--accent);
  color: var(--text-inverse);
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: 600;
  border-radius: var(--r-full);
  cursor: pointer;
  transition: all var(--t-fast);

  &:hover {
    background: var(--accent-dark);
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(78, 205, 196, 0.25);
  }
}

.btn-ghost {
  padding: 11px 32px;
  border: 1px solid var(--border-light);
  background: transparent;
  color: var(--text-caption);
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: 500;
  border-radius: var(--r-full);
  cursor: pointer;
  transition: all var(--t-fast);

  &:hover {
    color: var(--text-primary);
    border-color: var(--text-ghost);
    background: rgba(255, 255, 255, 0.04);
  }
}

.nf-glow {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 600px;
  height: 600px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(78, 205, 196, 0.04) 0%, transparent 70%);
  pointer-events: none;
}
</style>
