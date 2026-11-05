FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONUTF8=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home --uid 10001 tutor \
    && mkdir -p /app/data && chown tutor:tutor /app/data
COPY --chown=tutor:tutor ai_core.py api.py code_verifier.py rag_api.py rag_core.py rag_store.py document_ingest.py student_import.py manage_accounts.py ./
COPY --chown=tutor:tutor data/language_reference.json ./language_reference.json
COPY --chown=tutor:tutor static/ ./static/
USER tutor
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=8).close()"
CMD ["python", "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--timeout-keep-alive", "5", "--no-access-log"]
