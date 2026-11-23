# Frontend image - React application built by Vite, served by nginx.
# Build context: repository root (see docker-compose.yml).

# Base images pinned by digest (review S7, read on 30/10); Dependabot proposes the updates.
FROM node:22-slim@sha256:e9f565d32859f0cbfb52125eafe8be39390f24dac302dc3cdf566e8ba3ab21ee AS build

WORKDIR /app

# Dependencies first: this layer is rebuilt only when the lock file changes.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY frontend/ ./

# URL of the API as seen from the user's browser (fixed at build time).
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build


# Unprivileged variant of the official nginx image: runs as user 101, never as root, and
# keeps its pid and temporary files in /tmp (read-only root file system, review S7).
FROM nginxinc/nginx-unprivileged:stable-alpine@sha256:f5116ed4606f3eb015dd4a8e28cb9b351476dc0ad4bc6e9f93b19cec130cdf03

COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 3000
