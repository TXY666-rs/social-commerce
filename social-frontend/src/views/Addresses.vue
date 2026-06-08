<template>
  <div class="addresses-container">
    <div class="addresses-header">
      <h2>收货地址管理</h2>
      <el-button type="primary" @click="openDialog()" class="add-btn">
        <el-icon><Plus /></el-icon> 新增地址
      </el-button>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="address-skeleton">
      <div v-for="i in 3" :key="i" class="skeleton-card">
        <div class="skeleton-line w60"></div>
        <div class="skeleton-line w40"></div>
        <div class="skeleton-line w80"></div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else-if="addresses.length === 0" class="empty-state">
      <el-icon :size="48" color="var(--text-ghost)"><Location /></el-icon>
      <p>还没有收货地址，添加一个吧</p>
      <el-button type="primary" @click="openDialog()">添加地址</el-button>
    </div>

    <!-- Address list -->
    <div v-else class="address-list">
      <div v-for="addr in addresses" :key="addr.id" class="address-card">
        <div class="card-main">
          <div class="card-top">
            <span class="receiver-name">{{ addr.receiverName }}</span>
            <span class="receiver-phone">{{ addr.receiverPhone }}</span>
            <el-tag v-if="addr.isDefault === 1" size="small" type="warning" class="default-tag">默认</el-tag>
          </div>
          <div class="card-address">
            {{ formatFullAddress(addr) }}
          </div>
        </div>
        <div class="card-actions">
          <el-link type="primary" :underline="false" @click="handleSetDefault(addr)" v-if="addr.isDefault !== 1">
            设为默认
          </el-link>
          <el-link type="primary" :underline="false" @click="openDialog(addr)">编辑</el-link>
          <el-link type="danger" :underline="false" @click="handleDelete(addr)">删除</el-link>
        </div>
      </div>
    </div>

    <!-- Add/Edit dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑地址' : '新增地址'"
      width="520px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="formRules"
        label-width="80px"
        class="address-form"
      >
        <el-form-item label="收货人" prop="receiverName">
          <el-input v-model="form.receiverName" placeholder="请输入收货人姓名" maxlength="20" />
        </el-form-item>
        <el-form-item label="手机号" prop="receiverPhone">
          <el-input v-model="form.receiverPhone" placeholder="请输入手机号" maxlength="11" />
        </el-form-item>
        <el-form-item label="省份" prop="province">
          <el-input v-model="form.province" placeholder="省份" />
        </el-form-item>
        <el-form-item label="城市" prop="city">
          <el-input v-model="form.city" placeholder="城市" />
        </el-form-item>
        <el-form-item label="区/县" prop="district">
          <el-input v-model="form.district" placeholder="区/县" />
        </el-form-item>
        <el-form-item label="详细地址" prop="detailAddress">
          <el-input
            v-model="form.detailAddress"
            type="textarea"
            :rows="2"
            placeholder="街道、门牌号等详细地址"
            maxlength="200"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="默认地址">
          <el-switch v-model="form.isDefaultBool" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus, Location } from '@element-plus/icons-vue'
import type { Address } from '@/types'
import {
  getAddressList,
  createAddress,
  updateAddress,
  deleteAddress,
  setDefaultAddress
} from '@/api/address'

const loading = ref(false)
const addresses = ref<Address[]>([])
const dialogVisible = ref(false)
const submitting = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()

const form = reactive({
  receiverName: '',
  receiverPhone: '',
  province: '',
  city: '',
  district: '',
  detailAddress: '',
  isDefaultBool: false
})

const formRules: FormRules = {
  receiverName: [
    { required: true, message: '请输入收货人姓名', trigger: 'blur' },
    { min: 2, max: 20, message: '姓名长度为2-20个字符', trigger: 'blur' }
  ],
  receiverPhone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' }
  ],
  detailAddress: [
    { required: true, message: '请输入详细地址', trigger: 'blur' }
  ]
}

const formatFullAddress = (addr: Address): string => {
  const parts = [addr.province, addr.city, addr.district, addr.detailAddress].filter(Boolean)
  return parts.join(' ')
}

