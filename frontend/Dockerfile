FROM node:18-alpine

WORKDIR /app

RUN apk add --no-cache curl python3 make g++ git

# Copy dependency manifests first for better layer caching
COPY package.json ./

# Install dependencies deterministically (keep lockfile if it exists in future)
RUN npm set fund false && \
    npm config set update-notifier false && \
    npm install --legacy-peer-deps --loglevel warn

# Copy application source
COPY public ./public
COPY src ./src
COPY tsconfig.json ./
# (Optional) Environment files are intentionally not copied by default to avoid Docker build cache busting
# and accidental inclusion of secrets. If needed for build-time vars, explicitly COPY a specific .env file.
# COPY .env.development ./.env.development

ENV SKIP_PREFLIGHT_CHECK=true \
    NODE_OPTIONS="--max_old_space_size=1536" \
    TSC_COMPILE_ON_ERROR=true \
    DISABLE_ESLINT_PLUGIN=true \
    FAST_REFRESH=false

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
  CMD node -e "require('http').get('http://localhost:3000',r=>process.exit(r.statusCode===200?0:1)).on('error',()=>process.exit(1))"

# Add startup script
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Use entrypoint script for clearer logging and proper command execution
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["npm", "start"]
