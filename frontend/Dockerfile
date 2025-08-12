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

# DEBUG: Check what Railway can access
RUN echo "=== DEBUGGING RAILWAY BUILD CONTEXT ==="
RUN echo "Root directory contents:"
RUN ls -la /
RUN echo "Build context contents:"
RUN ls -la .
RUN echo "Looking for public directory:"
RUN find . -name "public" -type d 2>/dev/null || echo "No public directory found"
RUN echo "All directories in build context:"
RUN find . -type d -maxdepth 2
RUN echo "=== END DEBUG ==="

COPY --from=deps /app/node_modules ./node_modules
COPY . .

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
RUN echo "=== DEBUGGING RUNNER STAGE ==="
RUN echo "Current working directory:"
RUN pwd
RUN echo "Contents of current directory:"
RUN ls -la .
RUN echo "=== END RUNNER DEBUG ==="

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