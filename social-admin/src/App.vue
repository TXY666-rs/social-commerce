<template>
  <router-view />
</template>

<style>
@import './assets/base.css';

body {
  margin: 0;
  font-family: var(--font-body);
}

#app {
  min-height: 100vh;
}

::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: var(--bg-deep);
}

::-webkit-scrollbar-thumb {
  background: var(--border-light);
  border-radius: var(--r-full);
}

::-webkit-scrollbar-thumb:hover {
  background: var(--text-ghost);
}

::selection {
  background: var(--accent-glow2);
  color: var(--text-primary);
}

h1, h2, h3, h4, h5, h6 {
  font-family: var(--font-display);
  color: var(--text-primary);
  line-height: 1.2;
}

.el-button--primary {
  --el-button-bg-color: var(--accent) !important;
  --el-button-border-color: var(--accent) !important;
  --el-button-hover-bg-color: var(--accent-dark) !important;
  --el-button-hover-border-color: var(--accent-dark) !important;
  --el-button-text-color: var(--text-inverse) !important;
}

.el-input__wrapper {
  background-color: var(--bg-input) !important;
  box-shadow: 0 0 0 1px var(--border) inset !important;
}

.el-input__inner {
  color: var(--text-primary) !important;
}

.el-input__inner::placeholder {
  color: var(--text-ghost) !important;
}

.el-pagination {
  --el-pagination-bg-color: var(--bg-card);
  --el-pagination-text-color: var(--text-caption);
  --el-pagination-button-bg-color: var(--bg-card);
}

.el-empty__description p {
  color: var(--text-caption) !important;
}
</style>
