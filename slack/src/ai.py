"""
Pluggable "AI" hook.

If AI_SUMMARIZE_URL is set, POSTs {"messages":[...]} and expects:
- JSON with {"summary": "..."}  OR
- plain text (we'll return as-is)

If not set, returns a naive bullet list summary.
"""
from typing import List, Dict
import requests
from .config import AI_SUMMARIZE_URL, AI_SUMMARIZE_BEARER

def summarize(messages: List[Dict]) -> str:
    # messages: [{user, text, ts}, ...] oldest->newest

    # 1) Optional external AI HTTP hook
    if AI_SUMMARIZE_URL:
        headers = {"Content-Type": "application/json"}
        if AI_SUMMARIZE_BEARER:
            headers["Authorization"] = f"Bearer {AI_SUMMARIZE_BEARER}"
        try:
            resp = requests.post(AI_SUMMARIZE_URL, headers=headers, json={"messages": messages}, timeout=30)
            if resp.ok:
                try:
                    data = resp.json()
                    return data.get("summary") or data.get("text") or resp.text
                except Exception:
                    return resp.text
            else:
                return f"AI summarizer returned HTTP {resp.status_code}.\nFallback summary below:\n\n{_fallback(messages)}"
        except Exception as e:
            return f"AI summarizer error: {e}\n\nFallback summary below:\n\n{_fallback(messages)}"

    # 2) Fallback naive summary
    return _fallback(messages)

def _fallback(messages: List[Dict]) -> str:
    bullets = []
    for m in messages:
        text = (m.get("text") or "").strip()
        if not text:
            continue
        # truncate long lines
        if len(text) > 300:
            text = text[:297] + "..."
        bullets.append(f"- {text}")
    if not bullets:
        return "No recent human messages to summarize."
    return "Here’s a quick recap of the recent discussion:\n" + "\n".join(bullets[-30:])
