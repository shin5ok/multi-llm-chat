FROM python:3.12.3-slim

COPY *.py poetry.lock pyproject.toml README.md ./
RUN pip install --no-cache-dir poetry \
  && poetry config virtualenvs.in-project true
RUN poetry install --no-root

# USER nobody
ENV PYTHONUNBUFFERED=on

CMD ["poetry", "run", "chainlit", "run", "main.py", "--port=8080", "--host=0.0.0.0", "--headless"]
