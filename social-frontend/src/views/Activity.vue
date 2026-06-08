<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

interface CouponVO {
  id: number
  name: string
  type: number
  typeName: string
  thresholdAmount: number | null
  discountAmount: number | null
  discountRate: number | null
  maxDiscount: number | null
  totalStock: number
  claimedCount: number
  remainStock: number
  perUserLimit: number
  startTime: string
  endTime: string
  status: number
  statusName: string
  description: string | null
  claimedByMe: boolean
  myClaimedCount: number
}

const coupons = ref<CouponVO[]>([])
const loading = ref(false)

const fetchCoupons = async () => {
  loading.value = true
  try {
    const res = await request.get('/coupon/available')
    coupons.value = Array.isArray(res) ? res : (res.data || [])
  } catch (err) {
    console.error('获取优惠券失败', err)
  } finally {
    loading.value = false
  }
}

const handleClaim = async (coupon: CouponVO) => {
  try {
    await request.post(`/coupon/claim/${coupon.id}`)
    ElMessage.success('领取成功！')
    fetchCoupons()
  } catch (err: any) {
    const msg = err?.response?.data?.message || err?.message || '领取失败'
    ElMessage.error(msg)
  }
}

const formatCouponDesc = (c: CouponVO): string => {
  switch (c.type) {
    case 1: return `满${c.thresholdAmount || 0}减${c.discountAmount || 0}`
    case 2: return `${(c.discountRate || 1) * 10}折` + (c.maxDiscount ? ` 上限减${c.maxDiscount}` : '')
    case 3: return `立减${c.discountAmount || 0}元`
    default: return ''
  }
}

const isExpiredOrNotStarted = (c: CouponVO): boolean => {
  const now = new Date()
  const end = new Date(c.endTime)
  const start = new Date(c.startTime)
  return now > end || now < start
}

onMounted(() => {
  fetchCoupons()
})
</script>

<template>
  <div class="activity-page">
    <div class="page-header">
      <h2>活动中心</h2>
      <p>限时优惠，先到先得</p>
    </div>

    <div v-if="loading" class="loading-wrap">
      <el-skeleton :rows="3" animated />
    </div>

    <el-empty v-else-if="coupons.length === 0" description="暂无可用优惠活动" />

    <div v-else class="coupon-list">
      <div
        v-for="coupon in coupons"
        :key="coupon.id"
        class="coupon-card"
        :class="{ expired: isExpiredOrNotStarted(coupon), disabled: coupon.status !== 1 }"
      >
        <div class="coupon-left">
          <template v-if="coupon.type === 1 || coupon.type === 3">
            <span class="amount-symbol">¥</span>
            <span class="amount-value">{{ coupon.discountAmount || 0 }}</span>
          </template>
          <template v-if="coupon.type === 2">
            <span class="discount-rate">{{ coupon.discountRate ? (coupon.discountRate * 10).toFixed(0) : '' }}折</span>
          </template>
          <div class="condition">{{ coupon.type === 3 ? '全场通用' : `满${coupon.thresholdAmount}可用` }}</div>
        </div>

        <div class="coupon-info">
          <h4>{{ coupon.name }}</h4>
          <p class="desc" v-if="coupon.description">{{ coupon.description }}</p>
          <p class="time">{{ coupon.startTime?.replace('T', ' ')?.substring(0, 10) }} ~ {{ coupon.endTime?.replace('T', ' ')?.substring(0, 10) }}</p>
          <div class="stock-bar">
            <div class="stock-progress" :style="{ width: `${((coupon.totalStock - coupon.remainStock) / coupon.totalStock) * 100}%` }"></div>
          </div>
          <p class="stock-text">剩余 {{ coupon.remainStock ?? (coupon.totalStock - coupon.claimedCount) }} / {{ coupon.totalStock }}</p>
        </div>

        <div class="coupon-action">
          <template v-if="coupon.claimedByMe">
            <span class="claimed-tag">已领取</span>
            <span v-if="coupon.myClaimedCount > 0" class="claimed-count">{{ coupon.myClaimedCount }}张</span>
          </template>
          <template v-else-if="isExpiredOrNotStarted(coupon)">
            <el-button disabled size="small" round>已结束</el-button>
          </template>
          <template v-else-if="coupon.remainStock <= 0">
            <el-button disabled size="small" round>已抢光</el-button>
          </template>
          <template v-else>
            <el-button type="danger" size="small" round @click="handleClaim(coupon)" class="claim-btn">立即领取</el-button>
          </template>
        </div>

        <div class="coupon-hole hole-top"></div>
        <div class="coupon-hole hole-bottom"></div>
      </div>
    </div>

    <div class="my-coupons-link">
      <router-link to="/my-coupons">
        <el-button plain type="primary" round>查看我的优惠券</el-button>
      </router-link>
    </div>
  </div>
