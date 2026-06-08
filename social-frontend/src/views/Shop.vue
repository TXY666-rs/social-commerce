<template>
  <div class="shop-page">
    <!-- Hero 区域 -->
    <section class="hero">
      <div class="hero-inner">
        <div class="hero-badge stagger stagger-1">精选好物</div>
        <h1 class="hero-title stagger stagger-2">发现你的下一件心仪之物</h1>
        <p class="hero-subtitle stagger stagger-3">高品质商品，为你精选推荐</p>
        <div class="hero-search stagger stagger-4">
          <div class="search-box">
            <el-icon class="search-icon"><Search /></el-icon>
            <input
              v-model="searchKeyword"
              class="search-input"
              placeholder="搜索商品..."
              @keyup.enter="handleSearch"
            />
            <button class="search-btn" @click="handleSearch">搜索</button>
          </div>
        </div>
      </div>
      <div class="hero-glow"></div>
    </section>

    <!-- 分类栏 -->
    <section class="categories-bar">
      <div class="categories-inner">
        <button
          class="cat-chip"
          :class="{ active: selectedCategory === '' }"
          @click="selectCategory('')"
        >全部</button>
        <button
          v-for="cat in categories"
          :key="cat"
          class="cat-chip"
          :class="{ active: selectedCategory === cat }"
          @click="selectCategory(cat)"
        >{{ cat }}</button>
      </div>
    </section>

    <!-- 商品网格 -->
    <section class="products-section">
      <!-- F3: 骨架屏加载态 -->
      <div v-if="loading" class="products-inner">
        <div class="product-grid">
          <div v-for="n in 8" :key="'skel-' + n" class="product-card product-card-skel">
            <div class="card-image skel-image"></div>
            <div class="card-body">
              <div class="skel-line skel-line-title"></div>
              <div class="skel-line skel-line-tag"></div>
              <div class="skel-line skel-line-price"></div>
            </div>
          </div>
        </div>
      </div>

      <template v-else>
      <div class="products-inner">
        <el-empty v-if="loadError" description="加载失败，请检查网络">
          <el-button type="primary" @click="retryLoad">重新加载</el-button>
        </el-empty>
        <el-empty v-else-if="!loading && products.length === 0" description="暂无商品" />

        <div class="product-grid" v-if="products.length > 0">
          <div
            v-for="(product, index) in products"
            :key="product.id"
            class="product-card"
            :style="{ animationDelay: `${0.05 + index * 0.04}s` }"
            @click="goToDetail(product.id)"
            tabindex="0"
            role="link"
            :aria-label="'查看商品: ' + product.name"
            @keydown.enter="goToDetail(product.id)"
          >
            <!-- 图片区 F2: 使用 LazyImage 替代 el-image -->
            <div class="card-image">
              <LazyImage
                :src="getProductImageUrl(product) || defaultImage"
                :alt="product.name"
                fit="cover"
              />
              <div v-if="product.saleCount > 0" class="card-badge" aria-label="已售数量">
                已售 {{ product.saleCount }}
              </div>
            </div>
            <!-- 信息区 -->
            <div class="card-body">
              <h3 class="card-title">{{ product.name }}</h3>
              <div class="card-tags" v-if="product.categories?.length">
                <span v-for="cat in product.categories" :key="cat" class="tag">{{ cat }}</span>
              </div>
              <div class="card-bottom">
                <div class="card-price">
                  <span class="price-sym">¥</span>
                  <span class="price-val">{{ product.price?.toFixed(2) }}</span>
                </div>
                <span class="card-seller" v-if="product.sellerNickname">{{ product.sellerNickname }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      </template>
    </section>

    <!-- 分页 -->
    <div class="pagination-wrap" v-if="total > 0">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="20"
        :total="total"
        layout="total, prev, pager, next, jumper"
        @current-change="handlePageChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Picture } from '@element-plus/icons-vue'
import { getProductList, getCategories, getProductsByCategory } from '@/api/product'
import type { ProductListItem } from '@/types'
import { getProductImageUrl } from '@/utils/image'
import LazyImage from '@/components/LazyImage.vue'

const router = useRouter()

const loading = ref(false)
const loadError = ref(false)
const products = ref<ProductListItem[]>([])
const categories = ref<string[]>([])
const selectedCategory = ref('')
const searchKeyword = ref('')
const currentPage = ref(1)
const total = ref(0)
const defaultImage = 'https://via.placeholder.com/300x200?text=No+Image'

const loadProducts = async () => {
  loading.value = true
  loadError.value = false
  try {
    let res
    if (selectedCategory.value && !searchKeyword.value) {
      res = await getProductsByCategory(selectedCategory.value)
    } else {
      res = await getProductList({
        category: selectedCategory.value || undefined,
        keyword: searchKeyword.value || undefined,
        status: 1,
        pageNum: currentPage.value,
        pageSize: 20
      })
    }
    if (Array.isArray(res)) {
      products.value = res
      total.value = res.length
    } else {
      products.value = (res as any)?.records || []
      total.value = (res as any)?.total || 0
    }
  } catch (error) {
    console.error('加载商品列表失败:', error)
    loadError.value = true
  } finally {
    loading.value = false
  }
}

const retryLoad = () => { loadProducts(); loadCategories() }

const loadCategories = async () => {
  try { categories.value = await getCategories() } catch (e) { console.error(e) }
}

const selectCategory = (cat: string) => {
  selectedCategory.value = cat
  currentPage.value = 1
  loadProducts()
}

const handleSearch = () => { currentPage.value = 1; loadProducts() }
const handlePageChange = (page: number) => { currentPage.value = page; loadProducts() }
const goToDetail = (id: string) => router.push(`/shop/${id}`)

onMounted(() => { loadCategories(); loadProducts() })
</script>

<style scoped lang="scss">
.shop-page {
  min-height: 100vh;
}

/* ---- Hero ---- */
.hero {
  position: relative;
  padding: 56px 32px 48px;
  background: linear-gradient(180deg, var(--bg-deep) 0%, var(--bg-page) 100%);
  overflow: hidden;
}

.hero-inner {
  max-width: 1320px;
  margin: 0 auto;
  position: relative;
  z-index: 2;
}

.hero-badge {
  display: inline-block;
  font-family: var(--font-display);
  font-size: 12px;
  font-weight: 600;
  color: var(--accent);
  letter-spacing: 3px;
  text-transform: uppercase;
  border: 1px solid rgba(78, 205, 196, 0.25);
  padding: 6px 18px;
  border-radius: var(--r-full);
  margin-bottom: 20px;
}

.hero-title {
  font-family: var(--font-display);
  font-size: clamp(32px, 5vw, 48px);
  font-weight: 800;
  color: var(--text-primary);
  letter-spacing: -1px;
  margin-bottom: 12px;
}

.hero-subtitle {
  font-size: 16px;
  color: var(--text-caption);
  margin-bottom: 32px;
}

.hero-search {
  max-width: 560px;
}

.search-box {
  display: flex;
  align-items: center;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  padding: 5px 5px 5px 20px;
  transition: all var(--t-normal);

  &:focus-within {
    border-color: var(--accent);
    box-shadow: var(--shadow-glow), var(--shadow-md);
  }
}

.search-icon {
  font-size: 18px;
  color: var(--text-ghost);
  margin-right: 12px;
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  border: none;
  outline: none;
  background: none;
  font-family: var(--font-body);
  font-size: 15px;
  color: var(--text-primary);
  padding: 12px 0;

  &::placeholder { color: var(--text-ghost); }
}

.search-btn {
  padding: 12px 32px;
  background: var(--accent);
  color: var(--text-inverse);
  border: none;
  border-radius: var(--r-md);
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--t-fast);
  white-space: nowrap;

  &:hover {
    background: var(--accent-dark);
    box-shadow: 0 4px 16px rgba(78, 205, 196, 0.3);
  }
}

