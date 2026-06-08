<template>
  <div class="product-detail-container">
    <div v-loading="loading" class="detail-content">
      <el-empty v-if="!loading && !product" description="商品不存在" />

      <template v-if="product">
        <!-- Back button -->
        <div class="back-row">
          <el-button @click="router.back()" :icon="ArrowLeft" text class="back-btn">返回商城</el-button>
        </div>

        <div class="detail-main">
          <!-- Product image -->
          <div class="detail-image">
            <el-image
              :src="getProductImageUrl(product) || defaultImage"
              fit="contain"
              class="main-image"
            >
              <template #error>
                <div class="image-placeholder">
                  <el-icon :size="56" color="#d8cfc5"><Picture /></el-icon>
                </div>
              </template>
            </el-image>
          </div>

          <!-- Product info -->
          <div class="detail-info">
            <h1 class="product-name">{{ product.name }}</h1>

            <div class="info-row">
              <div class="tags" v-if="product.categories?.length">
                <span v-for="cat in product.categories" :key="cat" class="tag">{{ cat }}</span>
              </div>
              <span class="view-count">{{ product.viewCount }} 次浏览</span>
            </div>

            <div class="price-section">
              <span class="price-label">价格</span>
              <span class="price-value">
                <em class="price-symbol">¥</em>{{ product.price?.toFixed(2) }}
              </span>
            </div>

            <div class="info-grid">
              <div class="info-item" v-if="product.sellerNickname">
                <span class="label">卖家</span>
                <span class="value">{{ product.sellerNickname }}</span>
              </div>
              <div class="info-item">
                <span class="label">库存</span>
                <span class="value" :class="{ 'out-of-stock': product.stock === 0 }">
                  {{ product.stock > 0 ? `${product.stock} 件` : '已售罄' }}
                </span>
              </div>
            </div>

            <!-- Buy section -->
            <div class="buy-section" v-if="product.stock > 0">
              <div class="buy-row">
                <span class="label">数量</span>
                <el-input-number
                  v-model="quantity"
                  :min="1"
                  :max="product.stock"
                  size="default"
                />
              </div>

              <div class="buy-row">
                <span class="label">配送</span>
                <span style="font-size: 14px; color: var(--text-primary);">快递发货</span>
              </div>

              <div class="total-row">
                <span class="total-label">合计</span>
                <span class="total-price">
                  <em class="price-symbol">¥</em>{{ totalPrice }}
                </span>
              </div>

              <el-button type="primary" size="large" class="buy-btn" @click="showOrderDialog = true">
                立即购买
              </el-button>
            </div>
          </div>
        </div>

        <!-- Description -->
        <div class="detail-description">
          <h2>商品详情</h2>
          <div class="description-content">
            {{ product.description || '暂无商品描述' }}
          </div>
        </div>
      </template>
    </div>

    <!-- Order dialog -->
    <el-dialog v-model="showOrderDialog" title="确认订单" width="500px" :close-on-click-modal="false" class="order-dialog">
      <el-form :model="orderForm" :rules="orderRules" ref="orderFormRef" label-width="80px">
        <el-form-item label="商品">
          <span>{{ product?.name }}</span>
        </el-form-item>
        <el-form-item label="单价">
          <span class="price-text">¥{{ product?.price?.toFixed(2) }}</span>
        </el-form-item>
        <el-form-item label="数量">
          <span>{{ quantity }} 件</span>
        </el-form-item>
        <el-form-item label="配送方式">
          <span>快递发货</span>
        </el-form-item>
        <el-form-item label="总计">
          <span class="price-text total-text">¥{{ totalPrice }}</span>
        </el-form-item>
        <el-divider />
        <!-- 地址簿选择 -->
        <el-form-item v-if="addressList.length > 0" label="选择地址">
          <el-select v-model="selectedAddressId" placeholder="选择已保存的收货地址" clearable style="width:100%"
            @change="onAddressSelect">
            <el-option v-for="addr in addressList" :key="addr.id" :label="addrLabel(addr)" :value="addr.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="收货人" prop="receiverName">
          <el-input v-model="orderForm.receiverName" placeholder="请输入收货人姓名" />
        </el-form-item>
        <el-form-item label="联系电话" prop="receiverPhone">
          <el-input v-model="orderForm.receiverPhone" placeholder="请输入联系电话" />
        </el-form-item>
        <el-form-item label="收货地址" prop="receiverAddress">
          <el-input v-model="orderForm.receiverAddress" type="textarea" :rows="2" placeholder="请输入收货地址" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="orderForm.remark" placeholder="选填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showOrderDialog = false">取消</el-button>
        <el-button type="primary" @click="handlePlaceOrder" :loading="orderLoading">
          确认下单
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Picture } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { getProductDetail, createOrder } from '@/api/product'
import { getAddressList } from '@/api/address'
import type { Product, OrderCreate, Address } from '@/types'
import { getProductImageUrl } from '@/utils/image'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const orderLoading = ref(false)
const product = ref<Product | null>(null)
const quantity = ref(1)
const showOrderDialog = ref(false)
const orderFormRef = ref<FormInstance>()
const defaultImage = 'https://via.placeholder.com/400x400?text=No+Image'

