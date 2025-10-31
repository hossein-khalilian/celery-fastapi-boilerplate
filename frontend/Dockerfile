FROM node:25-alpine

WORKDIR /app

COPY package.json .
RUN npm install --silent

COPY . .

# Build the Next.js app at image build time so `next start` can run
RUN npm run build

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

EXPOSE 3000

CMD ["npm", "run", "start"]
