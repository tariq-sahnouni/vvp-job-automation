FROM python:3.12-alpine AS base

RUN apk add --no-cache git ca-certificates

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app /app

ENV PYTHONUNBUFFERED=1

FROM base AS test
COPY tests /tests
RUN python -m unittest discover -s /tests

FROM base AS runtime
ENTRYPOINT ["python", "/app/vvp_gitops_sync.py"]