</template>

<style scoped lang="scss">
.activity-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 24px;
}

.page-header {
  text-align: center;
  margin-bottom: 32px;

  h2 {
    font-size: 24px;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0 0 6px;
  }

  p {
    color: var(--text-muted);
    margin: 0;
    font-size: 14px;
  }
}

.loading-wrap { padding: 20px; }

.coupon-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.coupon-card {
  display: flex;
  background: linear-gradient(135deg, var(--ember), var(--gold));
  border-radius: var(--radius-lg);
  padding: 20px;
  position: relative;
  overflow: hidden;
  min-height: 120px;
  transition: transform 0.2s, box-shadow 0.2s;

  &:hover:not(.expired):not(.disabled) {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(192, 85, 58, 0.25);
  }

  &.expired {
    background: linear-gradient(135deg, var(--border-light), var(--border));
    opacity: 0.7;
  }

  &.disabled {
    background: linear-gradient(135deg, var(--border-light), var(--border));
  }
}

.coupon-left {
  width: 100px;
  text-align: center;
  border-right: 2px dashed rgba(255, 255, 255, 0.4);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  flex-shrink: 0;
  padding-right: 16px;

  .amount-symbol {
    font-size: 16px;
    color: rgba(255, 255, 255, 0.9);
    font-weight: bold;
  }

  .amount-value {
    font-size: 36px;
    color: #fff;
    font-weight: 800;
    line-height: 1;
  }

  .discount-rate {
    font-size: 30px;
    color: #fff;
    font-weight: 800;
  }

  .condition {
    font-size: 11px;
    color: rgba(255, 255, 255, 0.8);
    margin-top: 4px;
  }
}

.coupon-info {
  flex: 1;
  padding: 0 20px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  color: #fff;

  h4 {
    font-size: 16px;
    font-weight: 600;
    margin: 0 0 4px;
  }

  .desc {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.85);
    margin: 0 0 6px;
  }

  .time {
    font-size: 11px;
    color: rgba(255, 255, 255, 0.65);
    margin: 0 0 6px;
  }

  .stock-bar {
    height: 4px;
    background: rgba(255, 255, 255, 0.25);
    border-radius: 2px;
    overflow: hidden;
    margin-bottom: 4px;

    .stock-progress {
      height: 100%;
      background: rgba(255, 255, 255, 0.8);
      border-radius: 2px;
      transition: width 0.3s;
    }
  }

  .stock-text {
    font-size: 11px;
    color: rgba(255, 255, 255, 0.65);
    margin: 0;
  }
}

.expired .coupon-info,
.disabled .coupon-info {
  color: #e2e8f0;
}

.expired .coupon-left,
.disabled .coupon-left {
  border-color: rgba(200, 200, 200, 0.3);

  .amount-symbol, .amount-value, .discount-rate, .condition {
    color: #e2e8f0;
  }
}

.coupon-action {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  flex-shrink: 0;
  padding-left: 8px;

  .claimed-tag {
    color: #fff;
    font-weight: 600;
    font-size: 14px;
  }

  .claimed-count {
    font-size: 11px;
    color: rgba(255, 255, 255, 0.7);
    margin-top: 2px;
  }

  .claim-btn {
    background: rgba(255, 255, 255, 0.95);
    color: var(--ember);
    border: none;
    font-weight: 600;

    &:hover {
      background: #fff;
    }
  }
}

.coupon-hole {
  position: absolute;
  left: 108px;
  width: 20px;
  height: 20px;
  background: var(--bg-page);
  border-radius: 50%;
}

.hole-top { top: -10px; }
.hole-bottom { bottom: -10px; }

.my-coupons-link {
  text-align: center;
  margin-top: 32px;
}
</style>