.hero-glow {
  position: absolute;
  top: -100px;
  right: -100px;
  width: 500px;
  height: 500px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(78, 205, 196, 0.06) 0%, transparent 70%);
  pointer-events: none;
}

/* ---- 分类栏 ---- */
.categories-bar {
  padding: 16px 32px;
  background: var(--bg-deep);
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 72px;
  z-index: 100;
}

.categories-inner {
  max-width: 1320px;
  margin: 0 auto;
  display: flex;
  gap: 8px;
  overflow-x: auto;
  scrollbar-width: none;
  &::-webkit-scrollbar { display: none; }
}

.cat-chip {
  padding: 8px 22px;
  border: 1px solid var(--border);
  background: transparent;
  border-radius: var(--r-full);
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 500;
  color: var(--text-caption);
  cursor: pointer;
  white-space: nowrap;
  transition: all var(--t-fast);

  &:hover {
    color: var(--text-primary);
    border-color: var(--text-ghost);
    background: rgba(255, 255, 255, 0.04);
  }

  &.active {
    background: var(--accent);
    color: var(--text-inverse);
    border-color: var(--accent);
    font-weight: 600;
  }
}

/* ---- 商品区域 ---- */
.products-section {
  padding: 40px 32px 64px;
}

.products-inner {
  max-width: 1320px;
  margin: 0 auto;
  min-height: 300px;
}

