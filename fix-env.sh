#!/bin/bash
// filepath: fix-env.sh

echo "🔧 Setting up .env file..."

if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ Created .env from .env.example"
else
    echo "✅ .env file already exists"
fi

# Check if OPENAI_API_KEY is set
if ! grep -q "OPENAI_API_KEY=sk-" .env; then
    echo ""
    echo "⚠️  OPENAI_API_KEY not configured"
    echo ""
    read -p "Enter your OpenAI API key (or press Enter to skip): " api_key
    
    if [ -n "$api_key" ]; then
        # Update .env file
        if grep -q "OPENAI_API_KEY=" .env; then
            sed -i.bak "s|OPENAI_API_KEY=.*|OPENAI_API_KEY=$api_key|" .env
        else
            echo "OPENAI_API_KEY=$api_key" >> .env
        fi
        echo "✅ OPENAI_API_KEY updated in .env"
    else
        echo "⚠️  Skipping API key setup - you'll need to add it manually to .env"
    fi
fi

echo ""
echo "📋 Current .env configuration:"
cat .env | grep -v "API_KEY" | head -10