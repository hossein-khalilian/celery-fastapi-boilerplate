# Stage 1: build
FROM node:24-slim AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: prod image
FROM node:24-slim
WORKDIR /app
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/public ./public
ENV NEXT_TELEMETRY_DISABLED=1
EXPOSE 3000
CMD ["npm", "run", "start"]
