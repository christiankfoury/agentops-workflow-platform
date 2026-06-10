FROM node:20-alpine

RUN npm install -g pnpm@10

WORKDIR /app

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .

EXPOSE 3000

CMD ["sh", "-c", "CI=true pnpm install --frozen-lockfile && pnpm dev"]