/* ---- 商品网格：4列 ---- */
.product-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;

  @media (max-width: 1100px) { grid-template-columns: repeat(3, 1fr); }
  @media (max-width: 768px)  { grid-template-columns: repeat(2, 1fr); gap: 14px; }
  @media (max-width: 480px)  { grid-template-columns: 1fr; }
}

/* ---- 商品卡片 ---- */
.product-card {
  background: var(--bg-card);
  border-radius: var(--r-lg);
  overflow: hidden;
  cursor: pointer;
  transition: all 0.35s var(--ease-out);
  box-shadow: var(--shadow-card);
  border: 1px solid var(--border);
  animation: fadeUp 0.5s var(--ease-out) both;

  &:hover {
    transform: translateY(-6px);
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.3);
    border-color: var(--border-light);

    .card-title {
      color: var(--accent);
    }
  }
}

.card-image {
  position: relative;
  aspect-ratio: 1 / 1;
  overflow: hidden;
  background: var(--bg-deep);
}

.card-badge {
  position: absolute;
  top: 12px;
  right: 12px;
  background: rgba(30, 36, 51, 0.75);
  backdrop-filter: blur(8px);
  color: var(--text-caption);
  font-family: var(--font-display);
  font-size: 11px;
  font-weight: 500;
  padding: 4px 12px;
  border-radius: var(--r-full);
}

.card-body {
  padding: 16px 18px 20px;
}

.card-title {
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.4;
  transition: color var(--t-fast);
}

.card-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.tag {
  font-size: 11px;
  padding: 3px 10px;
  border-radius: var(--r-full);
  background: rgba(78, 205, 196, 0.08);
  color: var(--accent);
  font-weight: 500;
}

.card-bottom {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.card-price {
  display: flex;
  align-items: baseline;
  gap: 2px;
}

.price-sym {
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 600;
  color: var(--accent);
}

.price-val {
  font-family: var(--font-display);
  font-size: 24px;
  font-weight: 700;
  color: var(--accent);
  letter-spacing: -0.5px;
}

.card-seller {
  font-size: 12px;
  color: var(--text-ghost);
}

/* ---- 分页 ---- */
.pagination-wrap {
  display: flex;
  justify-content: center;
  padding: 0 32px 64px;
}

/* ---- 移动端 ---- */
@media (max-width: 768px) {
  .hero {
    padding: 36px 16px 32px;
  }

  .hero-title {
    font-size: 28px;
  }

  .categories-bar {
    padding: 12px 16px;
    top: 72px;
  }

  .products-section {
    padding: 24px 16px 48px;
  }
}

/* ---- F3: 骨架屏 ---- */
.product-card-skel {
  cursor: default;
  pointer-events: none;
  animation: skel-pulse 1.5s ease-in-out infinite;

  .skel-image {
    width: 100%;
    height: 100%;
    background: linear-gradient(
      90deg,
      var(--bg-deep) 0%,
      var(--bg-page) 50%,
      var(--bg-deep) 100%
    );
    background-size: 200% 100%;
    animation: skel-shimmer 1.5s ease-in-out infinite;
  }

  .skel-line {
    height: 14px;
    background: linear-gradient(
      90deg,
      var(--bg-deep) 0%,
      var(--bg-page) 50%,
      var(--bg-deep) 100%
    );
    background-size: 200% 100%;
    animation: skel-shimmer 1.5s ease-in-out infinite;
    border-radius: 4px;
    margin-bottom: 8px;
  }

  .skel-line-title {
    height: 16px;
    width: 80%;
  }

  .skel-line-tag {
    width: 40%;
    height: 12px;
  }

  .skel-line-price {
    width: 35%;
    height: 20px;
    margin-bottom: 0;
  }
}

@keyframes skel-shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

@keyframes skel-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}
</style>
