<template>
  <!-- F3: 通用骨架屏组件 -->
  <div class="skeleton" :class="[`skeleton-${variant}`, { 'skeleton-dark': dark }]">
    <slot />
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  variant?: 'text' | 'card' | 'circle' | 'product-grid' | 'order-card';
  dark?: boolean;
}>(), {
  variant: 'text',
  dark: false,
});
</script>

<style scoped lang="scss">
.skeleton {
  --sk-base: rgba(255, 255, 255, 0.06);
  --sk-shine: rgba(255, 255, 255, 0.1);

  &.skeleton-dark {
    --sk-base: rgba(0, 0, 0, 0.08);
    --sk-shine: rgba(0, 0, 0, 0.12);
  }

  background: linear-gradient(
    90deg,
    var(--sk-base) 0%,
    var(--sk-shine) 50%,
    var(--sk-base) 100%
  );
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s ease-in-out infinite;
  border-radius: var(--radius-md, 8px);

  @keyframes skeleton-shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
  }
}

// Text variant
.skeleton-text {
  height: 16px;
  width: 100%;
  border-radius: 4px;
}

// Circle variant (avatar)
.skeleton-circle {
  border-radius: 50%;
  width: 40px;
  height: 40px;
}

// Card variant
.skeleton-card {
  border-radius: var(--radius-lg, 12px);
}

// Product grid skeleton
.skeleton-product-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 20px;
  padding: 16px;

  .product-skel {
    background: var(--bg-card);
    border-radius: var(--radius-lg, 12px);
    overflow: hidden;

    .skel-image {
      aspect-ratio: 1;
      background: linear-gradient(
        90deg,
        var(--sk-base) 0%,
        var(--sk-shine) 50%,
        var(--sk-base) 100%
      );
      background-size: 200% 100%;
      animation: skeleton-shimmer 1.5s ease-in-out infinite;
    }

    .skel-body {
      padding: 12px;

      .skel-line {
        height: 14px;
        background: linear-gradient(
          90deg,
          var(--sk-base) 0%,
          var(--sk-shine) 50%,
          var(--sk-base) 100%
        );
        background-size: 200% 100%;
        animation: skeleton-shimmer 1.5s ease-in-out infinite;
        border-radius: 4px;
        margin-bottom: 8px;

        &:first-child { width: 80%; height: 16px; }
        &:nth-child(2) { width: 50%; }
        &:last-child { width: 35%; height: 20px; margin-bottom: 0; }
      }
    }
  }

  @keyframes skeleton-shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
  }
}

// Order card skeleton
.skeleton-order-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  background: var(--bg-card);
  border-radius: var(--radius-lg, 12px);
}
</style>
