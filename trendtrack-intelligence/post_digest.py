#!/usr/bin/env python3
"""
post_digest.py — Posts the weekly competitor intel digest to Slack.

Reads /tmp/digest.json (written by the Claude agent after collecting Trendtrack data),
then for each client:
  - Uploads all ad thumbnails to Slack (so no Trendtrack CDN URLs are exposed)
  - Posts the structured Block Kit message (emails + ad copy text)
  - Posts each ad creative as a Slack file share (thumbnail + initial_comment)

Usage:
  SLACK_BOT_TOKEN=xoxb-... python3 post_digest.py [/path/to/digest.json]
"""

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime

DIGEST_PATH = sys.argv[1] if len(sys.argv) > 1 else "/tmp/digest.json"
TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")

if not TOKEN:
    print("ERROR: SLACK_BOT_TOKEN environment variable not set")
    sys.exit(1)


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


def upload_thumbnail(thumbnail_url, filename, title, channel, comment):
    """Download thumbnail from Trendtrack and upload to Slack. Returns ok/error."""
    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    tmp.close()

    # Download
    dl = subprocess.run(
        ["curl", "-s", "-L", "-o", tmp.name, thumbnail_url],
        capture_output=True
    )
    if dl.returncode != 0:
        os.unlink(tmp.name)
        return False, f"download failed (curl {dl.returncode})"

    size = os.path.getsize(tmp.name)
    if size == 0:
        os.unlink(tmp.name)
        return False, "downloaded file is empty"

    # Get upload URL
    url_result = subprocess.run(
        ["curl", "-s", "https://slack.com/api/files.getUploadURLExternal",
         "-H", f"Authorization: Bearer {TOKEN}",
         "-G",
         "--data-urlencode", f"filename={filename}",
         "--data-urlencode", f"length={size}"],
        capture_output=True, text=True
    )
    url_data = json.loads(url_result.stdout)
    if not url_data.get("ok"):
        os.unlink(tmp.name)
        return False, f"getUploadURLExternal: {url_data.get('error')}"

    upload_url = url_data["upload_url"]
    file_id = url_data["file_id"]

    # Upload (302 is normal/expected response from Slack's upload endpoint)
    subprocess.run(
        ["curl", "-s", "-X", "PUT", upload_url,
         "-H", "Content-Type: image/jpeg",
         "--data-binary", f"@{tmp.name}"],
        capture_output=True
    )
    os.unlink(tmp.name)

    # Complete upload and post to channel
    complete_payload = {
        "files": [{"id": file_id, "title": title}],
        "channel_id": channel,
        "initial_comment": comment
    }
    complete_result = subprocess.run(
        ["curl", "-s", "-X", "POST", "https://slack.com/api/files.completeUploadExternal",
         "-H", f"Authorization: Bearer {TOKEN}",
         "-H", "Content-Type: application/json",
         "-d", json.dumps(complete_payload)],
        capture_output=True, text=True
    )
    complete_data = json.loads(complete_result.stdout)
    if complete_data.get("ok"):
        return True, None
    return False, complete_data.get("error", "unknown")


def build_fb_link(ad_id):
    clean_id = ad_id.replace("facebook_", "")
    return f"https://www.facebook.com/ads/library/?id={clean_id}"


def post_client_digest(client, week_range):
    channel = client["slack_channel_id"]
    name = client["name"]
    competitors = client["competitors"]
    pattern = client.get("pattern_summary", "")
    skipped = client.get("skipped", [])

    # Count active competitors (those with at least emails or ads)
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

        # Emails block
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

        # Ads text block (copy + CTA — no thumbnail here, thumbnails posted separately)
        ads = comp.get("ads", [])
        if ads:
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
                text = f"*{ad_label}*{media_label} (running {days} days - {reach_str} reach this week)\n\"{body}\"\nCTA: {cta}  |  Landing: {landing}\n<{fb_link}|View ad on Facebook>"
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
    else:
        r = slack_post(channel, blocks)
        return r.get("ok"), r.get("error")


def post_ad_creatives(client, week_range):
    """Upload ad thumbnails as Slack file shares for each competitor."""
    channel = client["slack_channel_id"]
    errors = []
    uploaded = 0

    for comp in client["competitors"]:
        ads = comp.get("ads", [])
        for i, ad in enumerate(ads[:2], 1):
            thumbnail_url = ad.get("thumbnail_url", "")
            if not thumbnail_url:
                continue

            ad_id = ad.get("id", "")
            comp_name = comp.get("name", comp.get("domain", ""))
            days = ad.get("days_running", "?")
            reach = ad.get("reach_delta_7d", 0)
            reach_str = f"+{reach:,}" if reach else "n/a"
            media_label = "Video ad" if ad.get("media_type") == "video" else "Image ad"
            body = ad.get("body", "") or ad.get("cta_description", "")
            if len(body) > 200:
                body = body[:200] + "..."
            cta = ad.get("cta", "")
            landing = ad.get("landing_path", ad.get("landing_page_url", ""))
            fb_link = build_fb_link(ad_id)

            comment = (
                f"*{comp_name}* -- {media_label} "
                f"(running {days} days - {reach_str} reach this week)\n"
                f"\"{body}\"\n"
                f"CTA: {cta}  |  Landing: {landing}\n"
                f"View full ad: {fb_link}"
            )

            filename = f"{comp.get('domain', 'ad').replace('.', '_')}_ad_{i}.jpg"
            title = f"{comp_name} - {media_label} #{i} ({week_range})"

            ok, err = upload_thumbnail(thumbnail_url, filename, title, channel, comment)
            if ok:
                uploaded += 1
            else:
                errors.append(f"{comp_name} ad {i}: {err}")

    return uploaded, errors


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

        # Count totals
        for comp in client.get("competitors", []):
            total_emails += len(comp.get("emails", []))
            total_ads += len(comp.get("ads", []))

        all_skipped.extend(client.get("skipped", []))

        # Post main text digest
        ok, err = post_client_digest(client, week_range)
        if not ok:
            print(f"  ERROR posting text digest: {err}")
            all_errors.append(f"{client['name']} text: {err}")
            continue

        print(f"  Text digest posted OK")

        # Post ad creatives as file uploads
        uploaded, thumb_errors = post_ad_creatives(client, week_range)
        print(f"  Ad creatives uploaded: {uploaded}")
        if thumb_errors:
            print(f"  Thumbnail errors: {thumb_errors}")
            all_errors.extend(thumb_errors)

        successful_posts += 1

    # Run summary
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    print(f"\n{'='*50}")
    print(f"Run complete -- {now}")
    print(f"Clients processed: {total_clients}")
    print(f"Emails found: {total_emails}")
    print(f"Ads found: {total_ads}")
    print(f"Slack posts sent: {successful_posts} / {total_clients}")
    if all_skipped:
        print(f"Skipped (no data): {', '.join(all_skipped)}")
    if all_errors:
        print(f"Errors: {chr(10).join(all_errors)}")
    else:
        print("Errors: none")


if __name__ == "__main__":
    main()
