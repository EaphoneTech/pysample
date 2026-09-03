# 多阶段构建：builder 用 uv 解析并安装依赖到 .venv，runner 仅复制运行所需。
FROM ghcr.io/astral-sh/uv:python3.12-trixie-slim AS builder
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
WORKDIR /app

# 先复制项目元数据与 lock，最大化依赖层缓存（依赖不变时跳过重装）。
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# 项目文件量少，逐个显式 COPY（不依赖 .dockerignore 决定进入镜像的内容）。
# hatchling 打包 main.py 需要 README.md（readme 字段）与 LICENSE/licenses/*（license-files）；
# LICENSE/THIRD-PARTY-LICENSES.md 一并带入镜像作为许可证文档。
COPY main.py README.md LICENSE THIRD-PARTY-LICENSES.md ./
COPY licenses/ ./licenses/
# VARIANT 控制 optional 依赖组：
#   builtin（默认）-> 仅 MIT/BSD 依赖（pathspec / typer-slim / python-docx），许可证纯净
#   external       -> 额外引入 GPL-3.0 聚合依赖 copyright-code-extractor
# 本地/CI 构建：
#   docker build .                                    # 标准版
#   docker build . --build-arg VARIANT=external       # external 版
ARG VARIANT=builtin
RUN if [ "$VARIANT" = "external" ]; then \
      uv sync --frozen --no-dev --extra external; \
    else \
      uv sync --frozen --no-dev; \
    fi

FROM python:3.12-slim-trixie AS runner
WORKDIR /app
COPY --from=builder /app /app
ENV PATH="/app/.venv/bin:$PATH" \
    LOG_LEVEL=INFO
ENTRYPOINT ["pysample"]
