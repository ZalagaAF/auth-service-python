FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Descomentá este bloque SOLO si psycopg está en requirements.txt sin "binary":
# RUN apt-get update \
#     && apt-get install -y --no-install-recommends libpq5 \
#     && rm -rf /var/lib/apt/lists/*

# Primero las dependencias: Docker guarda esta capa y no la reinstala
# mientras requirements.txt no cambie.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Usuario sin privilegios: el proceso no corre como root.
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin app

COPY --chown=app:app app ./app
COPY --chown=app:app alembic ./alembic
COPY --chown=app:app alembic.ini .

USER app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]