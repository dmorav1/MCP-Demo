# Slack Channel Reader (Socket Mode, Docker)

Reads messages from Slack channels using Slack Bolt (Python) over **Socket Mode**. 
Optionally summarizes the last N messages when you mention the bot with `summarize`.

## What it does
- Logs every message (that humans post) in channels the bot is in.
- On `@your-bot summarize`, fetches the recent history for that channel and replies with a summary.
- Socket Mode = no public HTTPS endpoint required.

---

## 1) Create & configure your Slack App

1. Go to https://api.slack.com/apps → **Create New App** → From scratch.
2. **Basic Information → App-Level Tokens**  
   - Create a token with scope: `connections:write`.  
   - This is your **App Level Token** (starts with `xapp-`). You’ll set it as `SLACK_APP_TOKEN`.
3. **Socket Mode**  
   - Enable **Socket Mode**.
4. **OAuth & Permissions → Scopes (Bot Token Scopes)**  
   Add at least:
   - `app_mentions:read` (to catch @mentions)
   - `chat:write` (to reply)
   - `channels:read`, `channels:history` (public channels)
   - (Optional, if you need private channels) `groups:read`, `groups:history`
   - (Optional, for DMs/MPIMs) `im:history`, `mpim:history`
5. **Install App** to your workspace (top of OAuth & Permissions page).  
   - Grab your **Bot User OAuth Token** (starts with `xoxb-`). Set it as `SLACK_BOT_TOKEN`.
6. **Event Subscriptions**  
   - Toggle **Enable Events**.
   - Subscribe to events:
     - `app_mention`
     - `message.channels`
     - (Optional) `message.groups` if you’ll use private channels  
   - With Socket Mode enabled, you **don’t need** a Request URL.

> Invite your bot to any channel you want it to read: `/invite @YourBotName`

---

## 2) Configure environment

Copy the example env file and fill in your tokens:

```bash
cp .env.example .env
# edit .env and set SLACK_BOT_TOKEN + SLACK_APP_TOKEN at minimum
