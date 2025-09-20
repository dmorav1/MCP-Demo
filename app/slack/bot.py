# app/bot.py

import os
import logging
from flask import Flask, request, make_response, jsonify
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.signature import SignatureVerifier

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
if not SLACK_BOT_TOKEN or not SLACK_SIGNING_SECRET:
    raise RuntimeError("SLACK_BOT_TOKEN and SLACK_SIGNING_SECRET must be set")

client = WebClient(token=SLACK_BOT_TOKEN)
signature_verifier = SignatureVerifier(signing_secret=SLACK_SIGNING_SECRET)

app = Flask(__name__)

@app.route("/slack/events", methods=["POST"])
def slack_events():
    # Verify request signature
    if not signature_verifier.is_valid_request(request.get_data(), request.headers):
        return make_response("Invalid signature", 403)

    data = request.get_json(silent=True) or {}

    # URL verification challenge
    if data.get("type") == "url_verification" and "challenge" in data:
        return make_response(data["challenge"], 200, {"content_type": "text/plain"})

    event = data.get("event", {}) or {}
    # Handle basic message events (ignore bot messages)
    if event.get("type") == "message" and event.get("subtype") is None and event.get("user"):
        channel = event.get("channel")
        text = event.get("text", "")
        try:
            # Simple echo reply
            client.chat_postMessage(channel=channel, text=f"Echo: {text}")
        except SlackApiError as e:
            logger.warning("Slack API error: %s", e.response.get("error"))

    return make_response("OK", 200)

@app.route("/health", methods=["GET"])
def health():
    return jsonify(status="ok"), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
