import os
import sys
import time
import json
import ssl
import certifi
import logging
import argparse
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

def _vprint(verbose: bool, msg: str) -> None:
    if verbose:
        logger.info(msg)

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
    ap.add_argument("--interval", "-i", type=int, default=int(os.getenv("SLACK_POLL_INTERVAL", "15")))
    ap.add_argument("--batch-size", "-b", type=int, default=int(os.getenv("SLACK_BATCH_SIZE", "20")))
    ap.add_argument("--min-messages", "-m", type=int, default=int(os.getenv("SLACK_MIN_MESSAGES", "1")))  # lower default
    ap.add_argument("--state-file", "-s", default=os.getenv("SLACK_STATE_FILE", ".slack_ingest_state.json"))
    ap.add_argument("--include-bots", action="store_true", default=os.getenv("SLACK_INCLUDE_BOTS", "false").lower() == "true")
    ap.add_argument("--verbose", "-v", action="store_true", default=os.getenv("SLACK_VERBOSE", "true").lower() == "true")
    args = ap.parse_args()

    bot_token = os.getenv("SLACK_BOT_TOKEN", "")
    if not bot_token.startswith("xoxb-"):
        print("SLACK_BOT_TOKEN must be set (xoxb-...)", file=sys.stderr)
        sys.exit(1)

    base_url = os.getenv("FASTAPI_BASE_URL", "http://localhost:8000").rstrip("/")
    ingest_url = f"{base_url}/ingest"

    _vprint(args.verbose, f"Config: channel=#{args.channel}, interval={args.interval}s, batch_size={args.batch_size}, min_messages={args.min_messages}, include_bots={args.include_bots}, state_file={args.state_file}, ingest_url={ingest_url}")

    # Slack client with certifi to avoid macOS cert issues
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    client = WebClient(token=bot_token, ssl=ssl_context)

    chan_id = resolve_channel_id(client, args.channel)
    _vprint(args.verbose, f"Resolved channel '{args.channel}' → id={chan_id}")
    if not chan_id:
        print(f"Channel '{args.channel}' not found or bot not a member.", file=sys.stderr)
        sys.exit(2)

    last_ts = load_state(args.state_file)
    _vprint(args.verbose, f"Loaded last_ts from state: {last_ts} ({ts_to_str(last_ts) if last_ts else 'n/a'})")
    print(f"Slack ingest running. channel=#{args.channel}, interval={args.interval}s, ingest={ingest_url}", flush=True)

    while True:
        try:
            # 1) Fetch messages (paginate)
            all_messages: List[Dict[str, Any]] = []
            cursor = None
            page_no = 0
            while True:
                kw = {"channel": chan_id, "limit": 200}
                if cursor:
                    kw["cursor"] = cursor
                if last_ts:
                    kw["oldest"] = last_ts
                    kw["inclusive"] = False
                page_no += 1
                _vprint(args.verbose, f"Requesting page #{page_no} conversations_history with params={kw}")
                resp = client.conversations_history(**kw)
                page_msgs = resp.get("messages", []) or []
                has_more = bool(resp.get("has_more"))
                cursor = resp.get("response_metadata", {}).get("next_cursor") or None
                _vprint(args.verbose, f"Page #{page_no} received: {len(page_msgs)} messages, has_more={has_more}, next_cursor={'set' if cursor else 'none'}")
                all_messages.extend(page_msgs)
                if not has_more or not cursor:
                    break

            print(f"Fetched {len(all_messages)} messages from Slack channel #{args.channel}", flush=True)

            if all_messages:
                # Oldest first
                all_messages.sort(key=lambda m: float(m.get("ts", "0")))

                # Build user map for display names
                user_ids = {m.get("user") for m in all_messages if m.get("user")}
                _vprint(args.verbose, f"Unique user ids in page: {len(user_ids)} → {sorted([u for u in user_ids if u])[:5]}{'...' if len(user_ids) > 5 else ''}")
                user_map = build_user_names(client, {u for u in user_ids if u})
                print(f"Resolved {len(user_map)} user names", flush=True)

                # Enrich and buffer (optionally include bots)
                buffer: List[Dict[str, Any]] = []
                skipped_bots = 0
                skipped_empty = 0
                for m in all_messages:
                    if not args.include_bots and (m.get("subtype") or m.get("bot_id")):
                        skipped_bots += 1
                        continue
                    text = (m.get("text") or "").strip()
                    if not text:
                        skipped_empty += 1
                        continue
                    m["user_name"] = user_map.get(m.get("user", ""), m.get("user", "Unknown"))
                    buffer.append(m)

                _vprint(args.verbose, f"Buffer built: total={len(all_messages)}, after_filter={len(buffer)}, skipped_bots={skipped_bots}, skipped_empty={skipped_empty}")
                if buffer[:2]:
                    for smp in buffer[:2]:
                        _vprint(args.verbose, f"Sample msg: ts={smp.get('ts')} user={smp.get('user_name')} text={smp.get('text')[:120]}")

                # Chunk into batches of batch_size
                def batches(seq, size):
                    for i in range(0, len(seq), size):
                        yield seq[i : i + size]

                ingested_any = False
                for idx, chunk in enumerate(batches(buffer, args.batch_size), start=1):
                    _vprint(args.verbose, f"Processing batch #{idx} size={len(chunk)}")
                    payload = build_ingest_payload(chunk, args.channel, args.min_messages)
                    if not payload:
                        _vprint(args.verbose, f"Batch #{idx} skipped: payload gated by min_messages (have={len(chunk)} < min={args.min_messages}) or empty after sanitization")
                        continue

                    # Print payload header preview
                    _vprint(args.verbose, f"Batch #{idx} payload: messages={len(payload['messages'])}, title='{payload['scenario_title']}', url={payload['url']}")
                    if payload["messages"][:2]:
                        for pi, pm in enumerate(payload["messages"][:2], start=1):
                            _vprint(args.verbose, f"  payload msg#{pi}: {pm['timestamp']} {pm['author_name']} [{pm['author_type']}] '{pm['content'][:120]}'")

                    try:
                        r = requests.post(ingest_url, json=payload, timeout=30)
                        _vprint(args.verbose, f"/ingest response: status={r.status_code}")
                        body = r.text
                        if len(body) > 400:
                            body = body[:400] + "...(truncated)"
                        _vprint(args.verbose, f"/ingest body: {body}")
                        if r.status_code >= 400:
                            print(f"/ingest failed: {r.status_code} {r.text}", file=sys.stderr, flush=True)
                        else:
                            ingested_any = True
                            print(f"Ingested {len(payload['messages'])} messages → {ingest_url}", flush=True)
                    except Exception as ex:
                        print(f"/ingest request error: {ex}", file=sys.stderr, flush=True)

                # Advance state and log last_ts
                if all_messages:
                    last_ts = all_messages[-1]["ts"]
                    save_state(args.state_file, last_ts)
                    _vprint(args.verbose, f"Saved state last_ts={last_ts} ({ts_to_str(last_ts)}) ingested_any={ingested_any}")

            else:
                _vprint(args.verbose, "No new messages in this interval")

        except SlackApiError as e:
            print(f"Slack API error: {e.response.get('error')}", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"Ingest loop error: {e}", file=sys.stderr, flush=True)

        time.sleep(args.interval)

if __name__ == "__main__":
    main()