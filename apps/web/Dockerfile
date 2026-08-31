FROM node:20-alpine

RUN npm install -g pnpm@10.29.3

WORKDIR /workspace

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json apps/web/package.json
COPY packages/shared/package.json packages/shared/package.json
RUN pnpm install --frozen-lockfile --filter @agentops/web...

COPY apps/web apps/web
COPY packages/shared packages/shared

WORKDIR /workspace/apps/web

EXPOSE 3000

CMD ["pnpm", "dev", "--hostname", "0.0.0.0"]
