<template>
  <!-- F2: Intersection Observer 图片懒加载 + 渐进式加载 -->
  <div class="lazy-image" :class="{ loaded: isLoaded, error: hasError }" :style="{ aspectRatio }">
    <!-- 占位/骨架 -->
    <div v-if="!isLoaded && !hasError" class="lazy-placeholder">
      <div class="placeholder-shimmer"></div>
    </div>

    <!-- 真实图片 -->
    <img
      v-show="isLoaded"
      ref="imgRef"
      :src="actualSrc"
      :alt="alt"
      :class="fitClass"
      @load="onLoad"
      @error="onError"
    />

    <!-- 错误兜底 -->
    <div v-if="hasError" class="lazy-error">
      <slot name="error">
        <el-icon :size="24" color="#454B5E"><Picture /></el-icon>
      </slot>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { Picture } from '@element-plus/icons-vue'

const props = withDefaults(defineProps<{
  src: string
  alt?: string
  fit?: 'cover' | 'contain' | 'fill' | 'none' | 'scale-down'
  aspectRatio?: string  // e.g. "1/1", "4/3", "16/9"
  lazy?: boolean        // 是否启用懒加载
}>(), {
  alt: '',
  fit: 'cover',
  aspectRatio: '1/1',
  lazy: true,
})

const imgRef = ref<HTMLImageElement>()
const isLoaded = ref(false)
const hasError = ref(false)
const actualSrc = ref('')
let observer: IntersectionObserver | null = null

const fitClass = computed(() => `fit-${props.fit}`)

function onLoad() {
  isLoaded.value = true
  hasError.value = false
}

function onError() {
  hasError.value = true
  isLoaded.value = false
}

onMounted(() => {
  if (!props.lazy) {
    // 不懒加载，直接设置src
    actualSrc.value = props.src
    return
  }

  // Intersection Observer 懒加载
  if (!imgRef.value) return

  observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          actualSrc.value = props.src
          observer?.unobserve(entry.target)
          observer?.disconnect()
        }
      })
    },
    {
      rootMargin: '200px',  // 提前200px加载
      threshold: 0.01,
    }
  )

  observer.observe(imgRef.value.parentElement!)
})

onBeforeUnmount(() => {
  observer?.disconnect()
})
</script>

<style scoped lang="scss">
.lazy-image {
  position: relative;
  overflow: hidden;
  background: var(--bg-deep);
  width: 100%;

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    transition: opacity 0.3s ease;

    &.fit-cover { object-fit: cover; }
    &.fit-contain { object-fit: contain; }
    &.fit-fill { object-fit: fill; }
    &.fit-none { object-fit: none; }
    &.fit-scale-down { object-fit: scale-down; }
  }

  &.loaded img {
    animation: fadeIn 0.4s ease;
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }
}

.lazy-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;

  .placeholder-shimmer {
    width: 100%;
    height: 100%;
    background: linear-gradient(
      90deg,
      var(--bg-deep) 0%,
      var(--bg-page) 50%,
      var(--bg-deep) 100%
    );
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
  }

  @keyframes shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
  }
}

.lazy-error {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-deep);
}
</style>
