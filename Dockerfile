FROM python:3.11-slim
WORKDIR /app
COPY requirements.lock.txt .
RUN python -m pip install --no-cache-dir -r requirements.lock.txt \
    && useradd --create-home --uid 10001 queryguard
COPY --chown=queryguard:queryguard . .
RUN mkdir -p /app/.local && chown queryguard:queryguard /app/.local
USER queryguard
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "queryguard.api:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
