FROM node:20-alpine AS builder

WORKDIR /app
RUN npm install -g pnpm

# Copy workspace configs
COPY pnpm-workspace.yaml package.json ./

# Copy packages strictly needed for OSS
COPY packages/core ./packages/core
COPY apps/api ./apps/api

# Install dependencies (ignoring enterprise)
# We use --filter to strict install only what's needed for api and core
RUN pnpm install --no-frozen-lockfile \
    --filter @tabi/core --filter api

# Build
RUN pnpm --filter @tabi/core build
RUN pnpm --filter api build

# Runtime Stage
FROM node:20-alpine
WORKDIR /app
ENV APP_MODE=oss

# Copy built artifacts
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/packages/core/dist ./packages/core/dist
COPY --from=builder /app/apps/api/dist ./apps/api/dist
COPY --from=builder /app/packages/core/package.json ./packages/core/package.json
COPY --from=builder /app/apps/api/package.json ./apps/api/package.json

CMD ["node", "apps/api/dist/main.js"]
