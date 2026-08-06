FROM node:22-bookworm-slim AS deps
WORKDIR /app
COPY apps/web/package.json ./
RUN npm install

FROM node:22-bookworm-slim AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY apps/web ./
COPY packages/ui-tokens /packages/ui-tokens
ENV NEXT_TELEMETRY_DISABLED=1
ENV ARCHAVOW_API_URL=http://api:8000
RUN npm run build

FROM node:22-bookworm-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3001
ENV ARCHAVOW_API_URL=http://api:8000
COPY --from=builder /app/.next/standalone ./
# Standalone nests under app/; static must sit beside that server tree
COPY --from=builder /app/.next/static ./app/.next/static
EXPOSE 3001
# outputFileTracingRoot nests the Next server under app/
CMD ["node", "app/server.js"]
