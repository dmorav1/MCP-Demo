#!/bin/bash

# Slack Ingest Processor Runner
# Processes Slack messages and ingests them as conversations into the database

set -e

echo "🚀 Starting Slack Ingest Processor..."

# Validate tokens
if [[ -z "$SLACK_BOT_TOKEN" || -z "$SLACK_APP_TOKEN" ]]; then
    echo "❌ Error: SLACK_BOT_TOKEN and SLACK_APP_TOKEN must be set"
    exit 1
fi

if [[ ! "$SLACK_BOT_TOKEN" =~ ^xoxb- ]]; then
    echo "❌ Error: SLACK_BOT_TOKEN must start with 'xoxb-'"
    exit 1
fi

if [[ ! "$SLACK_APP_TOKEN" =~ ^xapp- ]]; then
    echo "❌ Error: SLACK_APP_TOKEN must start with 'xapp-'"
    exit 1
fi

# Set defaults
CHANNEL=${SLACK_CHANNEL:-"warchan-ai"}
INTERVAL=${PROCESS_INTERVAL:-300}
BATCH_SIZE=${BATCH_SIZE:-20}
MIN_MESSAGES=${MIN_MESSAGES:-3}

echo "📋 Configuration:"
echo "   Channel: #$CHANNEL"
echo "   Interval: ${INTERVAL}s"
echo "   Batch size: $BATCH_SIZE messages"
echo "   Min messages: $MIN_MESSAGES"

# Build and run
cd "$(dirname "$0")"
docker build -t mcp-slack-ingest:dev .

docker run --rm -it \
  --name slack-ingest-processor \
  -e SLACK_BOT_TOKEN="$SLACK_BOT_TOKEN" \
  -e SLACK_APP_TOKEN="$SLACK_APP_TOKEN" \
  -e DATABASE_URL="${DATABASE_URL:-sqlite:///./mcp_data.db}" \
  -v "$PWD":/usr/src/app \
  -w /usr/src/app \
  mcp-slack-ingest:dev \
  python -u tools/slack_ingest_processor.py \
    --channel "$CHANNEL" \
    --interval "$INTERVAL" \
    --batch-size "$BATCH_SIZE" \
    --min-messages "$MIN_MESSAGES"