// 地址簿
const addressList = ref<Address[]>([])
const selectedAddressId = ref<number>()

const addrLabel = (addr: Address) => {
  const detail = addr.detailAddress || ''
  const parts = [addr.receiverName, addr.receiverPhone, detail].filter(Boolean)
  return parts.join(' · ')
}

const loadAddresses = async () => {
  try {
    addressList.value = await getAddressList()
  } catch { /* 地址加载失败不影响下单 */ }
}

const onAddressSelect = (id: number | undefined) => {
  if (!id) {
    orderForm.value = { receiverName: '', receiverPhone: '', receiverAddress: '', remark: '' }
    return
  }
  const addr = addressList.value.find(a => a.id === id)
  if (addr) {
    orderForm.value.receiverName = addr.receiverName
    orderForm.value.receiverPhone = addr.receiverPhone
    orderForm.value.receiverAddress = addr.detailAddress
    // 不覆盖备注
  }
}

const orderForm = ref({
  receiverName: '',
  receiverPhone: '',
  receiverAddress: '',
  remark: ''
})

const orderRules: FormRules = {
  receiverName: [{ required: true, message: '请输入收货人姓名', trigger: 'blur' }],
  receiverPhone: [{ required: true, message: '请输入联系电话', trigger: 'blur' }],
  receiverAddress: [{ required: true, message: '请输入收货地址', trigger: 'blur' }]
}

const totalPrice = computed(() => {
  if (!product.value) return '0.00'
  return (product.value.price * quantity.value).toFixed(2)
})

const loadProduct = async () => {
  loading.value = true
  try {
    const id = route.params.id as string
    product.value = await getProductDetail(id)
  } catch (error) {
    console.error('加载商品详情失败:', error)
    ElMessage.error('加载商品详情失败')
  } finally {
    loading.value = false
  }
}

// 打开下单弹窗时加载地址簿
watch(showOrderDialog, (open) => {
  if (open) {
    selectedAddressId.value = undefined
    loadAddresses()
  }
})

const handlePlaceOrder = async () => {
  if (!orderFormRef.value) return
  await orderFormRef.value.validate(async (valid) => {
    if (!valid) return
    orderLoading.value = true
    try {
      const data: OrderCreate = {
        productId: product.value!.id,
        quantity: quantity.value,
        receiverName: orderForm.value.receiverName,
        receiverPhone: orderForm.value.receiverPhone,
        receiverAddress: orderForm.value.receiverAddress,
        remark: orderForm.value.remark || undefined
      }
      await createOrder(data)
      ElMessage.success('下单成功！')
      showOrderDialog.value = false
      router.push('/orders')
    } catch (error) {
      console.error('下单失败:', error)
    } finally {
      orderLoading.value = false
    }
  })
}

onMounted(() => {
  loadProduct()
})
</script>

<style scoped lang="scss">
.product-detail-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 32px 48px;
}

