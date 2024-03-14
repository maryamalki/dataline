# Run linter on dockerfile to make sure we are following best practices
FROM hadolint/hadolint:v1.17.5-6-gbc8bab9-alpine

# Copy the dockerfile and linter config from the context
COPY hadolint.yaml /config/
COPY Dockerfile .

# Execute the linting process
RUN echo "### Linting Dockerfile ###" && /bin/hadolint --config /config/hadolint.yaml Dockerfile

# ------------------------------
#          TEMP STAGES
# ------------------------------
# Temp Stage - Build frontend to export dist folder
FROM node:21-alpine as base-frontend
# Need python for node-gyp in building
RUN apk add --no-cache python3 make gcc g++
WORKDIR /home/dataline/frontend
COPY text2sql-frontend/package.json text2sql-frontend/package-lock.json ./
RUN npm install

# Copy in frontend source
COPY text2sql-frontend/*.json ./
COPY text2sql-frontend/*.ts ./
COPY text2sql-frontend/*.js ./
COPY text2sql-frontend/index.html ./
COPY text2sql-frontend/public ./public
COPY text2sql-frontend/src ./src

# Temporary setup - need local env as the 'production' build is landing page only
ENV NODE_ENV=local
RUN npm run build

# ------------------------------
# Temp Stage - Build python wheels to export
FROM python:3.11.6-slim as requirements-stage

WORKDIR /tmp

RUN pip install poetry poetry-plugin-export

COPY text2sql-backend/pyproject.toml text2sql-backend/poetry.lock* /tmp/

RUN poetry export -f requirements.txt --output requirements.txt --without-hashes

RUN apt-get update \
    && apt-get -y install --no-install-recommends libpq-dev gcc python3-dev sudo

RUN pip wheel --no-cache-dir --no-deps --wheel-dir ./wheels -r requirements.txt

# ------------------------------
# Temp Stage - Get files for caddy
FROM debian:12-slim as caddy-temp

WORKDIR /tmp

RUN apt update && apt upgrade -y && \
    apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
RUN curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o ./caddy-stable-archive-keyring.gpg
RUN curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee ./caddy-stable.list

# ------------------------------
#            BASE
# ------------------------------
# First Stage - Build base image
FROM python:3.11.6-slim-bookworm as base

RUN apt-get update && apt-get -y install --no-install-recommends libpq5

# Update packages and install security patches
# Set working directory
WORKDIR /home/dataline/backend

COPY --from=requirements-stage /tmp/wheels /wheels
COPY --from=requirements-stage /tmp/requirements.txt .

# ANNOYING: removing wheels doesn't reduce size
RUN pip install --no-cache /wheels/* && rm -rf /wheels/

# ------------------------------
#            PROD
# ------------------------------
# Third Stage - Build production image (excludes dev dependencies)
FROM base as prod

# Setup supervisor and caddy
WORKDIR /home/dataline

# Install supervisor to manage be/fe processes
RUN pip install --no-cache-dir supervisor

# Install Caddy server
COPY --from=caddy-temp /tmp/caddy-stable-archive-keyring.gpg /usr/share/keyrings/caddy-stable-archive-keyring.gpg
COPY --from=caddy-temp /tmp/caddy-stable.list /etc/apt/sources.list.d/caddy-stable.list
RUN apt update
RUN apt install caddy


# ------------------------------
#            RUNNER
# ------------------------------
# Last stage - Copy frontend build and backend source and run
FROM prod as runner

# Copy in supervisor config, frontend build, backend source
COPY supervisord.conf .
COPY --from=base-frontend /home/dataline/frontend/dist /home/dataline/frontend/dist

# Copy in backend files
WORKDIR /home/dataline/backend
COPY text2sql-backend/*.py .
COPY text2sql-backend/dataline ./dataline
COPY text2sql-backend/alembic ./alembic
COPY text2sql-backend/alembic.ini .

WORKDIR /home/dataline

EXPOSE 7377
EXPOSE 2222

CMD ["supervisord", "-n"]
