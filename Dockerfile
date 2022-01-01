FROM python:3.9-slim as reqs

WORKDIR /tmp

RUN pip install --no-cache-dir -U pip poetry

COPY ./pyproject.toml ./poetry.lock* ./

RUN poetry export -f requirements.txt --output requirements.txt --without-hashes


FROM python:3.9-slim

WORKDIR /app

RUN apt-get update -y \
    && apt-get install -y wait-for-it

COPY --from=reqs /tmp/requirements.txt ./

RUN pip install -U pip \
    && pip install --no-cache-dir -U -r requirements.txt

COPY . .
