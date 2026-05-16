# Weekly Competitor Intelligence Digest

You are running Skyro Digital's weekly competitor intelligence automation. Your job is to pull the past week's competitor email campaigns and Meta ads for each client, then post a polished digest to their Slack channel.

**Today's context**: Run every Monday. The digest covers the previous 7 days of competitor activity.

---

## Step 1 — Read the client list

Read the file at `/Users/maxalderman/AI Agents - Max/trendtrack-intelligence/clients.json`.

This file contains all active clients and their competitors. Process every client in the list.

---

## Step 2 — For each client, fetch competitor data

For each client, loop through their competitors. For each competitor domain:

### Emails (campaigns only — no flows)
Make **one call** to `search_emails`:

`search_emails(shop="<domain>", timeframe="7d", intent="all", limit=10)`

From the results, **exclude** any email where:
- `classification.event.name` is "Abandoned Cart" or "Welcome"
- or the intent classification is `abandoned_cart` or `welcome`

Keep everything else — product campaigns, promotional campaigns, newsletters, etc.

**Skip and log** if 0 emails remain after filtering — write a note "No campaign emails found for [Brand]" but continue processing.

### Ads (active Meta ads)
Call `brief_competitor(competitor="<domain>", sections=["ads"], max_ads=5)`

This returns the top 5 active Meta ads for the competitor, ranked by recent reach growth.

**Skip and log** if a competitor returns 0 ads — write a note "No active ads found for [Brand]" but continue processing.

### If a domain can't be resolved at all
If Trendtrack returns an error or empty result for a domain, log "Could not resolve [Brand] ([domain]) — skipping" and move on. Never crash or stop processing other clients.

---

## Step 3 — Write the pattern summary

After collecting all data for a client's competitors, write a 2–4 sentence summary paragraph analyzing what patterns you're seeing across all of them that week. Look for:

- Common offer types (discounts, free shipping, bundles, urgency)
- Dominant messaging angles (education, social proof, fear, aspiration)
- Ad creative trends (video vs image, short vs long copy, UGC)
- Any brand that went unusually quiet or suddenly ramped up

Keep this analytical and useful — this is what turns raw data into strategic intelligence for the client.

**Framing**: Write as if you're Skyro Digital's in-house analyst. No mention of Trendtrack, no mention of data tools. Sound like a human expert who monitors competitors closely.

---

## Step 4 — Format the Slack message

Build a JSON payload for the Slack API. Use this structure for each client:

```json
{
  "channel": "<client.slack_channel_id>",
  "username": "Skyro Intelligence",
  "icon_emoji": ":bar_chart:",
  "blocks": [
    {
      "type": "header",
      "text": {
        "type": "plain_text",
        "text": "Competitor Intel — Week of [Mon date] – [Sun date]"
      }
    },
    {
      "type": "context",
      "elements": [
        {
          "type": "mrkdwn",
          "text": "Monitoring [N] competitor(s) for [Client Name]"
        }
      ]
    },
    {
      "type": "divider"
    },
    ... one section per competitor (see format below) ...
    {
      "type": "divider"
    },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*:mag: This Week's Pattern*\n[2–4 sentence summary from Step 3]"
      }
    }
  ]
}
```

### Per-competitor section format

For each competitor, build these blocks:

**Competitor header:**
```json
{
  "type": "section",
  "text": {
    "type": "mrkdwn",
    "text": "*[Competitor Name]* — [domain]\n_[N] email campaign(s) · [N] active ad(s) this week_"
  }
}
```

**Emails block** (if any emails found):
```json
{
  "type": "section",
  "text": {
    "type": "mrkdwn",
    "text": "*Emails sent this week:*\n• \"[Subject Line]\" — [Day, Month Date] · [promo / newsletter]\n• \"[Subject Line]\" — [Day, Month Date] · [promo / newsletter]\n..."
  }
}
```

Only include up to 7 emails in the message. If there are more, add a line: "_+ [N] more emails this week_"

**Top ad block** (if any ads found — show top 2 by reach growth):
For each ad, include:
```json
{
  "type": "section",
  "text": {
    "type": "mrkdwn",
    "text": "*Top ad* (running [N] days · +[reachDelta7d] reach this week)\n\"[First 200 chars of ad copy body...]\"\n→ CTA: [callToAction] · Landing: [path of landingPageUrl only, not full domain]"
  },
  "accessory": {
    "type": "image",
    "image_url": "[thumbnailUrl]",
    "alt_text": "[Competitor Name] ad"
  }
}
```

If the ad has no copy body, use the `ctaDescription` field instead. If both are empty, skip the ad.

**Divider between competitors:**
```json
{ "type": "divider" }
```

---

## Step 5 — Post to Slack

For each client, post using the Slack API via bash:

```bash
curl -s -X POST https://slack.com/api/chat.postMessage \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '<JSON payload>'
```

The `SLACK_BOT_TOKEN` environment variable holds the bot token (starts with `xoxb-`).

Check the response. If `"ok": true` — success. If `"ok": false` — log the error message and continue to the next client. Never stop the whole run because one client's post failed.

**Slack block limit**: Slack allows max 50 blocks per message. If a client has many competitors and would exceed 50 blocks, split into two messages for that client: first message covers competitors, second message covers the pattern summary.

---

## Step 6 — Log a run summary

After processing all clients, output a brief run summary:

```
✅ Run complete — [timestamp]
Clients processed: [N]
Competitors checked: [N]
Emails found: [N total across all]
Ads found: [N total across all]
Slack posts sent: [N successful] / [N attempted]
Skipped (no data): [list any competitor domains with no results]
Errors: [list any failures]
```

---

## Rules

- **Never mention Trendtrack** in any Slack message. The data should appear to come from Skyro Digital's own monitoring.
- **Never crash** — if any individual competitor or client fails, log it and move to the next one.
- **Skip empty sections** — if a competitor had 0 campaign emails, don't show the emails section for them. Just show ads (and vice versa). If a competitor had 0 of both, skip them entirely and log it.
- **Keep copy excerpts short** — truncate ad copy to 200 characters max in Slack messages. The goal is signal, not a full transcript.
- **Date format**: Use "Mon May 5" style (no year) for email sent dates. Use "May 5–11" style for the digest header date range.
