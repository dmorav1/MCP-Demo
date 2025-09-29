import pytest
from datetime import datetime, timezone
from app.slack.tools.slack_ingest_processor import build_ingest_payload

def _mk(ts: float, text="hi", user="U1", bot=False):
    return {
        "ts": str(ts),
        "text": text,
        "user": user,
        "bot_id": "B1" if bot else None,
    }

def test_build_ingest_payload_min_messages_gate():
    now = datetime.now(tz=timezone.utc).timestamp()
    msgs = [_mk(now - 10, "a"), _mk(now - 5, "b")]
    assert build_ingest_payload(msgs, "warchan-ai", min_messages=3) is None

def test_build_ingest_payload_happy_path_sorted_times():
    t1 = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc).timestamp()
    t2 = datetime(2024, 1, 1, 12, 1, tzinfo=timezone.utc).timestamp()
    payload = build_ingest_payload([_mk(t2, "b"), _mk(t1, "a")], "warchan-ai", min_messages=1)
    assert payload is not None
    assert payload["messages"][0]["content"] == "a"
    assert payload["messages"][1]["content"] == "b"
    assert payload["scenario_title"].startswith("#warchan-ai conversation (2024-01-01")
    assert payload["url"] == "slack://channel/warchan-ai"