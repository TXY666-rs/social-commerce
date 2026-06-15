# ============================================================
# Stage 1: Builder — install dependencies into a virtual env
# 优化：去掉 gcc（依赖都是预编译 wheel）+ pip 国内镜像加速
# ============================================================
FROM python:3.12-slim AS builder

WORKDIR /build

# pip 国内镜像加速（清华源）
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

COPY requirements.txt .

# Create a virtual env and install all Python dependencies
# （依赖都是预编译 wheel，无需 gcc 编译）
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# ============================================================
# Stage 2: Runtime — minimal production image
# ============================================================
FROM python:3.12-slim AS runtime

LABEL maintainer="ai-agent"
LABEL description="AI 智能客服 Agent — LangGraph ReAct + 多 Skill + 流式输出"
LABEL version="2.0.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai

# Create a non-root user
RUN groupadd --system --gid 1001 appuser && \
    useradd --system --uid 1001 --gid appuser --no-create-home appuser

# Copy the virtual env from the builder stage
COPY --from=builder /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY . .

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
