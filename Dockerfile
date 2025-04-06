FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install --prefix=/install -r requirements.txt

# imagem final (mais enxuta)
FROM python:3.11-slim AS final

WORKDIR /app

COPY --from=builder /install /usr/local

COPY . .

CMD ["uvicorn", "utils.api.app:app", "--host", "0.0.0.0", "--port", "8000"]