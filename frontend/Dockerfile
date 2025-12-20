FROM node:25-alpine

WORKDIR /app

COPY package.json .
RUN npm install --silent

COPY . .

# Build the app (required for production, but also available for dev fallback)
# In development mode, volumes will mount source and `npm run dev` will handle hot reload
RUN npm run build

ENV NEXT_TELEMETRY_DISABLED=1

EXPOSE 3000

# Default command (production mode)
# Will be overridden in docker-compose.yml based on PRODUCTION env var
CMD ["npm", "run", "start"]
