import os
import sys
import time
import ssl
import certifi
import argparse
import threading
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.errors import SlackApiError

# Fix the Python path to find the app module
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '../../..')
sys.path.insert(0, project_root)

# Now import app modules
from app.database import SessionLocal
from app import schemas, crud
from app.logging_config import setup_logging, get_logger

# Set up logging
setup_logging("INFO")
logger = get_logger(__name__)

class SlackConversationProcessor:
    """
    Processes Slack messages into conversation format for database ingestion
    """
    
    def __init__(self, db_session, batch_size: int = 20, min_messages: int = 3):
        self.db = db_session
        self.batch_size = batch_size
        self.min_messages = min_messages
        self.conversation_crud = crud.ConversationCRUD(db_session)
    
    def format_message_for_ingestion(self, messages: List[Dict], channel_name: str) -> schemas.ConversationIngest:
        """
        Convert Slack messages to ConversationIngest format expected by /ingest
        (scenario_title, original_title, url, messages=[{author_name, author_type, content, timestamp}])
        """
        if not messages:
            raise ValueError("No messages to process")

        # Sort by ts (oldest first)
        sorted_messages = sorted(messages, key=lambda m: float(m.get("ts", "0")))

        first_ts = float(sorted_messages[0]["ts"])
        last_ts = float(sorted_messages[-1]["ts"])
        first_time = datetime.fromtimestamp(first_ts, tz=timezone.utc)
        last_time = datetime.fromtimestamp(last_ts, tz=timezone.utc)

        scenario_title = f"#{channel_name} conversation ({first_time.strftime('%Y-%m-%d %H:%M')} - {last_time.strftime('%H:%M')})"
        original_title = f"Slack #{channel_name} - {first_time.strftime('%Y-%m-%d')}"

        items: List[Dict[str, Any]] = []
        for msg in sorted_messages:
            text = (msg.get("text") or "").strip()
            if not text:
                continue
            # Prefer resolved user_name added in the poll loop
            user_name = msg.get("user_name") or msg.get("username") or msg.get("user") or "Unknown"
            is_bot = bool(msg.get("bot_id"))
            author_type = "ai" if is_bot else "human"
            ts_iso = datetime.fromtimestamp(float(msg["ts"]), tz=timezone.utc).isoformat()

            items.append(
                {
                    "author_name": user_name,
                    "author_type": author_type,
                    "content": text,
                    "timestamp": ts_iso,
                }
            )

        if len(items) < self.min_messages:
            raise ValueError(f"Not enough meaningful messages ({len(items)} < {self.min_messages})")

        return schemas.ConversationIngest(
            scenario_title=scenario_title,
            original_title=original_title,
            url=f"slack://channel/{channel_name}",
            messages=items,  # <- correct field
        )

    def process_messages_batch(self, messages: List[Dict], channel_name: str) -> bool:
        """
        Process a batch synchronously using existing CRUD that expects ConversationIngest
        """
        try:
            conversation_data = self.format_message_for_ingestion(messages, channel_name)
            # Your CRUD should already accept the schema produced by /ingest
            db_conversation = self.conversation_crud.create_conversation_sync(conversation_data)
            logger.info(f"✅ Ingested conversation ID: {db_conversation.id} - {conversation_data.scenario_title}")
            return True
        except ValueError as ve:
            logger.warning(f"⚠️ Skipping batch: {ve}")
            return False
        except Exception as e:
            logger.error(f"❌ Error processing batch: {str(e)}")
            return False

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

