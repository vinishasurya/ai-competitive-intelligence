# Playwright base image: Chromium + system deps preinstalled, matching the
# pinned playwright==1.62.x in uv.lock.
FROM mcr.microsoft.com/playwright/python:v1.62.0-noble

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && uv export --no-dev --format requirements-txt > requirements.txt \
    && pip install --no-cache-dir -r requirements.txt

COPY app ./app

# ANTHROPIC_API_KEY, SEARCH_API_KEY, FRONTEND_ORIGIN come from the host env.
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
