# ============================================================
# social-admin Dockerfile —— 多阶段构建
# ============================================================

FROM node:22-alpine AS builder

WORKDIR /build
COPY package.json package-lock.json* ./
RUN npm config set registry https://registry.npmmirror.com \
 && (npm ci --prefer-offline || npm install --prefer-offline)

COPY . .
RUN npx vite build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /build/dist /usr/share/nginx/html

STOPSIGNAL SIGQUIT
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
