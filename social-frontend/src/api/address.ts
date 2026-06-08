import request from '@/utils/request'
import type { Address } from '@/types'

/** 获取用户地址列表 */
export const getAddressList = (): Promise<Address[]> => {
  return request.get('/address/list')
}

/** 创建地址 */
export const createAddress = (data: Address): Promise<Address> => {
  return request.post('/address/create', data)
}

/** 更新地址 */
export const updateAddress = (id: number, data: Address): Promise<boolean> => {
  return request.put(`/address/${id}`, data)
}

/** 删除地址 */
export const deleteAddress = (id: number): Promise<boolean> => {
  return request.delete(`/address/${id}`)
}

/** 设置默认地址 */
export const setDefaultAddress = (id: number): Promise<boolean> => {
  return request.put(`/address/default/${id}`)
}
