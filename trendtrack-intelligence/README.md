# Trendtrack Competitor Intelligence

Runs every Monday morning. For each active client, pulls the past week's competitor email campaigns and Meta ads from Trendtrack, then posts a digest to their Slack channel as "Skyro Intelligence."

---

## Files

| File | What it is | How often you edit it |
|---|---|---|
| `clients.json` | Client list with competitors and Slack channel IDs | Frequently — when adding/removing clients or competitors |
| `prompt.md` | Instructions the AI agent follows each run | Rarely — only to change tone, format, or what's included |
| `post_digest.py` | Python script that posts the digest to Slack | Never — it's infrastructure |

**How it works**: The agent (Claude) calls Trendtrack to collect competitor data, writes it to `/tmp/digest.json`, then runs `post_digest.py` to post everything to Slack. The Python script downloads all ad thumbnails from Trendtrack and re-uploads them to Slack's CDN so no external data source URLs are ever visible in the messages.

---

## One-time setup

### 1. Create the Skyro Intelligence Slack bot

1. Go to [api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → **From scratch**
2. App name: `Skyro Intelligence` | Pick your Skyro Digital Slack workspace
3. In the left sidebar → **OAuth & Permissions** → scroll to **Scopes** → **Bot Token Scopes**
4. Add these three scopes: `chat:write`, `chat:write.customize`, `chat:write.public`
5. Scroll up → **Install to Workspace** → Authorize
6. Copy the **Bot User OAuth Token** (starts with `xoxb-...`)

### 2. Store the bot token in Claude Code

Ask Claude: *"Add SLACK_BOT_TOKEN=xoxb-[your token] to my Claude Code environment variables"*

### 3. For private Slack channels

If any client channel is private, invite the bot once:
1. Open the channel in Slack
2. Type `/invite @Skyro Intelligence`

---

## Adding a new client

1. Open `clients.json`
2. Copy an existing client block and paste it at the end of the `clients` array
3. Fill in:
   - `id`: a short slug like `primal-remedies` (no spaces, lowercase)
   - `name`: full client name as you want it to appear in Slack
   - `slack_channel_id`: the channel ID (see below)
   - `competitors`: list of competitor brands with their domains

**How to find a Slack channel ID:**
Right-click the channel name in Slack → **Copy Link**. The URL ends in `/C1234567890` — that last part (starting with `C`) is the ID.

**How to find a competitor's domain:**
Ask Claude: *"Look up [Brand Name] on Trendtrack and tell me their domain"* — Claude will use the `lookup` tool to find it.

---

## Removing a client

Delete their entire block from `clients.json` (from `{` to the matching `}`).

---

## Changing what's in the digest

Edit `prompt.md`. The file is written in plain English — you can change:
- How many emails to show per competitor (search for `limit=7`)
- How many ads to show (search for `max_ads=5`)
- The tone of the pattern summary (find the "Framing" section)
- What to include or skip

---

## Running it manually

Ask Claude: *"Run the Trendtrack weekly competitor intelligence digest"* and paste in the contents of `prompt.md`, or use the scheduled command if set up.

---

## Credit usage

- ~17 Trendtrack credits per competitor per run
- 90 competitors (30 clients × 3) = ~1,530 credits/week
- Monthly estimate: ~6,100 credits (plan includes 10,000)

Check remaining credits anytime: ask Claude *"Check my Trendtrack credits"*
