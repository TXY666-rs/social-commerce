<template>
  <div class="profile-container">
    <div class="profile-card">
      <!-- Header banner -->
      <div class="profile-banner">
        <div class="banner-content">
          <el-avatar :size="80" :src="avatarUrl" class="profile-avatar">
            <el-icon :size="32"><User /></el-icon>
          </el-avatar>
          <div class="banner-info">
            <h2>{{ profileForm.username || '用户' }}</h2>
            <p>{{ profileForm.signature || '这个人很懒，什么都没留下' }}</p>
          </div>
          <el-upload
            class="avatar-upload"
            :action="uploadAction"
            :headers="uploadHeaders"
            :data="{ module: 'avatar' }"
            :show-file-list="false"
            :on-success="handleAvatarSuccess"
            :before-upload="beforeAvatarUpload"
            accept="image/*"
          >
            <el-button size="small" class="change-avatar-btn">更换头像</el-button>
          </el-upload>
        </div>
      </div>

      <!-- Form -->
      <div class="profile-content">
        <el-form
          ref="profileFormRef"
          :model="profileForm"
          :rules="profileRules"
          label-width="80px"
          class="profile-form"
        >
          <el-form-item label="用户名" prop="username">
            <el-input v-model="profileForm.username" disabled />
            <div class="form-tip">用户名不可修改</div>
          </el-form-item>

          <el-form-item label="邮箱" prop="email">
            <el-input v-model="profileForm.email" />
          </el-form-item>

          <el-form-item label="手机号" prop="phone">
            <el-input v-model="profileForm.phone" />
          </el-form-item>

          <el-form-item label="个性签名" prop="signature">
            <el-input v-model="profileForm.signature" type="textarea" :rows="3" placeholder="介绍一下自己吧~" />
          </el-form-item>

          <el-form-item>
            <el-button type="primary" :loading="loading" @click="handleSave" class="save-btn">保存修改</el-button>
            <el-button @click="goBack">返回</el-button>
          </el-form-item>
        </el-form>

        <!-- Action cards -->
        <div class="profile-actions">
          <div class="action-card">
            <h3>账户安全</h3>
            <div class="action-item">
              <span>修改密码</span>
              <el-link type="primary" :underline="false" @click="handleChangePassword">修改</el-link>
            </div>
            <div class="action-item">
              <span>登录设备</span>
              <el-link type="primary" :underline="false" @click="handleDeviceManage">管理</el-link>
            </div>
          </div>

          <div class="action-card">
            <h3>其他操作</h3>
            <div class="action-item">
              <span>注销账户</span>
              <el-link type="danger" :underline="false" @click="handleDeleteAccount">注销</el-link>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { User } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:9000/api'
const uploadAction = `${apiBaseUrl}/upload/image`
const uploadHeaders = computed(() => {
  const token = userStore.token
  return token ? { Authorization: `Bearer ${token}` } : {}
})

const avatarUrl = computed(() => {
  const avatar = userStore.userInfo?.avatar
  if (!avatar) return ''
  if (avatar.startsWith('http')) return avatar
  return `${apiBaseUrl}${avatar}`
})

const profileFormRef = ref<FormInstance>()
const loading = ref(false)

const profileForm = reactive({
  username: '',
  email: '',
  phone: '',
  signature: ''
})

const profileRules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
  ],
  phone: [
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' }
  ]
}

onMounted(() => {
  if (userStore.userInfo) {
    profileForm.username = userStore.userInfo.username || ''
    profileForm.email = userStore.userInfo.email || ''
    profileForm.phone = userStore.userInfo.phone || ''
    profileForm.signature = userStore.userInfo.signature || ''
  }
})

const beforeAvatarUpload = (file: File) => {
  const isImage = file.type.startsWith('image/')
  const isLt5M = file.size / 1024 / 1024 < 5
  if (!isImage) {
    ElMessage.error('只能上传图片文件！')
    return false
  }
  if (!isLt5M) {
    ElMessage.error('图片大小不能超过5MB！')
    return false
  }
  return true
}

const handleAvatarSuccess = async (response: any) => {
  if (response.code === 200 && response.data?.url) {
    const avatarUrl = response.data.url
    try {
      await userStore.updateUserInfo({ avatar: avatarUrl })
      ElMessage.success('头像更新成功')
    } catch (error: any) {
      ElMessage.error(error.message || '头像更新失败')
    }
  } else {
    ElMessage.error(response.message || '头像上传失败')
  }
}

const handleSave = async () => {
  if (!profileFormRef.value) return
  const valid = await profileFormRef.value.validate()
  if (!valid) return
  loading.value = true
  try {
    await userStore.updateUserInfo({
      email: profileForm.email,
      phone: profileForm.phone,
      signature: profileForm.signature,
    })
    ElMessage.success('保存成功')
  } catch (error: any) {
    ElMessage.error(error.message || '保存失败')
  } finally {
    loading.value = false
  }
}

const handleChangePassword = () => ElMessage.info('修改密码功能开发中')
const handleDeviceManage = () => ElMessage.info('设备管理功能开发中')
const handleDeleteAccount = () => ElMessage.warning('账户注销功能开发中，请联系客服')
const goBack = () => router.back()
</script>

<style scoped lang="scss">
.profile-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 24px;
}

.profile-card {
  background: var(--bg-card);
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--shadow-md);
  border: 1px solid var(--border-light);
}

.profile-banner {
  background: linear-gradient(135deg, var(--accent-dark), var(--accent));
  padding: 32px;

  .banner-content {
    display: flex;
    align-items: center;
    gap: 20px;
    color: #fff;

    .profile-avatar {
      border: 3px solid rgba(255, 255, 255, 0.3);
      flex-shrink: 0;
    }

    .banner-info {
      flex: 1;

      h2 {
        font-size: 22px;
        font-weight: 700;
        margin: 0 0 4px;
      }

      p {
        font-size: 14px;
        opacity: 0.85;
        margin: 0;
      }
    }

    .change-avatar-btn {
      background: rgba(255, 255, 255, 0.2);
      border: 1px solid rgba(255, 255, 255, 0.3);
      color: #fff;
      border-radius: var(--radius-full);

      &:hover {
        background: rgba(255, 255, 255, 0.3);
      }
    }
  }
}

.profile-content {
  padding: 28px 32px 32px;
}

.profile-form {
  margin-bottom: 28px;

  :deep(.el-form-item) {
    margin-bottom: 20px;
  }

  :deep(.el-input__wrapper) {
    border-radius: var(--radius-sm);
  }

  .form-tip {
    font-size: 12px;
    color: var(--text-muted);
    margin-top: 4px;
  }

  .save-btn {
    background: linear-gradient(135deg, var(--accent-dark), var(--accent));
    border: none;
    border-radius: var(--radius-sm);

    &:hover {
      background: var(--accent-dark);
    }
  }
}

.profile-actions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;

  .action-card {
    background: var(--bg-page);
    border-radius: var(--radius-lg);
    padding: 18px 20px;

    h3 {
      font-size: 15px;
      font-weight: 600;
      color: var(--text-primary);
      margin: 0 0 12px;
    }

    .action-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 10px 0;
      border-bottom: 1px solid var(--border-light);

      &:last-child {
        border-bottom: none;
      }

      span {
        font-size: 14px;
        color: var(--text-secondary);
      }
    }
  }
}
</style>
