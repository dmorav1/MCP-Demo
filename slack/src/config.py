import os

def _get(name: str, default=None, required=False):
    val = os.getenv(name, default)
    if required and (val is None or str(val).strip() == ""):
        raise RuntimeError(f"Missing required env var: {name}")
    return val

SLACK_BOT_TOKEN = _get("SLACK_BOT_TOKEN", required=True)
SLACK_APP_TOKEN = _get("SLACK_APP_TOKEN", required=True)

SUMMARY_WINDOW = int(_get("SUMMARY_WINDOW", 50))
BOT_DEBUG = str(_get("BOT_DEBUG", "false")).lower() == "true"

AI_SUMMARIZE_URL = _get("AI_SUMMARIZE_URL", None)
AI_SUMMARIZE_BEARER = _get("AI_SUMMARIZE_BEARER", None)
