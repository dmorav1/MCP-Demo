import os, time, hmac, hashlib, json, requests

SIGNING_SECRET = os.environ["SLACK_SIGNING_SECRET"]  # same as your .env
url = "http://localhost:3000/slack/events"

def sign(body: str, ts: str) -> str:
    base = f"v0:{ts}:{body}".encode()
    digest = hmac.new(SIGNING_SECRET.encode(), base, hashlib.sha256).hexdigest()
    return "v0=" + digest

def post(payload: dict):
    ts = str(int(time.time()))
    body = json.dumps(payload, separators=(",", ":"))
    headers = {
        "Content-Type": "application/json",
        "X-Slack-Request-Timestamp": ts,
        "X-Slack-Signature": sign(body, ts),
    }
    r = requests.post(url, headers=headers, data=body)
    print(r.status_code, r.text)

if __name__ == "__main__":
    # 1) URL verification simulation
    post({"type": "https://slack.com/api/conversations.list", "challenge": "test-challenge"})

    # 2) Event callback simulation
    post({
        "type": "event_callback",
        "event": {
            "type": "message",
            "user": "Jose",
            "text": "hello: This is a test message from post_signed_event.py",
            "channel": "warchan-ai",
        }
    })