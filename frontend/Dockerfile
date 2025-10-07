FROM node:18-alpine as builder

WORKDIR /app

RUN apk add --no-cache python3 make g++ git

COPY package*.json ./

RUN rm -f package-lock.json

RUN npm cache clean --force && \
    npm install --legacy-peer-deps \
                --no-package-lock \
                --loglevel verbose \
                ajv@6.12.6 \
                ajv-keywords@3.5.2 && \
    npm install --legacy-peer-deps \
                --loglevel verbose

RUN node -e "console.log('ajv version:', require('ajv/package.json').version)" && \
    node -e "console.log('ajv-keywords version:', require('ajv-keywords/package.json').version)"

COPY . .

FROM node:18-alpine

WORKDIR /app

RUN apk add --no-cache curl

COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/src ./src
COPY --from=builder /app/tsconfig.json ./tsconfig.json

ENV SKIP_PREFLIGHT_CHECK=true
ENV NODE_OPTIONS="--max_old_space_size=4096"
ENV TSC_COMPILE_ON_ERROR=true
ENV DISABLE_ESLINT_PLUGIN=true

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=5 \
  CMD curl -f http://localhost:3000 || exit 1

CMD ["sh", "-c", "npm start || (echo 'Startup failed, checking logs...' && cat /root/.npm/_logs/*.log 2>/dev/null && exit 1)"]
