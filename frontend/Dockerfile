# Use the official Node.js runtime as the base image
FROM node:18-alpine AS base

# Install dependencies only when needed
FROM base AS deps
# Check https://github.com/nodejs/docker-node/tree/b4117f9333da4138b03a546ec926ef50a31506c3#nodealpine to understand why libc6-compat might be needed.
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Copy package files (Railway sets build context to frontend/ directory)
COPY package.json package-lock.json ./

# Install all dependencies (including devDependencies for build)
RUN npm ci

# Rebuild the source code only when needed
FROM base AS builder
WORKDIR /app

# DEBUG: Check what Railway can access (force output with cache busting)
ARG CACHEBUST=1
RUN echo "=== DEBUGGING RAILWAY BUILD CONTEXT BUST${CACHEBUST} ===" >&2
RUN echo "Build context contents:" >&2 && ls -la . >&2 && echo "CACHE_BUST_A${CACHEBUST}" >&2
RUN echo "Looking for public directory:" >&2 && (find . -name "public" -type d 2>&1 || echo "No public directory found") >&2 && echo "CACHE_BUST_B${CACHEBUST}" >&2
RUN echo "All directories in build context:" >&2 && find . -type d -maxdepth 2 >&2 && echo "CACHE_BUST_C${CACHEBUST}" >&2
RUN echo "=== END DEBUG ===" >&2

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# DEBUG: Check if public directory exists after COPY . .
RUN echo "After COPY . . check:" >&2 && ls -la . >&2 && ls -la public >&2 || echo "No public dir after copy" >&2 && echo "CACHE_BUST_D${CACHEBUST}" >&2

# Disable telemetry during build
ENV NEXT_TELEMETRY_DISABLED=1

# Build the application
RUN npm run build

# Production image, copy all the files and run Next.js
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Create nextjs user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# DEBUG: Check what's available in runner stage for copying public
RUN echo "=== DEBUGGING RUNNER STAGE BUST${CACHEBUST} ===" >&2
RUN echo "Current working directory:" >&2 && pwd >&2 && echo "CACHE_BUST_E${CACHEBUST}" >&2
RUN echo "Contents of current directory:" >&2 && ls -la . >&2 && echo "CACHE_BUST_F${CACHEBUST}" >&2
RUN echo "Builder stage public check:" >&2 && ls -la /app/public >&2 || echo "No /app/public in builder stage" >&2 && echo "CACHE_BUST_G${CACHEBUST}" >&2
RUN echo "=== END RUNNER DEBUG ===" >&2

# Copy public assets directly from source (unchanged by build)
COPY --from=builder /app/public ./public

# Set the correct permission for prerender cache
RUN mkdir .next
RUN chown nextjs:nodejs .next

# Copy standalone application and static files
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/api/health || exit 1

CMD ["node", "server.js"]