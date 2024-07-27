FROM python:3.12.3-slim

COPY main.py poetry.lock pyproject.toml ./
RUN pip install --no-cache-dir poetry \
  && poetry config virtualenvs.in-project true
RUN poetry install

# USER nobody
ENV PYTHONUNBUFFERED=on

CMD ["poetry", "run", "chainlit", "run", "main.py", "--port=8080", "--host=0.0.0.0", "--headless"]
