FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

RUN chown nobody /app

COPY *.py pyproject.toml README.md ./
RUN pip install --no-cache-dir poetry \
    && poetry self add poetry-plugin-export \
    && poetry export -o requirements.txt \
    && pip uninstall -y poetry \
    && pip install --no-cache-dir uv \
    && uv pip install --system -r requirements.txt

USER nobody
ENV PYTHONUNBUFFERED=on

CMD ["chainlit", "run", "main.py", "--port=8080", "--host=0.0.0.0", "--headless"]
