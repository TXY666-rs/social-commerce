<template>
  <div class="knowledge-container">
    <div class="page-header">
      <div>
        <h2>知识库管理</h2>
        <p>上传和管理知识库文件</p>
      </div>
    </div>

    <!-- Upload section -->
    <div class="upload-section">
      <el-upload
        ref="uploadRef"
        :auto-upload="false"
        :on-change="handleFileChange"
        :on-remove="handleFileRemove"
        :file-list="fileList"
        multiple
        class="upload-area"
        drag
      >
        <el-icon :size="40" class="upload-icon"><UploadFilled /></el-icon>
        <div class="el-upload__text">将文件拖到此处，或<em>点击上传</em></div>
        <template #tip>
          <div class="upload-tip">支持上传文档、图片等文件</div>
        </template>
      </el-upload>

      <div class="upload-actions">
        <div class="type-select">
          <span class="type-label">文件权限：</span>
          <el-radio-group v-model="uploadType">
            <el-radio value="private">管理员可读</el-radio>
            <el-radio value="public">公共读</el-radio>
          </el-radio-group>
        </div>
        <el-button
          type="primary"
          :loading="uploading"
          :disabled="fileList.length === 0"
          @click="handleUpload"
          class="upload-btn"
        >
          <el-icon><Upload /></el-icon>
          上传文件
        </el-button>
      </div>
    </div>

    <!-- File list -->
    <div class="file-section">
      <div class="section-header">
        <h3>已上传文件</h3>
        <el-button :icon="Refresh" circle @click="loadFileList" :loading="loading" />
      </div>

      <div v-loading="loading" class="file-table-wrapper">
        <el-empty v-if="!loading && files.length === 0" description="暂无文件" />

        <el-table v-else :data="files" :header-cell-style="{ background: 'var(--bg-deep)', color: 'var(--text-caption)', fontWeight: '600' }">
          <el-table-column type="index" label="#" width="60" />
          <el-table-column prop="fileName" label="文件名" min-width="300" show-overflow-tooltip />
          <el-table-column label="上传时间" width="180" align="center">
            <template #default="{ row }">{{ formatTime(row.createTime) }}</template>
          </el-table-column>
          <el-table-column label="更新时间" width="180" align="center">
            <template #default="{ row }">{{ formatTime(row.updateTime) }}</template>
          </el-table-column>
        </el-table>
      </div>

      <div class="pagination-container" v-if="files.length > 0">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="files.length"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { UploadFilled, Upload, Refresh } from '@element-plus/icons-vue'
import { ElMessage, type UploadFile } from 'element-plus'
import { uploadFiles, getFileList } from '@/api/upload'
import type { AliOssFileVO } from '@/types'

const uploadRef = ref()
const fileList = ref<UploadFile[]>([])
const uploadType = ref<'private' | 'public'>('private')
const uploading = ref(false)

const loading = ref(false)
const files = ref<AliOssFileVO[]>([])
const currentPage = ref(1)
const pageSize = ref(10)

const handleFileChange = (_file: UploadFile, newFileList: UploadFile[]) => {
  fileList.value = newFileList
}

const handleFileRemove = (_file: UploadFile, newFileList: UploadFile[]) => {
  fileList.value = newFileList
}

const handleUpload = async () => {
  if (fileList.value.length === 0) {
    ElMessage.warning('请先选择文件')
    return
  }
  uploading.value = true
  try {
    const rawFiles = fileList.value.map(f => f.raw).filter((f): f is File => !!f)
    if (rawFiles.length === 0) {
      ElMessage.warning('没有可上传的文件')
      return
    }
    await uploadFiles(rawFiles, uploadType.value)
    ElMessage.success('上传成功')
    fileList.value = []
    uploadRef.value?.clearFiles()
    loadFileList()
  } catch (error: any) {
    ElMessage.error(error.message || '上传失败')
  } finally {
    uploading.value = false
  }
}

const loadFileList = async () => {
  loading.value = true
  try {
    const res = await getFileList({ pageNum: currentPage.value, pageSize: pageSize.value })
    files.value = res.records || []
  } catch (error) {
    console.error('加载文件列表失败:', error)
    ElMessage.error('加载文件列表失败')
  } finally {
    loading.value = false
  }
}

const handlePageChange = (page: number) => { currentPage.value = page; loadFileList() }
const handleSizeChange = (size: number) => { pageSize.value = size; currentPage.value = 1; loadFileList() }
const formatTime = (time?: string) => {
  if (!time) return '-'
  return time.replace('T', ' ').substring(0, 19)
}

onMounted(() => loadFileList())
</script>

<style scoped lang="scss">
.knowledge-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

.page-header {
  margin-bottom: 24px;

  h2 {
    font-size: 20px;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0 0 4px;
  }

  p {
    font-size: 14px;
    color: var(--text-muted);
    margin: 0;
  }
}

.upload-section {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  padding: 24px;
  margin-bottom: 20px;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-light);

  .upload-area {
    width: 100%;

    :deep(.el-upload-dragger) {
      width: 100%;
      padding: 36px 20px;
      border-radius: var(--radius-md);
      border-color: var(--border-light);

      &:hover {
        border-color: var(--primary-light);
      }
    }

    .upload-icon {
      color: var(--border-default);
      margin-bottom: 10px;
    }
  }

  .upload-tip {
    font-size: 12px;
    color: var(--text-muted);
    margin-top: 8px;
  }
}

.upload-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border-light);

  .type-select {
    display: flex;
    align-items: center;
    gap: 8px;

    .type-label {
      font-size: 14px;
      color: var(--text-secondary);
      white-space: nowrap;
    }
  }

  .upload-btn {
    border-radius: var(--radius-sm);
    font-weight: 600;
    background: var(--accent);
    border: none;

    &:hover {
      background: var(--accent-dark);
    }
  }
}

.file-section {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  padding: 24px;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-light);

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;

    h3 {
      font-size: 16px;
      font-weight: 600;
      color: var(--text-primary);
      margin: 0;
    }
  }
}

.file-table-wrapper {
  min-height: 200px;
}

.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: 20px;
  padding-bottom: 8px;
}
</style>
