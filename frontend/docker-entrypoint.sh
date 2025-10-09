#!/bin/sh
set -eu

echo "Starting frontend (React dev server)..."
echo "Node: $(node -v)"
echo "NPM:  $(npm -v)"

echo "Working directory: $(pwd)"
ls -1 || true

# If node_modules not present (mounted volume scenario), install quickly
if [ ! -d node_modules ]; then
  echo "node_modules missing - installing dependencies (this should be cached in image)"
  npm install --legacy-peer-deps --loglevel warn
fi

# Disable color codes in output for cleaner container logs
export FORCE_COLOR=0

# Start React dev server
exec "$@"
