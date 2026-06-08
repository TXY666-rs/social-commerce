<template>
  <div class="login-page">
    <!-- 左侧视觉区 -->
    <div class="login-visual">
      <div class="visual-content">
        <div class="visual-badge">AI 商城</div>
        <h1 class="visual-headline">
          <span>精选好物</span>
          <span class="accent">为你而来</span>
        </h1>
        <p class="visual-desc">发现独特的商品，享受智能购物体验</p>
      </div>
      <div class="visual-glow"></div>
    </div>

    <!-- 右侧表单 -->
    <div class="login-form-side">
      <div class="form-container">
        <div class="form-header">
          <h2>欢迎回来</h2>
          <p>登录您的账户继续购物</p>
        </div>

        <el-form
          ref="loginFormRef"
          :model="loginForm"
          :rules="loginRules"
          class="login-form"
          @submit.prevent="handleLogin"
        >
          <el-form-item prop="username">
            <el-input v-model="loginForm.username" placeholder="请输入用户名" size="large" :prefix-icon="User" />
          </el-form-item>

          <el-form-item prop="password">
            <el-input v-model="loginForm.password" type="password" placeholder="请输入密码" size="large" :prefix-icon="Lock" show-password @keyup.enter="handleLogin" />
          </el-form-item>

          <div class="form-meta">
            <el-checkbox v-model="rememberMe">记住我</el-checkbox>
            <el-link :underline="false" @click="handleForgotPassword" class="forgot-link">忘记密码？</el-link>
          </div>

          <el-form-item>
            <button type="button" class="submit-btn" :class="{ loading }" :disabled="loading" @click="handleLogin">
              <span v-if="!loading">登录</span>
              <span v-else class="spinner"></span>
            </button>
          </el-form-item>

          <div class="form-footer">
            <span>还没有账户？</span>
            <el-link :underline="false" @click="goToRegister" class="register-link">立即注册</el-link>
          </div>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const loginFormRef = ref<FormInstance>()
const loading = ref(false)
const rememberMe = ref(false)

const loginForm = reactive({ username: '', password: '' })

const loginRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度在 3 到 20 个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 30, message: '密码长度在 6 到 30 个字符', trigger: 'blur' }
  ]
}

const handleLogin = async () => {
  if (!loginFormRef.value) return
  const valid = await loginFormRef.value.validate()
  if (!valid) return

  loading.value = true
  try {
    await userStore.login(loginForm.username, loginForm.password)
    ElMessage.success('登录成功')
    const redirect = (route.query.redirect as string) || '/'
    router.push(redirect)
  } catch (error: any) {
    ElMessage.error(error.message || '登录失败')
  } finally {
    loading.value = false
  }
}

const handleForgotPassword = () => ElMessage.info('请联系管理员重置密码')
const goToRegister = () => router.push('/register')
</script>

<style scoped lang="scss">
.login-page {
  display: flex;
  min-height: 100vh;
}

/* ---- 左侧视觉 ---- */
.login-visual {
  flex: 1;
  background: var(--bg-deep);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 64px;
  position: relative;
  overflow: hidden;
}

.visual-content {
  position: relative;
  z-index: 2;
  animation: fadeUp 0.8s var(--ease-out) both;
}

.visual-badge {
  display: inline-block;
  font-family: var(--font-display);
  font-size: 12px;
  font-weight: 600;
  color: var(--accent);
  letter-spacing: 3px;
  border: 1px solid rgba(78, 205, 196, 0.25);
  padding: 6px 18px;
  border-radius: var(--r-full);
  margin-bottom: 32px;
}

.visual-headline {
  font-family: var(--font-display);
  font-size: clamp(36px, 5vw, 52px);
  font-weight: 800;
  color: var(--text-primary);
  line-height: 1.15;
  letter-spacing: -1px;
  margin-bottom: 20px;

  span { display: block; }
  .accent { color: var(--accent); margin-left: 0.3em; }
}

.visual-desc {
  font-size: 16px;
  color: var(--text-caption);
  margin-left: 0.3em;
}

.visual-glow {
  position: absolute;
  bottom: -150px;
  left: -100px;
  width: 400px;
  height: 400px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(78, 205, 196, 0.06) 0%, transparent 70%);
  pointer-events: none;
}

/* ---- 右侧表单 ---- */
.login-form-side {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 64px 48px;
  background: var(--bg-page);
}

.form-container {
  width: 100%;
  max-width: 380px;
  animation: fadeUp 0.6s var(--ease-out) both;
  animation-delay: 0.2s;
}

.form-header {
  margin-bottom: 36px;

  h2 {
    font-family: var(--font-display);
    font-size: 28px;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 8px;
  }

  p {
    font-size: 14px;
    color: var(--text-caption);
  }
}

.login-form {
  :deep(.el-form-item) { margin-bottom: 20px; }

  :deep(.el-input__wrapper) {
    border-radius: var(--r-md) !important;
    box-shadow: none !important;
    border: 1px solid var(--border) !important;
    padding: 4px 14px;
    transition: all var(--t-fast);
    background: var(--bg-input) !important;

    &:hover { border-color: var(--border-light) !important; }

    &.is-focus {
      border-color: var(--accent) !important;
      box-shadow: var(--shadow-glow) !important;
    }
  }
}

.form-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.forgot-link {
  color: var(--accent) !important;
  font-size: 13px;
}

.submit-btn {
  width: 100%;
  height: 50px;
  border: none;
  background: var(--accent);
  color: var(--text-inverse);
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 600;
  border-radius: var(--r-md);
  cursor: pointer;
  transition: all var(--t-fast);

  &:hover:not(:disabled) {
    background: var(--accent-dark);
    transform: translateY(-1px);
    box-shadow: 0 8px 24px rgba(78, 205, 196, 0.25);
  }

  &:disabled { opacity: 0.6; cursor: not-allowed; }
  &.loading { pointer-events: none; }
}

.spinner {
  display: inline-block;
  width: 18px;
  height: 18px;
  border: 2px solid rgba(30, 36, 51, 0.3);
  border-top-color: var(--text-inverse);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.form-footer {
  text-align: center;
  margin-top: 28px;
  padding-top: 24px;
  border-top: 1px solid var(--border);
  font-size: 14px;
  color: var(--text-caption);

  .register-link {
    color: var(--accent) !important;
    font-weight: 500;
    margin-left: 4px;
  }
}

@media (max-width: 768px) {
  .login-page { flex-direction: column; }
  .login-visual { padding: 40px 24px; min-height: 200px; }
  .visual-headline { font-size: 28px; }
  .login-form-side { padding: 32px 24px; }
}
</style>
