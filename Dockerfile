# 使用官方Python运行时作为基础镜像
FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml .
COPY README.md .

RUN pip install --no-cache-dir . --index-url=https://mirrors.aliyun.com/pypi/simple/

COPY main.py .

ENTRYPOINT ["pysample"]
