<template>
  <div class="orders-container">
    <div class="page-header">
      <h1>我的订单</h1>
    </div>

    <!-- Status filter -->
    <div class="status-tabs">
      <span
        class="status-chip"
        :class="{ active: currentStatus === undefined }"
        @click="setStatus(undefined)"
      >全部</span>
      <span
        v-for="s in statusOptions"
        :key="s.value"
        class="status-chip"
        :class="{ active: currentStatus === s.value }"
        @click="setStatus(s.value)"
      >{{ s.label }}</span>
    </div>

    <!-- Order list -->
    <div v-loading="loading" class="order-list">
      <el-empty v-if="!loading && orders.length === 0" description="暂无订单" />

      <div v-for="order in orders" :key="order.id" class="order-card">
        <div class="order-header">
          <div class="order-meta">
            <span class="order-id">订单号 {{ order.id }}</span>
            <span class="order-time">{{ order.createTime }}</span>
            <span class="delivery-tag express">
              快递发货
            </span>
          </div>
          <span class="status-badge" :class="'status-' + order.status">
            {{ order.statusDesc }}
          </span>
        </div>

        <div class="order-body">
          <div class="product-info" @click="goToProduct(order.productId)">
            <el-image
              :src="resolveImageUrl(order.productImage)"
              fit="cover"
              class="product-image"
            >
              <template #error>
                <div class="image-placeholder">
                  <el-icon :size="20" color="#cbd5e1"><Picture /></el-icon>
                </div>
              </template>
            </el-image>
            <div class="product-detail">
              <h4>{{ order.productName }}</h4>
              <p class="price-line">
                <span class="unit-price">¥{{ order.productPrice?.toFixed(2) }}</span>
                <span class="quantity">x{{ order.quantity }}</span>
              </p>
            </div>
          </div>
          <div class="order-total">
            <span class="total-label">实付</span>
            <span class="total-price">¥{{ order.totalPrice?.toFixed(2) }}</span>
          </div>
        </div>

        <div class="order-footer">
          <div class="order-detail-info">
            <div class="receiver-info" v-if="order.receiverName">
              <el-icon><Location /></el-icon>
              {{ order.receiverName }} {{ order.receiverPhone }}
              <br />
              {{ order.receiverAddress }}
            </div>
            <div class="delivery-info" v-if="order.status >= 2 && order.trackingNumber">
              <el-icon><Van /></el-icon>
              快递单号: {{ order.trackingNumber }}
            </div>
            <div class="delivery-info" v-if="order.status >= 2 && order.deliveryRemark">
              <el-icon><ChatLineSquare /></el-icon>
              备注: {{ order.deliveryRemark }}
            </div>
          </div>
          <div class="order-actions">
            <el-button v-if="order.status === 0" type="primary" size="small" @click="handlePay(order.id)">立即支付</el-button>
            <el-button v-if="order.status === 0 || order.status === 1" size="small" @click="handleCancel(order)">取消订单</el-button>
            <el-button v-if="order.status === 2" type="primary" size="small" @click="handleComplete(order.id)">确认收货</el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <div class="pagination-container" v-if="total > 0">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="loadOrders"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Picture, Location, User, Van, ChatLineSquare } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getMyOrders, payOrder, cancelOrder, completeOrder } from '@/api/product'
import type { Order } from '@/types'
import { resolveImageUrl } from '@/utils/image'

const router = useRouter()

const loading = ref(false)
const orders = ref<Order[]>([])
const currentStatus = ref<number | undefined>(undefined)
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

const statusOptions = [
  { value: 0, label: '待支付' },
  { value: 1, label: '已支付' },
  { value: 2, label: '已发货' },
  { value: 3, label: '已完成' },
  { value: 4, label: '已取消' },
  { value: 5, label: '退款中' },
  { value: 6, label: '已退款' }
]

const setStatus = (val: number | undefined) => {
  currentStatus.value = val
  currentPage.value = 1
  loadOrders()
}

const loadOrders = async () => {
  loading.value = true
  try {
    const params = {
      status: currentStatus.value,
      pageNum: currentPage.value,
      pageSize: pageSize.value
    }
    const res = await getMyOrders(params)
    orders.value = res.records || []
    total.value = res.total || 0
  } catch (error) {
    console.error('加载订单列表失败:', error)
  } finally {
    loading.value = false
  }
}

const handlePay = async (orderId: string) => {
  try {
    await ElMessageBox.confirm('确认支付该订单？', '支付确认', { confirmButtonText: '确认支付', cancelButtonText: '取消', type: 'warning' })
    await payOrder(orderId)
    ElMessage.success('支付成功')
    loadOrders()
  } catch (error: any) {
    if (error !== 'cancel') ElMessage.error('支付失败')
  }
}

const handleCancel = async (order: Order) => {
  try {
    const isPaid = order.status === 1
    const message = isPaid ? '确认取消该订单？卖家尚未发货，取消后支付金额将原路退回' : '确认取消该订单？'
    await ElMessageBox.confirm(message, '取消确认', { confirmButtonText: '确认取消', cancelButtonText: '返回', type: 'warning' })
    await cancelOrder(order.id)
    ElMessage.success(isPaid ? '订单已取消，退款将原路返回' : '订单已取消')
    loadOrders()
  } catch (error: any) {
    if (error !== 'cancel') ElMessage.error('取消失败')
  }
}

