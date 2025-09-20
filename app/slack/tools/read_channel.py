import os
import sys
import argparse
from datetime import datetime, timezone
import ssl
import certifi
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

def ts_to_str(ts: str) -> str:
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ts

def get_channel_id(client: WebClient, name: str) -> str | None:
    name = name.lstrip("#").lower()
    cursor = None
    while True:
        resp = client.conversations_list(
            types="public_channel,private_channel",
            limit=1000,
            cursor=cursor
        )
        for ch in resp.get("channels", []):
            # ch["name"] is lower-case
            if ch.get("name", "").lower() == name:
                return ch["id"]
        cursor = resp.get("response_metadata", {}).get("next_cursor") or None
        if not cursor:
            break
    return None

def build_user_map(client: WebClient, user_ids: set[str]) -> dict[str, str]:
    names: dict[str, str] = {}
    for uid in user_ids:
        try:
            ui = client.users_info(user=uid)
            profile = ui.get("user", {})
            names[uid] = profile.get("real_name") or profile.get("name") or uid
        except SlackApiError:
            names[uid] = uid
    return names

def is_channel_id(value: str) -> bool:
    # Slack channel IDs start with C (public) or G (private), then alphanum
    return isinstance(value, str) and len(value) >= 9 and value[0] in ("C", "G")

def main():
    ap = argparse.ArgumentParser(description="Read recent Slack channel messages")
    ap.add_argument("--channel", "-c", default="warchan-ai", help="Channel name or ID (e.g., warchan-ai or C0123456)")
    ap.add_argument("--limit", "-n", type=int, default=20, help="Number of messages to fetch")
    ap.add_argument("--token", help="Slack bot token (xoxb-...). If not set, reads SLACK_BOT_TOKEN env")
    args = ap.parse_args()

    token = args.token or os.getenv("SLACK_BOT_TOKEN")
    if not token:
        print("Missing SLACK_BOT_TOKEN (xoxb-...). Export it or pass --token.", file=sys.stderr)
        sys.exit(1)

    # Use certifi CA bundle to avoid macOS cert issues
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    client = WebClient(token=token, ssl=ssl_context)

    try:
        if is_channel_id(args.channel):
            chan_id = args.channel
        else:
            chan_id = get_channel_id(client, args.channel)

        if not chan_id:
            print(f"Channel '{args.channel}' not found or bot not a member.", file=sys.stderr)
            print("Ensure scopes: channels:read, channels:history (and groups:read/history if private).", file=sys.stderr)
            print("Invite the bot: /invite @YourBot", file=sys.stderr)
            sys.exit(2)

        hist = client.conversations_history(channel=chan_id, limit=args.limit)
        msgs = hist.get("messages", [])
        user_ids = {m.get("user") for m in msgs if m.get("user")}
        user_map = build_user_map(client, {u for u in user_ids if u})

        print(f"# {args.channel} (last {len(msgs)} messages)")
        for m in reversed(msgs):
            ts = ts_to_str(m.get("ts", ""))
            user = user_map.get(m.get("user") or "", m.get("username") or "bot")
            text = m.get("text", "")
            print(f"[{ts}] {user}: {text}")

    except SlackApiError as e:
        err = e.response.get("error")
        print(f"Slack API error: {err}", file=sys.stderr)
        if err == "not_in_channel":
            print("Invite the bot to the channel first: /invite @YourBot", file=sys.stderr)
        elif err == "missing_scope":
            print("Add scopes: channels:read, channels:history (+ groups:read, groups:history for private). Reinstall the app.", file=sys.stderr)
        elif err == "invalid_auth" or err == "not_authed":
            print("Use a valid bot token (xoxb-...). Export SLACK_BOT_TOKEN or pass --token.", file=sys.stderr)
        sys.exit(3)

if __name__ == "__main__":
    main()