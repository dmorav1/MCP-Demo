import os
import sys
import time
import json
import ssl
import certifi
import argparse
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

import requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

def ts_to_str(ts: str) -> str:
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ts

def resolve_channel_id(client: WebClient, channel_name: str) -> Optional[str]:
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

def build_user_names(client: WebClient, user_ids: set[str]) -> dict[str, str]:
    names: dict[str, str] = {}
    for uid in user_ids:
        try:
            ui = client.users_info(user=uid)
            u = ui.get("user", {}) or {}
            names[uid] = u.get("real_name") or u.get("name") or uid
        except SlackApiError:
            names[uid] = uid
    return names

def build_ingest_payload(messages: List[Dict[str, Any]], channel_name: str, min_messages: int) -> Optional[Dict[str, Any]]:
    if not messages:
        return None

    # Oldest first
    msgs = sorted(messages, key=lambda m: float(m.get("ts", "0")))

    items: List[Dict[str, Any]] = []
    for m in msgs:
        text = (m.get("text") or "").strip()
        if not text:
            continue
        author_name = m.get("user_name") or m.get("username") or m.get("user") or "Unknown"
        author_type = "ai" if m.get("bot_id") else "human"
        ts_iso = datetime.fromtimestamp(float(m["ts"]), tz=timezone.utc).isoformat()
        items.append(
            {
                "author_name": author_name,
                "author_type": author_type,
                "content": text,
                "timestamp": ts_iso,
            }
        )

    if len(items) < min_messages:
        return None

    first_ts = float(msgs[0]["ts"])
    last_ts = float(msgs[-1]["ts"])
    first_time = datetime.fromtimestamp(first_ts, tz=timezone.utc)
    last_time = datetime.fromtimestamp(last_ts, tz=timezone.utc)

    return {
        "scenario_title": f"#{channel_name} conversation ({first_time.strftime('%Y-%m-%d %H:%M')} - {last_time.strftime('%H:%M')})",
        "original_title": f"Slack #{channel_name} - {first_time.strftime('%Y-%m-%d')}",
        "url": f"slack://channel/{channel_name}",
        "messages": items,  # expected by /ingest
    }

def load_state(state_file: str) -> Optional[str]:
    try:
        with open(state_file, "r") as f:
            obj = json.load(f)
            return obj.get("last_ts")
    except Exception:
        return None

def save_state(state_file: str, last_ts: str) -> None:
    try:
        with open(state_file, "w") as f:
            json.dump({"last_ts": last_ts}, f)
    except Exception:
        pass

def main():
    ap = argparse.ArgumentParser(description="Slack → /ingest poller")
    ap.add_argument("--channel", "-c", default=os.getenv("SLACK_CHANNEL", "warchan-ai"))
    ap.add_argument("--interval", "-i", type=int, default=int(os.getenv("SLACK_POLL_INTERVAL", "120")))
    ap.add_argument("--batch-size", "-b", type=int, default=int(os.getenv("SLACK_BATCH_SIZE", "20")))
    ap.add_argument("--min-messages", "-m", type=int, default=int(os.getenv("SLACK_MIN_MESSAGES", "3")))
    ap.add_argument("--state-file", "-s", default=os.getenv("SLACK_STATE_FILE", ".slack_ingest_state.json"))
    args = ap.parse_args()

    bot_token = os.getenv("SLACK_BOT_TOKEN", "")
    if not bot_token.startswith("xoxb-"):
        print("SLACK_BOT_TOKEN must be set (xoxb-...)", file=sys.stderr)
        sys.exit(1)

    base_url = os.getenv("FASTAPI_BASE_URL", "http://localhost:8000").rstrip("/")
    ingest_url = f"{base_url}/ingest"

    # Slack client with certifi to avoid macOS cert issues
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    client = WebClient(token=bot_token, ssl=ssl_context)

    chan_id = resolve_channel_id(client, args.channel)
    if not chan_id:
        print(f"Channel '{args.channel}' not found or bot not a member.", file=sys.stderr)
        sys.exit(2)

    last_ts = load_state(args.state_file)

    print(f"Slack ingest running. channel=#{args.channel}, interval={args.interval}s, ingest={ingest_url}", flush=True)

    while True:
        try:
            kw = {"channel": chan_id, "limit": 200}
            if last_ts:
                kw["oldest"] = last_ts
                kw["inclusive"] = False

            resp = client.conversations_history(**kw)
            messages = resp.get("messages", [])

            if messages:
                # Oldest first
                messages.sort(key=lambda m: float(m.get("ts", "0")))
                # Build user map
                user_ids = {m.get("user") for m in messages if m.get("user")}
                user_map = build_user_names(client, {u for u in user_ids if u})

                # Enrich and buffer
                buffer: List[Dict[str, Any]] = []
                for m in messages:
                    if m.get("subtype") or m.get("bot_id"):  # skip bot/system; adjust if you want bots
                        continue
                    m["user_name"] = user_map.get(m.get("user", ""), m.get("user", "Unknown"))
                    buffer.append(m)
                    ts_h = ts_to_str(m.get("ts", ""))
                    print(f"[{ts_h}] {m['user_name']}: {m.get('text','')}", flush=True)

                # Chunk into batches of batch_size
                def chunks(seq, size):
                    for i in range(0, len(seq), size):
                        yield seq[i : i + size]

                for chunk in chunks(buffer, args.batch_size):
                    payload = build_ingest_payload(chunk, args.channel, args.min_messages)
                    if not payload:
                        continue

                    r = requests.post(ingest_url, json=payload, timeout=30)
                    if r.status_code >= 400:
                        print(f"/ingest failed: {r.status_code} {r.text}", file=sys.stderr, flush=True)
                    else:
                        print(f"Ingested {len(payload['messages'])} messages → {ingest_url}", flush=True)

                last_ts = messages[-1]["ts"]
                save_state(args.state_file, last_ts)

        except SlackApiError as e:
            print(f"Slack API error: {e.response.get('error')}", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"Ingest loop error: {e}", file=sys.stderr, flush=True)

        time.sleep(args.interval)

if __name__ == "__main__":
    main()