def ingest_loop(app: App, channel_id: str, channel_name: str, interval_sec: int, batch_size: int, min_messages: int):
    """
    Periodically fetch messages and process them for ingestion (synchronous)
    """
    last_ts: str | None = None
    ssl_ctx = ssl.create_default_context(cafile=certifi.where())
    client = app.client.__class__(token=app.client.token, ssl=ssl_ctx)
    
    message_buffer = []
    
    while True:
        try:
            # Create new DB session for each batch
            db = SessionLocal()
            processor = SlackConversationProcessor(db, batch_size, min_messages)
            
            kw = {"channel": channel_id, "limit": 100}
            if last_ts:
                kw["oldest"] = last_ts
                kw["inclusive"] = False
            
            resp = client.conversations_history(**kw)
            messages = resp.get("messages", [])
            
            if messages:
                # Sort messages oldest first
                messages = sorted(messages, key=lambda m: float(m.get("ts", "0")))
                
                # Get user names
                user_ids = {m.get("user") for m in messages if m.get("user")}
                user_map = build_user_names(client, {u for u in user_ids if u})
                
                # Process messages
                for msg in messages:
                    # Skip bot messages and system messages
                    if msg.get("subtype") or msg.get("bot_id"):
                        continue
                    
                    # Add user name to message
                    msg["user_name"] = user_map.get(msg.get("user", ""), msg.get("user", "Unknown"))
                    message_buffer.append(msg)
                    
                    # Log the message
                    ts = ts_to_str(msg.get("ts", ""))
                    user_name = msg["user_name"]
                    text = msg.get("text", "")
                    logger.info(f"[{ts}] {user_name}: {text}")
                
                # Process buffer when it reaches batch size
                if len(message_buffer) >= batch_size:
                    batch_to_process = message_buffer[:batch_size]
                    message_buffer = message_buffer[batch_size:]
                    
                    # Call synchronous method
                    success = processor.process_messages_batch(batch_to_process, channel_name)
                    if success:
                        logger.info(f"📦 Processed batch of {len(batch_to_process)} messages")
                
                last_ts = messages[-1]["ts"]
            
            db.close()
            
        except SlackApiError as e:
            logger.error(f"Slack API error: {e.response.get('error')}")
        except Exception as e:
            logger.error(f"Error in ingest loop: {e}")
        
        time.sleep(interval_sec)

def main():
    ap = argparse.ArgumentParser(description="Slack to Database Ingest Processor (Socket Mode)")
    ap.add_argument("--channel", "-c", default="warchan-ai", help="Channel name (e.g., warchan-ai)")
    ap.add_argument("--interval", "-i", type=int, default=300, help="Processing interval seconds (default: 5 min)")
    ap.add_argument("--batch-size", "-b", type=int, default=20, help="Messages per conversation batch")
    ap.add_argument("--min-messages", "-m", type=int, default=3, help="Minimum messages to create conversation")
    args = ap.parse_args()

    bot_token = os.getenv("SLACK_BOT_TOKEN", "")
    app_token = os.getenv("SLACK_APP_TOKEN", "")
    
    if not bot_token or not app_token:
        logger.error("Set SLACK_BOT_TOKEN (xoxb-...) and SLACK_APP_TOKEN (xapp-...) in env.")
        sys.exit(1)
    
    if not bot_token.startswith("xoxb-"):
        logger.error("SLACK_BOT_TOKEN must start with xoxb- (bot token).")
        sys.exit(1)
    
    if not app_token.startswith("xapp-"):
        logger.error("SLACK_APP_TOKEN must start with xapp- (App-Level token with connections:write).")
        sys.exit(1)

    # Create Bolt app (Socket Mode)
    app = App(token=bot_token)
    
    # Add minimal event handlers to prevent "Unhandled request" logs
    @app.event("message")
    def handle_message_events(event, logger):
        # Just acknowledge, processing is done in the ingest loop
        pass
    
    @app.event("app_mention")
    def handle_app_mention(event, logger):
        logger.info(f"[mention] user={event.get('user')} text={event.get('text')}")

    # Resolve channel ID before starting
    chan_id = resolve_channel_id(app.client, args.channel)
    if not chan_id:
        logger.error(f"Channel '{args.channel}' not found or bot not a member. Invite the bot and add scopes channels:read, channels:history.")
        sys.exit(2)

    logger.info(f"🚀 Starting Slack ingest processor for #{args.channel}")
    logger.info(f"   - Batch size: {args.batch_size} messages")
    logger.info(f"   - Min messages: {args.min_messages}")
    logger.info(f"   - Interval: {args.interval} seconds")

    # Start background ingest thread
    ingest_thread = threading.Thread(
        target=ingest_loop, 
        args=(app, chan_id, args.channel, args.interval, args.batch_size, args.min_messages), 
        daemon=True
    )
    ingest_thread.start()

    # Start Socket Mode connection (keeps process alive)
    handler = SocketModeHandler(app, app_token)
    logger.info("🔌 Socket Mode connection started")
    handler.start()

if __name__ == "__main__":
    main()