.back-row {
  margin-bottom: 20px;

  .back-btn {
    color: var(--text-secondary);
    font-weight: 500;

    &:hover {
      color: var(--primary);
    }
  }
}

.detail-main {
  display: flex;
  gap: 44px;
  background: var(--bg-card);
  border-radius: var(--radius-xl);
  padding: 32px;
  box-shadow: var(--shadow-md);
  border: 1px solid var(--border-light);

  @media (max-width: 768px) {
    flex-direction: column;
    gap: 24px;
  }
}

.detail-image {
  width: 440px;
  flex-shrink: 0;

  @media (max-width: 768px) {
    width: 100%;
  }

  .main-image {
    width: 100%;
    height: 420px;
    border-radius: var(--radius-lg);
    overflow: hidden;
    background: var(--bg-deep);
  }

  .image-placeholder {
    width: 100%;
    height: 420px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg-deep);
    border-radius: var(--radius-lg);
  }
}

.detail-info {
  flex: 1;

  .product-name {
    font-size: 24px;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0 0 16px 0;
    line-height: 1.35;
    letter-spacing: -0.3px;
  }

  .info-row {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 24px;

    .tags {
      display: flex;
      gap: 6px;

      .tag {
        font-size: 12px;
        padding: 3px 12px;
        border-radius: var(--radius-full);
        background: var(--primary-bg);
        color: var(--primary);
        font-weight: 500;
      }
    }

    .view-count {
      font-size: 13px;
      color: var(--text-muted);
    }
  }

  .price-section {
    background: var(--price-bg);
    padding: 20px 24px;
    border-radius: var(--radius-lg);
    margin-bottom: 24px;
    display: flex;
    align-items: baseline;
    gap: 12px;

    .price-label {
      font-size: 14px;
      color: var(--text-muted);
    }

    .price-value {
      font-size: 32px;
      font-weight: 700;
      color: var(--price-color);
      letter-spacing: -0.5px;

      .price-symbol {
        font-size: 17px;
        font-style: normal;
      }
    }
  }

  .info-grid {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-bottom: 24px;
  }

  .info-item {
    display: flex;
    align-items: center;

    .label {
      width: 56px;
      font-size: 14px;
      color: var(--text-muted);
    }

    .value {
      font-size: 14px;
      color: var(--text-primary);

      &.out-of-stock {
        color: var(--danger);
        font-weight: 600;
      }
    }
  }

  .buy-section {
    padding-top: 24px;
    border-top: 1px solid var(--border-light);

    .buy-row {
      display: flex;
      align-items: center;
      margin-bottom: 16px;

      .label {
        width: 56px;
        font-size: 14px;
        color: var(--text-muted);
      }
    }

    .total-row {
      display: flex;
      align-items: baseline;
      margin-bottom: 22px;

      .total-label {
        width: 56px;
        font-size: 14px;
        color: var(--text-muted);
      }

      .total-price {
        font-size: 28px;
        font-weight: 700;
        color: var(--price-color);
        letter-spacing: -0.5px;

        .price-symbol {
          font-size: 15px;
          font-style: normal;
        }
      }
    }

    .buy-btn {
      width: 100%;
      height: 50px;
      border-radius: var(--radius-md);
      font-size: 16px;
      font-weight: 600;
      background: var(--accent);
      border: none;
      letter-spacing: 0.5px;

      &:hover {
        background: var(--accent-dark);
      }
    }
  }
}

.detail-description {
  background: var(--bg-card);
  border-radius: var(--radius-xl);
  padding: 32px;
  margin-top: 24px;
  box-shadow: var(--shadow-md);
  border: 1px solid var(--border-light);

  h2 {
    font-size: 17px;
    font-weight: 600;
    margin: 0 0 16px 0;
    color: var(--text-primary);
  }

  .description-content {
    font-size: 14px;
    line-height: 1.85;
    color: var(--text-secondary);
    white-space: pre-wrap;
  }
}

.price-text {
  color: var(--price-color);
  font-weight: 600;

  &.total-text {
    font-size: 20px;
  }
}
</style>
