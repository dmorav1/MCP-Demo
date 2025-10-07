#!/bin/bash
// filepath: fix-package-json.sh

echo "🔧 Fixing package.json (removing comments)..."

if [ ! -f frontend/package.json ]; then
    echo "❌ frontend/package.json not found"
    exit 1
fi

cat > frontend/package.json << 'EOF'
{
  "name": "mcp-chat-frontend",
  "version": "1.0.0",
  "private": true,
  "dependencies": {
    "@testing-library/jest-dom": "^5.17.0",
    "@testing-library/react": "^13.4.0",
    "@testing-library/user-event": "^13.5.0",
    "@types/jest": "^27.5.2",
    "@types/node": "^16.18.0",
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "axios": "^1.6.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-scripts": "5.0.1",
    "typescript": "^4.9.5",
    "web-vitals": "^2.1.4",
    "ajv": "6.12.6",
    "ajv-keywords": "3.5.2"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject"
  },
  "eslintConfig": {
    "extends": ["react-app", "react-app/jest"]
  },
  "browserslist": {
    "production": [">0.2%", "not dead", "not op_mini all"],
    "development": ["last 1 chrome version", "last 1 firefox version", "last 1 safari version"]
  },
  "overrides": {
    "ajv": "6.12.6",
    "ajv-keywords": "3.5.2",
    "schema-utils": {
      "ajv": "6.12.6",
      "ajv-keywords": "3.5.2"
    },
    "webpack-dev-server": {
      "ajv": "6.12.6",
      "ajv-keywords": "3.5.2"
    }
  }
}
EOF

echo "✅ package.json fixed"
echo ""
echo "Now run: ./start-all.sh"