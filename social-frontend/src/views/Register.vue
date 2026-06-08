<template>
  <div class="register-container">
    <div class="register-card">
      <div class="register-header">
        <div class="brand-icon">
          <el-icon :size="32" color="#fff"><ShoppingBag /></el-icon>
        </div>
        <h1>创建账户</h1>
        <p>加入 AI 商城，开启全新购物体验</p>
      </div>

      <el-form
        ref="registerFormRef"
        :model="registerForm"
        :rules="registerRules"
        class="register-form"
        @submit.prevent="handleRegister"
      >
        <el-form-item prop="username">
          <el-input
            v-model="registerForm.username"
            placeholder="请输入用户名"
            size="large"
            :prefix-icon="User"
            @blur="checkUsername"
          />
          <div v-if="usernameStatus" class="field-status" :class="usernameStatus">
            {{ usernameMessage }}
          </div>
        </el-form-item>

        <el-form-item prop="email">
          <el-input
            v-model="registerForm.email"
            placeholder="请输入邮箱"
            size="large"
            :prefix-icon="Message"
            @blur="checkEmail"
          />
          <div v-if="emailStatus" class="field-status" :class="emailStatus">
            {{ emailMessage }}
          </div>
        </el-form-item>

        <el-form-item prop="phone">
          <el-input
            v-model="registerForm.phone"
            placeholder="请输入手机号（可选）"
            size="large"
            :prefix-icon="Phone"
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="registerForm.password"
            type="password"
            placeholder="请输入密码"
            size="large"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>

        <el-form-item prop="confirmPassword">
          <el-input
            v-model="registerForm.confirmPassword"
            type="password"
            placeholder="请确认密码"
            size="large"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>

        <div class="agreement-row">
          <el-checkbox v-model="agreement">
            我已阅读并同意
            <el-link type="primary" :underline="false" @click="showAgreement">《用户协议》</el-link>
            和
            <el-link type="primary" :underline="false" @click="showPrivacy">《隐私政策》</el-link>
          </el-checkbox>
        </div>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            class="register-button"
            :loading="loading"
            :disabled="!agreement"
            @click="handleRegister"
          >
            注册
          </el-button>
        </el-form-item>

        <div class="register-footer">
          <span>已有账户？</span>
          <el-link type="primary" :underline="false" @click="goToLogin">立即登录</el-link>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { User, Lock, Message, Phone, ShoppingBag } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { checkUsernameExists, checkEmailExists } from '@/api/user'

const router = useRouter()
const userStore = useUserStore()

const registerFormRef = ref<FormInstance>()
const loading = ref(false)
const agreement = ref(false)
const usernameStatus = ref<'checking' | 'success' | 'error'>()
const emailStatus = ref<'checking' | 'success' | 'error'>()
const usernameMessage = ref('')
const emailMessage = ref('')

const registerForm = reactive({
  username: '',
  email: '',
  phone: '',
  password: '',
  confirmPassword: ''
})

const validateConfirmPassword = (rule: any, value: string, callback: any) => {
  if (value !== registerForm.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const registerRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度在 3 到 20 个字符', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_]+$/, message: '用户名只能包含字母、数字和下划线', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
  ],
  phone: [
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 30, message: '密码长度在 6 到 30 个字符', trigger: 'blur' },
    { pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[^]{6,}$/, message: '密码必须包含大小写字母和数字', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

watch(() => registerForm.username, () => {
  if (usernameStatus.value === 'error') {
    usernameStatus.value = undefined
  }
})

watch(() => registerForm.email, () => {
  if (emailStatus.value === 'error') {
    emailStatus.value = undefined
  }
})

const checkUsername = async () => {
  if (!registerForm.username || registerForm.username.length < 3) return
  usernameStatus.value = 'checking'
  usernameMessage.value = '检查中...'
  try {
    const exists = await checkUsernameExists(registerForm.username)
    if (exists) {
      usernameStatus.value = 'error'
      usernameMessage.value = '用户名已存在'
    } else {
      usernameStatus.value = 'success'
      usernameMessage.value = '用户名可用'
    }
  } catch {
    usernameStatus.value = undefined
    usernameMessage.value = ''
  }
}

const checkEmail = async () => {
  if (!registerForm.email) return
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailRegex.test(registerForm.email)) return
  emailStatus.value = 'checking'
  emailMessage.value = '检查中...'
  try {
    const exists = await checkEmailExists(registerForm.email)
    if (exists) {
      emailStatus.value = 'error'
      emailMessage.value = '邮箱已存在'
    } else {
      emailStatus.value = 'success'
      emailMessage.value = '邮箱可用'
    }
  } catch {
    emailStatus.value = undefined
    emailMessage.value = ''
  }
}

const handleRegister = async () => {
  if (!registerFormRef.value) return
  const valid = await registerFormRef.value.validate()
  if (!valid) return
  if (!agreement.value) {
    ElMessage.warning('请先阅读并同意用户协议和隐私政策')
    return
  }
  loading.value = true
  try {
    await userStore.register(
      registerForm.username,
      registerForm.password,
      registerForm.email,
      registerForm.phone || undefined
    )
    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } catch (error: any) {
    ElMessage.error(error.message || '注册失败')
  } finally {
    loading.value = false
  }
}

const showAgreement = () => ElMessage.info('用户协议内容')
const showPrivacy = () => ElMessage.info('隐私政策内容')
const goToLogin = () => router.push('/login')
</script>

<style scoped lang="scss">
.register-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: var(--bg-page);
  padding: 20px;
}

.register-card {
  width: 100%;
  max-width: 420px;
  padding: 40px;
  background: var(--bg-card);
  border-radius: var(--r-xl);
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--border);
  overflow-y: auto;
  max-height: 92vh;
  animation: fadeUp 0.6s var(--ease-out) both;
}

.register-header {
  text-align: center;
  margin-bottom: 32px;

  .brand-icon {
    width: 48px;
    height: 48px;
    border-radius: var(--r-md);
    background: linear-gradient(135deg, var(--accent), var(--accent-dark));
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 20px;
    box-shadow: 0 4px 12px rgba(78, 205, 196, 0.3);
  }

  h1 {
    font-family: var(--font-display);
    font-size: var(--text-2xl);
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 6px;
  }

  p {
    font-size: var(--text-base);
    color: var(--text-caption);
  }
}

.register-form {
  :deep(.el-form-item) { margin-bottom: 18px; }

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

.field-status {
  font-size: 12px;
  margin-top: 4px;

  &.checking { color: var(--text-ghost); }
  &.success { color: var(--lime); }
  &.error { color: #E86A6A; }
}

.agreement-row { margin-bottom: 18px; }

.register-button {
  width: 100%;
  height: 50px;
  border-radius: var(--r-md);
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 600;
  background: var(--accent);
  color: var(--text-inverse);
  border: none;
  cursor: pointer;
  transition: all var(--t-fast);

  &:hover {
    background: var(--accent-dark);
    transform: translateY(-1px);
    box-shadow: 0 8px 24px rgba(78, 205, 196, 0.25);
  }

  &:disabled { opacity: 0.6; cursor: not-allowed; }
}

.register-footer {
  text-align: center;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--border);
  font-size: var(--text-base);
  color: var(--text-caption);

  .el-link { margin-left: 4px; font-weight: 500; color: var(--accent) !important; }
}
</style>
