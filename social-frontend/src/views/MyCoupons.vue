<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

interface UserCouponVO {
  id: number
  userId: number
  couponId: number
  couponName: string
  type: number
  typeName: string
  thresholdAmount: number | null
  discountAmount: number | null
  discountRate: number | null
  maxDiscount: number | null
  startTime: string
  endTime: string
  status: number
  statusName: string
  claimTime: string
  useTime: string | null
}

const coupons = ref<UserCouponVO[]>([])
const loading = ref(false)
const activeTab = ref(0)

const fetchMyCoupons = async () => {
  loading.value = true
  try {
    let status = undefined
    if (activeTab.value === 1) status = 0
    if (activeTab.value === 2) status = 1
    const res = await request.get('/coupon/my', { params: { status } })
    coupons.value = Array.isArray(res) ? res : (res.data || [])
  } catch (err) {
    console.error('获取优惠券失败', err)
  } finally {
    loading.value = false
  }
}

const handleUse = async (coupon: UserCouponVO) => {
  try {
    await request.post(`/coupon/use/${coupon.id}`)
    ElMessage.success('使用成功')
    fetchMyCoupons()
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.message || err?.message || '使用失败')
  }
}

const onTabChange = () => fetchMyCoupons()

const formatDiscount = (c: UserCouponVO): string => {
  if (c.type === 1) return `满${c.thresholdAmount}减${c.discountAmount}`
  if (c.type === 2) return `${c.discountRate ? (c.discountRate * 10).toFixed(0) : ''}折`
  if (c.type === 3) return `立减${c.discountAmount}元`
  return ''
}

onMounted(() => fetchMyCoupons())
</script>

<template>
  <div class="my-coupons-page">
    <div class="page-header">
      <h2>我的优惠券</h2>
    </div>

    <div class="tabs">
      <el-radio-group v-model="activeTab" @change="onTabChange">
        <el-radio-button :value="0">全部 ({{ coupons.length }})</el-radio-button>
        <el-radio-button :value="1">未使用</el-radio-button>
        <el-radio-button :value="2">已使用</el-radio-button>
      </el-radio-group>
    </div>

    <div v-if="loading" class="loading-wrap"><el-skeleton :rows="3" animated /></div>

    <el-empty v-else-if="coupons.length === 0" description="暂无优惠券，去活动页领取吧~">
      <router-link to="/activity">
        <el-button type="primary" round>去领券</el-button>
      </router-link>
    </el-empty>

    <div v-else class="coupon-list">
      <div v-for="c in coupons" :key="c.id" class="coupon-item" :class="{ used: c.status !== 0 }">
        <div class="item-left">
          <div class="coupon-amount">
            <template v-if="c.type === 1 || c.type === 3">
              <span class="symbol">¥</span><span class="value">{{ c.discountAmount || 0 }}</span>
            </template>
            <template v-if="c.type === 2">
              <span class="value">{{ c.discountRate ? (c.discountRate * 10).toFixed(0) : '' }}</span><span class="symbol">折</span>
            </template>
          </div>
          <span class="discount-desc">{{ formatDiscount(c) }}</span>
        </div>
        <div class="item-center">
          <span class="name">{{ c.couponName }}</span>
          <span class="time">有效期至 {{ c.endTime?.replace('T', ' ')?.substring(0, 10) }}</span>
        </div>
        <div class="item-right">
          <span class="status-tag" :class="'status-' + c.status">{{ c.statusName }}</span>
          <el-button v-if="c.status === 0" type="danger" size="small" round @click="handleUse(c)">使用</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.my-coupons-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 24px;
}

.page-header {
  text-align: center;
  margin-bottom: 20px;

  h2 {
    font-size: 22px;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0;
  }
}

.tabs {
  display: flex;
  justify-content: center;
  margin-bottom: 24px;
}

.loading-wrap { padding: 20px; }

.coupon-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.coupon-item {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  padding: 16px 20px;
  display: flex;
  align-items: center;
  gap: 20px;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-light);
  transition: all var(--transition-fast);

  &:hover {
    box-shadow: var(--shadow-md);
  }

  &.used {
    opacity: 0.55;
  }

  .item-left {
    text-align: center;
    min-width: 80px;
    flex-shrink: 0;

    .coupon-amount {
      color: var(--price-color);
      line-height: 1;

      .symbol {
        font-size: 14px;
        font-weight: 600;
      }

      .value {
        font-size: 28px;
        font-weight: 800;
      }
    }

    .discount-desc {
      font-size: 11px;
      color: var(--text-muted);
      margin-top: 4px;
      display: block;
    }
  }

  .item-center {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 4px;
    border-left: 1px solid var(--border-light);
    padding-left: 20px;

    .name {
      font-size: 15px;
      font-weight: 600;
      color: var(--text-primary);
    }

    .time {
      font-size: 12px;
      color: var(--text-muted);
    }
  }

  .item-right {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;

    .status-tag {
      font-size: 12px;
      padding: 2px 10px;
      border-radius: 20px;
      font-weight: 500;

      &.status-0 { background: var(--accent-glow); color: var(--success); }
      &.status-1 { background: var(--bg-page); color: var(--text-muted); }
      &.status-2 { background: var(--bg-page); color: var(--text-muted); }
    }
  }
}
</style>
