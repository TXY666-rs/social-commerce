import request from '@/utils/request'
import type { AliOssFileVO, FileListResult } from '@/types'

// 上传文件（知识库）
export const uploadFiles = (files: File[], type: string): Promise<any> => {
  const formData = new FormData()
  files.forEach(file => formData.append('files', file))
  formData.append('type', type)
  return request.post('/upload/files', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

// 获取文件列表（知识库）
export const getFileList = (params: {
  pageNum?: number
  pageSize?: number
}): Promise<FileListResult> => {
  return request.get('/upload/list', { params })
}
