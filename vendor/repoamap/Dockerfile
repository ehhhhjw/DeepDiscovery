FROM node:22-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir /repoamap
WORKDIR /repoamap

# Install dependencies and build repoamap, then link the package to the global scope
# To reduce the size of the layer, npm ci and npm link are executed in the same RUN command
COPY . .
RUN npm ci \
    && npm run build \
    && npm link \
    && npm ci --omit=dev \
    && npm cache clean --force

WORKDIR /app

# Check the operation of repoamap
RUN repoamap --version
RUN repoamap --help

ENTRYPOINT ["repoamap"]
