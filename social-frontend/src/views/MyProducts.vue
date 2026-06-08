<template>
  <div class="my-products-container">
    <!-- Header -->
    <div class="page-header">
      <div class="header-left">
        <h2>我的商品</h2>
        <span class="count-badge">{{ total }} 件</span>
      </div>
      <div class="header-right">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索商品..."
          :prefix-icon="Search"
          clearable
          style="width: 200px"
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        />
        <el-select v-model="selectedStatus" placeholder="状态" clearable style="width: 110px" @change="handleSearch">
          <el-option label="上架中" :value="1" />
          <el-option label="已下架" :value="0" />
        </el-select>
        <el-select v-model="selectedCategory" placeholder="分类" clearable style="width: 130px" @change="handleSearch">
          <el-option v-for="cat in categories" :key="cat" :label="cat" :value="cat" />
        </el-select>
        <el-button type="primary" @click="openCreateDialog" class="create-btn">
          <el-icon><Plus /></el-icon>
          发布商品
        </el-button>
      </div>
    </div>

    <!-- Product table -->
    <div v-loading="loading" class="product-table-wrapper">
      <el-empty v-if="!loading && products.length === 0" description="暂无商品，点击上方按钮发布" />

      <el-table v-else :data="products" style="width: 100%" :header-cell-style="{ background: 'var(--bg-deep)', color: 'var(--text-caption)', fontWeight: '600' }">
        <el-table-column label="商品" min-width="260">
          <template #default="{ row }">
            <div class="product-cell">
              <el-image :src="getProductImageUrl(row)" fit="cover" class="product-thumb">
                <template #error>
                  <div class="thumb-placeholder">
                    <el-icon :size="18" color="#cbd5e1"><Picture /></el-icon>
                  </div>
                </template>
              </el-image>
              <div class="product-cell-info">
                <span class="product-cell-name">{{ row.name }}</span>
                <div class="product-cell-tags">
                  <span v-for="cat in (row.categories || [])" :key="cat" class="mini-tag">{{ cat }}</span>
                </div>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="价格" width="110" align="center">
          <template #default="{ row }">
            <span class="price-text">¥{{ row.price?.toFixed(2) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="销量" width="70" align="center">
          <template #default="{ row }">{{ row.saleCount || 0 }}</template>
        </el-table-column>

        <el-table-column label="浏览" width="70" align="center">
          <template #default="{ row }">{{ row.viewCount || 0 }}</template>
        </el-table-column>

        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <span class="status-dot" :class="row.status === 1 ? 'active' : 'inactive'">
              {{ row.status === 1 ? '上架中' : '已下架' }}
            </span>
          </template>
        </el-table-column>

        <el-table-column label="发布时间" width="160" align="center">
          <template #default="{ row }">{{ formatTime(row.createTime) }}</template>
        </el-table-column>

        <el-table-column label="操作" width="200" align="center" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button :type="row.status === 1 ? 'warning' : 'success'" link size="small" @click="handleToggleStatus(row)">
              {{ row.status === 1 ? '下架' : '上架' }}
            </el-button>
            <el-button type="danger" link size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Pagination -->
    <div class="pagination-container" v-if="total > 0">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="20"
        :total="total"
        layout="total, prev, pager, next, jumper"
        @current-change="handlePageChange"
      />
    </div>

    <!-- Edit dialog -->
    <el-dialog v-model="showEditDialog" title="编辑商品" width="640px" :close-on-click-modal="false" destroy-on-close>
      <el-form :model="editForm" :rules="editRules" ref="editFormRef" label-width="80px">
        <el-form-item label="商品名称" prop="name">
          <el-input v-model="editForm.name" placeholder="请输入商品名称" maxlength="100" show-word-limit />
        </el-form-item>
        <el-form-item label="商品描述" prop="description">
          <el-input v-model="editForm.description" type="textarea" :rows="4" placeholder="请描述商品" maxlength="500" show-word-limit />
        </el-form-item>
        <el-form-item label="价格" prop="price">
          <el-input-number v-model="editForm.price" :min="0" :precision="2" :step="1" style="width: 200px" />
        </el-form-item>
        <el-form-item label="分类" prop="categories">
          <el-select v-model="editForm.categories" placeholder="选择分类（可多选）" clearable multiple style="width: 300px">
            <el-option v-for="cat in categories" :key="cat" :label="cat" :value="cat" />
          </el-select>
        </el-form-item>
        <el-form-item label="配送方式" prop="deliveryTypes">
          <span style="font-size: 14px; color: var(--text-primary);">快递发货</span>
        </el-form-item>
        <el-form-item label="商品图片">
          <el-upload
            :action="uploadAction"
            :headers="uploadHeaders"
            :data="{ module: 'product' }"
            list-type="picture-card"
            :file-list="editFileList"
            :on-success="handleEditUploadSuccess"
            :on-remove="handleEditUploadRemove"
            :before-upload="beforeUpload"
            accept="image/*"
            :limit="5"
            :on-exceed="() => ElMessage.warning('最多上传5张图片')"
          >
            <el-icon :size="28"><Plus /></el-icon>
          </el-upload>
          <div class="upload-tip">支持 jpg/png/gif/webp，单张不超过10MB，最多5张</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSaveEdit" :loading="editLoading">保存修改</el-button>
      </template>
    </el-dialog>

    <!-- Create dialog -->
    <el-dialog v-model="showCreateDialog" title="发布商品" width="640px" :close-on-click-modal="false" destroy-on-close>
      <el-form :model="createForm" :rules="createRules" ref="createFormRef" label-width="80px">
        <el-form-item label="商品名称" prop="name">
          <el-input v-model="createForm.name" placeholder="请输入商品名称" maxlength="100" show-word-limit />
        </el-form-item>
        <el-form-item label="商品描述" prop="description">
          <el-input v-model="createForm.description" type="textarea" :rows="4" placeholder="请描述商品" maxlength="500" show-word-limit />
        </el-form-item>
        <el-form-item label="价格" prop="price">
          <el-input-number v-model="createForm.price" :min="0" :precision="2" :step="1" style="width: 200px" />
        </el-form-item>
        <el-form-item label="分类" prop="categories">
          <el-select v-model="createForm.categories" placeholder="选择分类（可多选）" clearable multiple style="width: 300px">
            <el-option v-for="cat in categories" :key="cat" :label="cat" :value="cat" />
          </el-select>
        </el-form-item>
        <el-form-item label="配送方式" prop="deliveryTypes">
          <span style="font-size: 14px; color: var(--text-primary);">快递发货</span>
        </el-form-item>
        <el-form-item label="商品图片">
          <el-upload
            :action="uploadAction"
            :headers="uploadHeaders"
            :data="{ module: 'product' }"
            list-type="picture-card"
            :file-list="createFileList"
            :on-success="handleCreateUploadSuccess"
            :on-remove="handleCreateUploadRemove"
            :before-upload="beforeUpload"
            accept="image/*"
            :limit="5"
            :on-exceed="() => ElMessage.warning('最多上传5张图片')"
          >
            <el-icon :size="28"><Plus /></el-icon>
          </el-upload>
          <div class="upload-tip">支持 jpg/png/gif/webp，单张不超过10MB，最多5张</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleCreate" :loading="createLoading">发布</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Search, Picture, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules, UploadFile } from 'element-plus'
import {
  getMyProducts, updateProduct, deleteProduct, toggleProductStatus, createProduct, getCategories
} from '@/api/product'
import type { Product, ProductUpdate, ProductCreate } from '@/types'
import { resolveImageUrl, resolveImageUrls, joinImageUrls, parseRawImages, getProductImageUrl } from '@/utils/image'
import { getCookie } from '@/utils/cookie'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:9000/api'
const uploadAction = `${apiBaseUrl}/upload/image`
const uploadHeaders = computed(() => {
  const token = getCookie('token') || localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
})

const loading = ref(false)
const products = ref<Product[]>([])
const categories = ref<string[]>([])
const selectedCategory = ref('')
const selectedStatus = ref<number | undefined>(undefined)
const searchKeyword = ref('')
const currentPage = ref(1)
const total = ref(0)

const showEditDialog = ref(false)
const editLoading = ref(false)
const editFormRef = ref<FormInstance>()
const editingProductId = ref<string>('')
const editForm = ref<ProductUpdate>({ name: '', description: '', price: 0, stock: 1, categories: [], deliveryTypes: [1], image: '' })
const editImageUrls = ref<string[]>([])
const editFileList = ref<UploadFile[]>([])
const editRules: FormRules = {
  name: [{ required: true, message: '请输入商品名称', trigger: 'blur' }],
  price: [{ required: true, message: '请输入价格', trigger: 'blur' }]
}

const showCreateDialog = ref(false)
const createLoading = ref(false)
const createFormRef = ref<FormInstance>()
const createForm = ref<ProductCreate>({ name: '', description: '', price: 0, stock: 1, categories: [], deliveryTypes: [1], image: '' })
const createImageUrls = ref<string[]>([])
const createFileList = ref<UploadFile[]>([])
const createRules: FormRules = {
  name: [{ required: true, message: '请输入商品名称', trigger: 'blur' }],
  price: [{ required: true, message: '请输入价格', trigger: 'blur' }]
}

const beforeUpload = (file: File) => {
  const isImage = file.type.startsWith('image/')
  const isLt10M = file.size / 1024 / 1024 < 10
  if (!isImage) { ElMessage.error('只能上传图片文件！'); return false }
  if (!isLt10M) { ElMessage.error('图片大小不能超过10MB！'); return false }
  return true
}

const handleEditUploadSuccess = (response: any) => {
  if (response.code === 200 && response.data?.url) {
    editImageUrls.value.push(response.data.url)
    editForm.value.image = joinImageUrls(editImageUrls.value)
  } else {
    ElMessage.error(response.message || '上传失败')
  }
}

const handleEditUploadRemove = (file: UploadFile) => {
  const url = file.response?.data?.url || file.url
  if (url) {
    editImageUrls.value = editImageUrls.value.filter(u => u !== url)
    editForm.value.image = joinImageUrls(editImageUrls.value)
  }
}

const handleCreateUploadSuccess = (response: any) => {
  if (response.code === 200 && response.data?.url) {
    createImageUrls.value.push(response.data.url)
    createForm.value.image = joinImageUrls(createImageUrls.value)
  } else {
    ElMessage.error(response.message || '上传失败')
  }
}

const handleCreateUploadRemove = (file: UploadFile) => {
  const url = file.response?.data?.url || file.url
  if (url) {
    createImageUrls.value = createImageUrls.value.filter(u => u !== url)
    createForm.value.image = joinImageUrls(createImageUrls.value)
  }
}

const loadProducts = async () => {
  loading.value = true
  try {
    const res = await getMyProducts({
      category: selectedCategory.value || undefined,
      keyword: searchKeyword.value || undefined,
      status: selectedStatus.value,
      pageNum: currentPage.value,
      pageSize: 20
    })
    products.value = res.records || []
    total.value = res.total || 0
  } catch (error) {
    console.error('加载商品列表失败:', error)
    ElMessage.error('加载商品列表失败')
  } finally {
    loading.value = false
  }
}

const loadCategories = async () => {
  try { categories.value = await getCategories() } catch {}
}

const handleSearch = () => { currentPage.value = 1; loadProducts() }
const handlePageChange = (page: number) => { currentPage.value = page; loadProducts() }

const formatTime = (time?: string) => {
  if (!time) return '-'
  return time.replace('T', ' ').substring(0, 19)
}

const handleEdit = (product: Product) => {
  editingProductId.value = product.id
  editForm.value = {
    name: product.name,
    description: product.description || '',
    price: product.price,
    stock: product.stock,
    categories: product.categories || [],
    deliveryTypes: product.deliveryTypes || [1],
    image: product.image || '',
  }
  editImageUrls.value = parseRawImages(product.image)
  editFileList.value = editImageUrls.value.map((url, index) => ({ name: `image-${index}`, url: resolveImageUrl(url) }))
  showEditDialog.value = true
}

const handleSaveEdit = async () => {
  if (!editFormRef.value) return
  await editFormRef.value.validate(async (valid) => {
    if (!valid) return
    editLoading.value = true
    try {
      await updateProduct(editingProductId.value, editForm.value)
      ElMessage.success('修改成功')
      showEditDialog.value = false
      loadProducts()
    } catch (error) {
      ElMessage.error('修改失败')
    } finally {
      editLoading.value = false
    }
  })
}

const openCreateDialog = () => {
  createForm.value = { name: '', description: '', price: 0, stock: 1, categories: [], deliveryTypes: [1], image: '' }
  createImageUrls.value = []
  createFileList.value = []
  showCreateDialog.value = true
}

const handleToggleStatus = async (product: Product) => {
  const newStatus = product.status === 1 ? 0 : 1
  const action = newStatus === 1 ? '上架' : '下架'
  try {
    await ElMessageBox.confirm(`确定要${action}「${product.name}」吗？`, `${action}确认`, { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
    await toggleProductStatus(product.id, newStatus)
    ElMessage.success(`${action}成功`)
    loadProducts()
  } catch (error: any) {
    if (error !== 'cancel') ElMessage.error(`${action}失败`)
  }
}

const handleDelete = async (product: Product) => {
  try {
    await ElMessageBox.confirm(`确定要删除「${product.name}」吗？删除后不可恢复。`, '删除确认', {
      confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'error', confirmButtonClass: 'el-button--danger'
    })
    await deleteProduct(product.id)
    ElMessage.success('删除成功')
    loadProducts()
  } catch (error: any) {
    if (error !== 'cancel') ElMessage.error('删除失败')
  }
}

const handleCreate = async () => {
  if (!createFormRef.value) return
  await createFormRef.value.validate(async (valid) => {
    if (!valid) return
    createLoading.value = true
    try {
      const data: ProductCreate = {
        name: createForm.value.name,
        description: createForm.value.description,
        price: createForm.value.price,
        stock: 1,
        categories: createForm.value.categories,
        deliveryTypes: createForm.value.deliveryTypes,
        image: createForm.value.image
      }
      await createProduct(data)
      ElMessage.success('发布成功')
      showCreateDialog.value = false
      loadProducts()
    } catch (error) {
      ElMessage.error('发布失败')
    } finally {
      createLoading.value = false
    }
  })
}

onMounted(() => {
  loadCategories()
  loadProducts()
})
</script>

<style scoped lang="scss">
.my-products-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 12px;

  .header-left {
    display: flex;
    align-items: center;
    gap: 10px;

    h2 {
      margin: 0;
      font-size: 20px;
      font-weight: 700;
      color: var(--text-primary);
    }

    .count-badge {
      font-size: 12px;
      padding: 2px 10px;
      border-radius: var(--radius-full);
      background: var(--primary-bg);
      color: var(--primary);
      font-weight: 600;
    }
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;

    :deep(.el-input__wrapper) {
      border-radius: var(--radius-sm);
    }

    .create-btn {
      border-radius: var(--radius-sm);
      font-weight: 600;
      background: var(--accent);
      border: none;

      &:hover {
        background: var(--accent-dark);
      }
    }
  }
}

.product-table-wrapper {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  padding: 16px;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-light);
  min-height: 300px;

  :deep(.el-table) {
    border-radius: var(--radius-sm);
  }
}

.product-cell {
  display: flex;
  align-items: center;
  gap: 12px;

  .product-thumb {
    width: 56px;
    height: 56px;
    border-radius: var(--radius-sm);
    overflow: hidden;
    flex-shrink: 0;

    .thumb-placeholder {
      width: 100%;
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      background: var(--bg-deep);
    }
  }

  .product-cell-info {
    display: flex;
    flex-direction: column;
    gap: 4px;

    .product-cell-name {
      font-size: 14px;
      font-weight: 600;
      color: var(--text-primary);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      max-width: 180px;
    }

    .product-cell-tags {
      display: flex;
      gap: 4px;

      .mini-tag {
        font-size: 11px;
        padding: 1px 6px;
        border-radius: 4px;
        background: var(--primary-bg);
        color: var(--primary);
      }
    }
  }
}

.price-text {
  color: var(--price-color);
  font-weight: 600;
}

.status-dot {
  font-size: 12px;
  padding: 2px 10px;
  border-radius: var(--radius-full);
  font-weight: 500;

  &.active {
    background: var(--accent-glow);
    color: var(--success);
  }

  &.inactive {
    background: var(--bg-page);
    color: var(--text-muted);
  }
}

.upload-tip {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
}

.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: 24px;
  padding-bottom: 20px;
}
</style>
