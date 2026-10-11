FROM node:20.20.2-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:20.20.2-slim AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_AI_TRIGGER_TOKEN=@bot
ENV NEXT_PUBLIC_AI_TRIGGER_TOKEN=$NEXT_PUBLIC_AI_TRIGGER_TOKEN
RUN npm run build

FROM node:20.20.2-slim AS runner
WORKDIR /app
ENV NODE_ENV=production

ENV HOSTNAME=0.0.0.0 PORT=3000 NEXT_TELEMETRY_DISABLED=1

RUN groupadd --system --gid 10001 nodejs \
    && useradd --system --uid 10001 --gid nodejs --no-create-home nextjs

COPY --from=builder --chown=nextjs:nodejs /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER 10001:10001

EXPOSE 3000
CMD ["node", "server.js"]
