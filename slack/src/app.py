import logging
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from .config import (
    SLACK_BOT_TOKEN,
    SLACK_APP_TOKEN,
    SUMMARY_WINDOW,
    BOT_DEBUG,
)
from .ai import summarize

# Logging
logging.basicConfig(level=logging.DEBUG if BOT_DEBUG else logging.INFO)
logger = logging.getLogger("slackbot")

# Initialize Bolt App
app = App(token=SLACK_BOT_TOKEN)

def _is_human_message(event: dict) -> bool:
    # subtype is None => normal user message; ignore bot messages/joins/edits/etc.
    return event.get("subtype") is None and bool(event.get("user"))

@app.event("message")
def on_message_events(body, logger):
    """Log all human messages in channels the bot is in."""
    event = body.get("event", {})
    if _is_human_message(event):
        channel = event.get("channel")
        user = event.get("user")
        text = event.get("text", "")
        logger.info(f"[{channel}] <@{user}>: {text}")

@app.event("app_mention")
def on_app_mention(body, say, client, logger):
    """Respond to '@bot summarize' by summarizing recent channel history."""
    event = body.get("event", {})
    channel = event.get("channel")
    user = event.get("user")
    text = (event.get("text") or "").lower()
    thread_ts = event.get("thread_ts") or event.get("ts")

    if "summarize" in text:
        # Fetch recent history
        try:
            history = client.conversations_history(channel=channel, limit=SUMMARY_WINDOW)
            msgs = [
                {"user": m.get("user"), "text": m.get("text", ""), "ts": m.get("ts")}
                for m in history.get("messages", [])
                if m.get("subtype") is None
            ]
            # We want oldest->newest for better summaries
            msgs.reverse()
            summary = summarize(msgs)
            say(text=summary, thread_ts=thread_ts)
        except Exception as e:
            logger.exception("Failed to summarize")
            say(text=f"Sorry, I couldn't summarize: `{e}`", thread_ts=thread_ts)
    else:
        say(
            text=f"Hi <@{user}>! Try `@me summarize` to summarize the last {SUMMARY_WINDOW} messages.",
            thread_ts=thread_ts,
        )

def main():
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()

if __name__ == "__main__":
    main()
