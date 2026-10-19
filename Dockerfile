FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 CREWAI_TELEMETRY_DISABLED=true OTEL_SDK_DISABLED=true
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home appuser && mkdir -p /app/data && chown appuser:appuser /app/data
COPY app.py .
COPY reporting.py reports_ui.py natural_reports.py .
COPY ml_traditional.py multi_agents.py duckdb_tools.py usage_policy.py .
COPY observability.py local_rag.py train_reproducible.py evaluate_golden.py initialize_app.py run_tests.py .
COPY data/models/etapa2/ /app/model_seed/
COPY rag/ /app/rag/
COPY evaluation/ /app/evaluation/
COPY tests/ /app/tests/
COPY data/*.csv /app/seed/
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
# Match the scikit-learn version used to train the saved model.
RUN pip install --no-cache-dir scikit-learn==1.7.2
USER appuser
EXPOSE 8501
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health', timeout=3)" || exit 1
CMD ["sh", "-c", "python initialize_app.py && exec streamlit run app.py --server.address=0.0.0.0 --server.port=8501 --server.headless=true --browser.gatherUsageStats=false"]