const loadAddresses = async () => {
  loading.value = true
  try {
    addresses.value = await getAddressList()
  } catch (error: any) {
    ElMessage.error(error.message || '加载地址列表失败')
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  form.receiverName = ''
  form.receiverPhone = ''
  form.province = ''
  form.city = ''
  form.district = ''
  form.detailAddress = ''
  form.isDefaultBool = false
}

const openDialog = (addr?: Address) => {
  resetForm()
  if (addr) {
    isEdit.value = true
    editingId.value = addr.id ?? null
    form.receiverName = addr.receiverName
    form.receiverPhone = addr.receiverPhone
    form.province = addr.province || ''
    form.city = addr.city || ''
    form.district = addr.district || ''
    form.detailAddress = addr.detailAddress
    form.isDefaultBool = addr.isDefault === 1
  } else {
    isEdit.value = false
    editingId.value = null
  }
  dialogVisible.value = true
}

const handleSubmit = async () => {
  if (!formRef.value) return
  const valid = await formRef.value.validate()
  if (!valid) return

  submitting.value = true
  try {
    const data: Address = {
      receiverName: form.receiverName,
      receiverPhone: form.receiverPhone,
      province: form.province,
      city: form.city,
      district: form.district,
      detailAddress: form.detailAddress,
      isDefault: form.isDefaultBool ? 1 : 0
    }

    if (isEdit.value && editingId.value !== null) {
      await updateAddress(editingId.value, data)
      ElMessage.success('地址修改成功')
    } else {
      await createAddress(data)
      ElMessage.success('地址添加成功')
    }
    dialogVisible.value = false
    await loadAddresses()
  } catch (error: any) {
    ElMessage.error(error.message || '保存失败')
  } finally {
    submitting.value = false
  }
}

const handleDelete = async (addr: Address) => {
  try {
    await ElMessageBox.confirm(
      `确定删除收货地址「${addr.receiverName} - ${formatFullAddress(addr)}」吗？`,
      '删除确认',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
    await deleteAddress(addr.id!)
    ElMessage.success('删除成功')
    await loadAddresses()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

const handleSetDefault = async (addr: Address) => {
  try {
    await setDefaultAddress(addr.id!)
    ElMessage.success('已设为默认地址')
    await loadAddresses()
  } catch (error: any) {
    ElMessage.error(error.message || '设置失败')
  }
}

onMounted(() => {
  loadAddresses()
})
</script>

<style scoped lang="scss">
.addresses-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 32px 24px;
}

.addresses-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 28px;

  h2 {
    font-family: var(--font-display);
    font-size: 22px;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0;
  }

  .add-btn {
    background: linear-gradient(135deg, var(--accent-dark), var(--accent));
    border: none;
    border-radius: var(--r-full, 999px);
    padding: 10px 24px;
    font-weight: 600;

    &:hover {
      background: var(--accent-dark);
    }
  }
}

/* Skeleton */
.address-skeleton {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.skeleton-card {
  background: var(--bg-card);
  border-radius: var(--radius-lg, 12px);
  padding: 24px;
  border: 1px solid var(--border-light);

  .skeleton-line {
    height: 16px;
    border-radius: 4px;
    background: linear-gradient(90deg, var(--border-light) 25%, rgba(255,255,255,0.06) 50%, var(--border-light) 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    margin-bottom: 12px;

    &:last-child { margin-bottom: 0; }
  }

  .w60 { width: 60%; }
  .w40 { width: 40%; }
  .w80 { width: 80%; }
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* Empty */
.empty-state {
  text-align: center;
  padding: 64px 0;

  p {
    color: var(--text-muted);
    margin: 16px 0 24px;
    font-size: 15px;
  }
}

/* Address list */
.address-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.address-card {
  background: var(--bg-card);
  border-radius: var(--radius-lg, 12px);
  padding: 20px 24px;
  border: 1px solid var(--border-light);
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: border-color var(--t-fast, 0.2s), box-shadow var(--t-fast, 0.2s);

  &:hover {
    border-color: var(--accent);
    box-shadow: 0 2px 12px rgba(78, 205, 196, 0.08);
  }
}

.card-main {
  flex: 1;
  min-width: 0;
}

.card-top {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;

  .receiver-name {
    font-weight: 600;
    font-size: 16px;
    color: var(--text-primary);
  }

  .receiver-phone {
    font-size: 14px;
    color: var(--text-secondary);
  }

  .default-tag {
    flex-shrink: 0;
  }
}

.card-address {
  font-size: 14px;
  color: var(--text-caption);
  line-height: 1.5;
}

.card-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex-shrink: 0;
  margin-left: 24px;
}

/* Dialog form */
.address-form {
  :deep(.el-form-item) {
    margin-bottom: 18px;
  }

  :deep(.el-input__wrapper) {
    border-radius: var(--radius-sm, 6px);
  }

  :deep(.el-textarea__inner) {
    border-radius: var(--radius-sm, 6px);
  }
}

/* Mobile */
@media (max-width: 768px) {
  .addresses-container {
    padding: 20px 16px;
  }

  .addresses-header h2 {
    font-size: 18px;
  }

  .address-card {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .card-actions {
    flex-direction: row;
    margin-left: 0;
    gap: 16px;
  }
}
</style>
