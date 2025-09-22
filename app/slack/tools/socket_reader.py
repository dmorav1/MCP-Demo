import os
import sys
import time
import ssl
import certifi
import argparse
import threading
from datetime import datetime, timezone
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.errors import SlackApiError

def ts_to_str(ts: str) -> str:
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ts

def resolve_channel_id(client, channel_name: str) -> str | None:
    name = channel_name.lstrip("#").lower()
    cursor = None
    while True:
        resp = client.conversations_list(types="public_channel,private_channel", limit=1000, cursor=cursor)
        for ch in resp.get("channels", []):
            if ch.get("name", "").lower() == name:
                return ch["id"]
        cursor = resp.get("response_metadata", {}).get("next_cursor") or None
        if not cursor:
            break
    return None

def build_user_names(client, user_ids: set[str]) -> dict[str, str]:
    names = {}
    for uid in user_ids:
        try:
            ui = client.users_info(user=uid)
            u = ui.get("user", {}) or {}
            names[uid] = u.get("real_name") or u.get("name") or uid
        except SlackApiError:
            names[uid] = uid
    return names

def poll_loop(app: App, channel_id: str, interval_sec: int, limit: int):
    last_ts: str | None = None
    ssl_ctx = ssl.create_default_context(cafile=certifi.where())
    # Use the same token but with custom SSL context to avoid macOS cert issues
    client = app.client.__class__(token=app.client.token, ssl=ssl_ctx)
    while True:
        try:
            kw = {"channel": channel_id, "limit": limit}
            if last_ts:
                kw["oldest"] = last_ts
                kw["inclusive"] = False
            resp = client.conversations_history(**kw)
            messages = resp.get("messages", [])
            if messages:
                # sort oldest first
                messages = sorted(messages, key=lambda m: float(m.get("ts", "0")))
                # resolve user names
                user_ids = {m.get("user") for m in messages if m.get("user")}
                user_map = build_user_names(client, {u for u in user_ids if u})
                for m in messages:
                    ts = ts_to_str(m.get("ts", ""))
                    user = user_map.get(m.get("user") or "", m.get("username") or "bot")
                    text = m.get("text", "")
                    print(f"[{ts}] {user}: {text}", flush=True)
                last_ts = messages[-1]["ts"]
        except SlackApiError as e:
            print(f"Slack API error: {e.response.get('error')}", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr, flush=True)
        time.sleep(interval_sec)

def main():
    ap = argparse.ArgumentParser(description="Socket-mode Slack channel reader (polls every N seconds).")
    ap.add_argument("--channel", "-c", default="warchan-ai", help="Channel name (e.g., warchan-ai)")
    ap.add_argument("--interval", "-i", type=int, default=120, help="Polling interval seconds")
    ap.add_argument("--limit", "-n", type=int, default=100, help="Max messages per poll")
    args = ap.parse_args()

    bot_token = os.getenv("SLACK_BOT_TOKEN", "")
    app_token = os.getenv("SLACK_APP_TOKEN", "")
    if not bot_token or not app_token:
        print("Set SLACK_BOT_TOKEN (xoxb-...) and SLACK_APP_TOKEN (xapp-...) in env.", file=sys.stderr)
        sys.exit(1)
    if not bot_token.startswith("xoxb-"):
        print("SLACK_BOT_TOKEN must start with xoxb- (bot token).", file=sys.stderr); sys.exit(1)
    if not app_token.startswith("xapp-"):
        print("SLACK_APP_TOKEN must start with xapp- (App-Level token with connections:write).", file=sys.stderr); sys.exit(1)

    # Create Bolt app (Socket Mode)
    app = App(token=bot_token)

    READ_ONLY = os.getenv("READ_ONLY", "true").lower() == "true"

    # Handle generic message events (to avoid "Unhandled request" logs)
    @app.event("message")
    def handle_message_events(event, logger, say):
        if event.get("subtype") or event.get("bot_id"):
            return
        logger.info(f"[message] ch={event.get('channel')} user={event.get('user')} text={event.get('text')}")
        if not READ_ONLY:
            # say requires chat:write scope
            say(f"Echo: {event.get('text')}")

    @app.event("app_mention")
    def handle_app_mention(event, say, logger):
        user = event.get("user")
        text = event.get("text", "")
        logger.info(f"[mention] user={user} text={text}")
        if not READ_ONLY:
            say(f"Hi <@{user}>! I’m listening.")

    # Resolve channel ID before starting
    chan_id = resolve_channel_id(app.client, args.channel)
    if not chan_id:
        print(f"Channel '{args.channel}' not found or bot not a member. Invite the bot and add scopes channels:read, channels:history.", file=sys.stderr)
        sys.exit(2)

    # Start background polling thread (every N seconds)
    t = threading.Thread(target=poll_loop, args=(app, chan_id, args.interval, args.limit), daemon=True)
    t.start()

    # Start Socket Mode connection (keeps the process alive and ready for future event handlers)
    handler = SocketModeHandler(app, app_token)
    handler.start()

if __name__ == "__main__":
    main()