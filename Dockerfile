FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

RUN chown nobody /app

COPY *.py pyproject.toml uv.lock README.md ./
RUN pip install --no-cache-dir uv \
    && uv sync --frozen --no-dev

# USER nobody
ENV PYTHONUNBUFFERED=on
ENV PATH="/app/.venv/bin:$PATH"

CMD ["chainlit", "run", "main.py", "--port=8080", "--host=0.0.0.0", "--headless"]
