#!/usr/bin/env python3
"""
post_digest.py — Posts the weekly competitor intel digest to Slack.

Reads /tmp/digest.json (written by the Claude agent after collecting Trendtrack data).
Ad thumbnails are served through images.weserv.nl (a free image proxy CDN) so the
hover/copy URL in Slack shows images.weserv.nl, not the original source.

Usage:
  SLACK_BOT_TOKEN=xoxb-... python3 post_digest.py [/path/to/digest.json]
"""

import json
import os
import subprocess
import sys
import urllib.parse
from datetime import datetime

DIGEST_PATH = sys.argv[1] if len(sys.argv) > 1 else "/tmp/digest.json"
TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")

if not TOKEN:
    print("ERROR: SLACK_BOT_TOKEN environment variable not set")
    sys.exit(1)


def proxy_image_url(original_url):
    """Wrap a thumbnail URL in the wsrv.nl proxy so the source CDN is hidden."""
    if not original_url:
        return None
    # Strip the scheme — wsrv.nl wants the URL without https://
    stripped = original_url.replace("https://", "").replace("http://", "")
    return f"https://images.weserv.nl/?url={urllib.parse.quote(stripped)}"


def build_fb_link(ad_id):
    clean_id = ad_id.replace("facebook_", "")
    return f"https://www.facebook.com/ads/library/?id={clean_id}"


def slack_post(channel, blocks, username="Skyro Intelligence", icon=":bar_chart:"):
    payload = {
        "channel": channel,
        "username": username,
        "icon_emoji": icon,
        "blocks": blocks
    }
    result = subprocess.run(
        ["curl", "-s", "-X", "POST", "https://slack.com/api/chat.postMessage",
         "-H", f"Authorization: Bearer {TOKEN}",
         "-H", "Content-Type: application/json",
         "-d", json.dumps(payload)],
        capture_output=True, text=True
    )
    return json.loads(result.stdout)


def post_client_digest(client, week_range):
    channel = client["slack_channel_id"]
    name = client["name"]
    competitors = client["competitors"]
    pattern = client.get("pattern_summary", "")
    skipped = client.get("skipped", [])

    active = [c for c in competitors if c.get("emails") or c.get("ads")]
    n_competitors = len(active)

    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"Competitor Intel -- Week of {week_range}"}},
        {"type": "context", "elements": [{"type": "mrkdwn", "text": f"Monitoring {n_competitors} competitor(s) for *{name}*"}]},
        {"type": "divider"}
    ]

    for comp in active:
        n_emails = len(comp.get("emails", []))
        n_ads = len(comp.get("ads", []))
        comp_domain = comp.get("domain", "")
        comp_name = comp.get("name", comp_domain)

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{comp_name}* -- {comp_domain}\n_{n_emails} email campaign(s) - {n_ads} active ad(s) this week_"
            }
        })

        # Email list
        emails = comp.get("emails", [])
        if emails:
            show = emails[:7]
            lines = []
            for e in show:
                subject = e.get("subject", "(no subject)")
                sent_day = e.get("sent_day", e.get("sent_at", ""))
                category = e.get("category", "")
                cat_label = "newsletter" if "newsletter" in category.lower() else "promo" if "promo" in category.lower() else "campaign"
                lines.append(f"- \"{subject}\" -- {sent_day} - {cat_label}")
            if len(emails) > 7:
                lines.append(f"_+ {len(emails) - 7} more emails this week_")
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Emails sent this week:*\n" + "\n".join(lines)}
            })

        # Ad sections — one per ad, with thumbnail inline as accessory image
        ads = comp.get("ads", [])
        for i, ad in enumerate(ads[:2], 1):
            body = ad.get("body", "") or ad.get("cta_description", "")
            if not body:
                continue

            if len(body) > 200:
                body = body[:200] + "..."

            days = ad.get("days_running", "?")
            reach = ad.get("reach_delta_7d", 0)
            reach_str = f"+{reach:,}" if reach else "n/a"
            cta = ad.get("cta", "")
            landing = ad.get("landing_path", ad.get("landing_page_url", ""))
            ad_label = "Top ad" if i == 1 else "2nd ad"
            media_label = " (video)" if ad.get("media_type") == "video" else ""
            fb_link = build_fb_link(ad.get("id", ""))

            text = (
                f"*{ad_label}*{media_label} (running {days} days - {reach_str} reach this week)\n"
                f"\"{body}\"\n"
                f"CTA: {cta}  |  Landing: {landing}\n"
                f"<{fb_link}|View ad on Facebook>"
            )

            thumbnail_url = ad.get("thumbnail_url", "")
            proxied = proxy_image_url(thumbnail_url)

            if proxied:
                blocks.append({
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": text},
                    "accessory": {"type": "image", "image_url": proxied, "alt_text": f"{comp_name} ad creative"}
                })
            else:
                blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": text}})

        blocks.append({"type": "divider"})

    # Pattern summary
    if pattern:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*:mag: This Week's Pattern*\n{pattern}"}
        })

    # Skipped log
    if skipped:
        skip_text = ", ".join(skipped)
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"_No data found for: {skip_text}_"}]
        })

    # Slack max 50 blocks — split if needed
    if len(blocks) > 50:
        first_chunk = blocks[:49] + [{"type": "divider"}]
        r1 = slack_post(channel, first_chunk)
        if not r1.get("ok"):
            return False, r1.get("error")
        r2 = slack_post(channel, blocks[49:])
        return r2.get("ok"), r2.get("error")

    r = slack_post(channel, blocks)
    return r.get("ok"), r.get("error")


def main():
    with open(DIGEST_PATH) as f:
        digest = json.load(f)

    week_range = digest.get("week_range", "this week")
    clients = digest.get("clients", [])

    total_clients = len(clients)
    successful_posts = 0
    total_emails = 0
    total_ads = 0
    all_skipped = []
    all_errors = []

    for client in clients:
        print(f"\nPosting digest for: {client['name']}")

        for comp in client.get("competitors", []):
            total_emails += len(comp.get("emails", []))
            total_ads += len(comp.get("ads", []))

        all_skipped.extend(client.get("skipped", []))

        ok, err = post_client_digest(client, week_range)
        if not ok:
            print(f"  ERROR: {err}")
            all_errors.append(f"{client['name']}: {err}")
            continue

        print(f"  Posted OK")
        successful_posts += 1

    now = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    print(f"\n{'='*50}")
    print(f"Run complete -- {now}")
    print(f"Clients processed: {total_clients}")
    print(f"Emails found: {total_emails}")
    print(f"Ads found: {total_ads}")
    print(f"Slack posts sent: {successful_posts} / {total_clients}")
    if all_skipped:
        print(f"Skipped (no data): {', '.join(all_skipped)}")
    print(f"Errors: {chr(10).join(all_errors) if all_errors else 'none'}")


if __name__ == "__main__":
    main()
