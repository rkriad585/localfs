# syntax=docker/dockerfile:1
FROM python:3.13-slim AS builder

WORKDIR /build
COPY pyproject.toml README.md ./
RUN pip install build && python -m build --wheel --sdist .

FROM python:3.13-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install /tmp/localfs-*.whl && rm /tmp/localfs-*.whl

COPY . .
RUN pip install -e .

EXPOSE 5000

ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5000

CMD ["python", "main.py"]