const handleComplete = async (orderId: string) => {
  try {
    await ElMessageBox.confirm('确认已收到商品？', '收货确认', { confirmButtonText: '确认收货', cancelButtonText: '取消', type: 'info' })
    await completeOrder(orderId)
    ElMessage.success('已确认收货')
    loadOrders()
  } catch (error: any) {
    if (error !== 'cancel') ElMessage.error('操作失败')
  }
}

const goToProduct = (productId: string) => {
  router.push(`/shop/${productId}`)
}

onMounted(() => {
  loadOrders()
})
</script>

<style scoped lang="scss">
.orders-container {
  max-width: 920px;
  margin: 0 auto;
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;

  h1 {
    font-size: 22px;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0;
  }
}

.status-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 24px;

  .status-chip {
    padding: 6px 18px;
    border-radius: var(--radius-full);
    font-size: 13px;
    font-weight: 500;
    color: var(--text-secondary);
    background: var(--bg-card);
    border: 1px solid var(--border-light);
    cursor: pointer;
    transition: all var(--transition-fast);
    user-select: none;

    &:hover {
      border-color: var(--primary-lighter);
      color: var(--primary);
    }

    &.active {
      background: var(--primary);
      color: var(--text-inverse);
      border-color: transparent;
      box-shadow: 0 2px 10px rgba(109, 76, 125, 0.25);
    }
  }
}

.order-list {
  min-height: 300px;
}

.order-card {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  padding: 20px;
  margin-bottom: 14px;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-light);
  transition: all var(--transition-fast);

  &:hover {
    box-shadow: var(--shadow-md);
  }

  .order-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 14px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border);

    .order-meta {
      display: flex;
      gap: 12px;
      align-items: center;

      .order-id {
        font-size: 14px;
        color: var(--text-primary);
        font-weight: 600;
      }

      .order-time {
        font-size: 13px;
        color: var(--text-muted);
      }

      .delivery-tag {
        font-size: 11px;
        padding: 2px 8px;
        border-radius: 5px;
        font-weight: 500;

        &.express {
          background: var(--primary-bg);
          color: var(--primary);
        }

        &.pickup {
          background: var(--accent-bg);
          color: var(--accent);
        }
      }
    }

    .status-badge {
      font-size: 12px;
      padding: 4px 12px;
      border-radius: 20px;
      font-weight: 600;

      &.status-0 { background: var(--accent-bg); color: var(--accent); }
      &.status-1 { background: var(--primary-bg); color: var(--primary); }
      &.status-2 { background: var(--accent-glow); color: var(--success); }
      &.status-3 { background: var(--accent-glow); color: var(--success); }
      &.status-4 { background: var(--bg-page); color: var(--text-muted); }
    }
  }

  .order-body {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 14px;

    .product-info {
      display: flex;
      gap: 12px;
      cursor: pointer;
      flex: 1;

      .product-image {
        width: 72px;
        height: 72px;
        border-radius: var(--radius-md);
        overflow: hidden;
        flex-shrink: 0;
      }

      .image-placeholder {
        width: 72px;
        height: 72px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: var(--bg-deep);
      }

      .product-detail {
        h4 {
          font-size: 14px;
          color: var(--text-primary);
          margin: 0 0 6px 0;
          font-weight: 500;
        }

        .price-line {
          .unit-price {
            font-size: 14px;
            color: var(--text-secondary);
            margin-right: 8px;
          }
          .quantity {
            font-size: 13px;
            color: var(--text-muted);
          }
        }
      }
    }

    .order-total {
      text-align: right;
      flex-shrink: 0;
      margin-left: 20px;

      .total-label {
        font-size: 13px;
        color: #94a3b8;
        margin-right: 6px;
      }

      .total-price {
        font-size: 18px;
        font-weight: 700;
        color: var(--price-color);
      }
    }
  }

  .order-footer {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    padding-top: 12px;
    border-top: 1px solid var(--border);

    .order-detail-info {
      font-size: 13px;
      color: var(--text-muted);
      line-height: 1.6;

      .receiver-info, .buyer-info {
        display: flex;
        align-items: flex-start;
        gap: 4px;

        .el-icon {
          margin-top: 3px;
          flex-shrink: 0;
        }
      }

      .delivery-info {
        display: flex;
        align-items: center;
        gap: 4px;
        margin-top: 4px;
        color: var(--primary);
      }
    }

    .order-actions {
      display: flex;
      gap: 8px;

      .el-button {
        border-radius: var(--radius-sm);
      }
    }
  }
}

.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: 24px;
  padding-bottom: 20px;
}

.deliver-dialog-content {
  .deliver-tip {
    background: var(--accent-glow);
    color: var(--success);
    padding: 10px 16px;
    border-radius: var(--radius-sm);
    margin: 0 0 20px 0;
    font-size: 14px;
    font-weight: 500;
  }
}
</style>
