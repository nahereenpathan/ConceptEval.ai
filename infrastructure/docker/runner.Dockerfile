# Hardened Rootless Execution Sandbox Image
# Concept-Aware Code Evaluation SaaS Platform

FROM python:3.12-alpine

# Metadata
LABEL maintainer="engineering@concept-eval.org"
LABEL description="Minimal, non-root execution sandbox for student Python evaluation"

# Security hardening:
# 1. Create unprivileged group and user (UID/GID 10001)
# 2. Setup isolated sandbox workspace
# 3. Strip write access from system directories
RUN addgroup -g 10001 sandbox && \
    adduser -D -u 10001 -G sandbox -s /sbin/nologin sandbox && \
    mkdir -p /sandbox/workspace && \
    chown -R sandbox:sandbox /sandbox && \
    chmod 755 /sandbox && \
    chmod 700 /sandbox/workspace

# Configure Python execution flags for isolation
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONIOENCODING=utf-8 \
    PYTHONHASHSEED=random \
    HOME=/sandbox/workspace \
    TMPDIR=/tmp

# Switch permanently to unprivileged non-root user
USER 10001:10001
WORKDIR /sandbox/workspace

# Isolated Python entrypoint:
# -I : Isolated mode (ignores PYTHONPATH and user site-packages)
# -B : Do not write .pyc bytecode files
# -u : Force unbuffered binary stdout and stderr
ENTRYPOINT ["python3", "-I", "-B", "-u"]
