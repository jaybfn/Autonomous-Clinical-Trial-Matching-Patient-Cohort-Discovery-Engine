# syntax=docker/dockerfile:1
FROM mcr.microsoft.com/devcontainers/python:3.11-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Optional system tools used later for Terraform / GCP local workflows
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates git make \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY requirements-dev.txt pyproject.toml README.md ./
COPY src ./src

RUN pip install --upgrade pip \
    && pip install -r requirements-dev.txt

CMD ["sleep", "infinity"]
