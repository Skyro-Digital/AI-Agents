"""LinkedIn connection automation using Playwright CDP."""

import csv
import os
import random
import sys
import time
from datetime import datetime

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from config import (
    CDP_URL,
    DELAY_AFTER_PAGINATION,
    DELAY_BETWEEN_ACTIONS,
    DELAY_BETWEEN_CONNECTIONS,
    LOG_FILE,
    MAX_CONNECTIONS_PER_RUN,
    MAX_PAGES,
    SEARCH_URL,
)


def random_delay(delay_range):
    """Sleep for a random duration within the given (min, max) range."""
    delay = random.uniform(*delay_range)
    print(f"  Waiting {delay:.0f}s...")
    time.sleep(delay)


def load_existing_connections():
    """Load previously connected profile URLs from CSV."""
    connected = set()
    if not os.path.exists(LOG_FILE):
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "name", "profile_url", "status"])
        return connected

    with open(LOG_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            connected.add(row["profile_url"])
    return connected


def log_connection(name, profile_url, status):
    """Append a connection record to the CSV log."""
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now().isoformat(), name, profile_url, status])


def detect_safety_issues(page):
    """Check for CAPTCHAs or rate limit warnings. Returns (has_issue, reason)."""
    captcha_selectors = [
        'iframe[title*="recaptcha"]',
        'iframe[src*="captcha"]',
        '#captcha-internal',
    ]
    for selector in captcha_selectors:
        if page.locator(selector).count() > 0:
            return True, "CAPTCHA detected"

    page_text = page.locator("body").inner_text()
    warning_phrases = [
        "you've reached the weekly invitation limit",
        "you've exceeded",
        "try again later",
        "unusual activity",
    ]
    lower_text = page_text.lower()
    for phrase in warning_phrases:
        if phrase in lower_text:
            return True, f"Warning detected: '{phrase}'"

    return False, ""


def get_profiles_on_page(page):
    """Extract profile data from the current search results page using JS.

    LinkedIn uses both <button> and <a> tags for action buttons (Connect, Pending, etc).
    Connect buttons are often <a> tags with aria-label="Invite ... to connect".

    Returns list of dicts: {name, url, button_text, aria_label}
    """
    return page.evaluate("""() => {
        const profiles = [];

        // Find ALL clickable action elements (both buttons and links)
        const actionEls = Array.from(document.querySelectorAll('button, a'));

        for (const el of actionEls) {
            const text = el.textContent.trim();
            const ariaLabel = el.getAttribute('aria-label') || '';

            // Identify the action type
            let actionType = null;
            if (text === 'Connect' || ariaLabel.startsWith('Invite ') && ariaLabel.endsWith(' to connect')) {
                actionType = 'Connect';
            } else if (text === 'Pending') {
                actionType = 'Pending';
            } else if (text === 'Follow') {
                actionType = 'Follow';
            } else if (text === 'Message') {
                actionType = 'Message';
            }

            if (!actionType) continue;

            // Walk up the DOM to find a container with a profile link
            let container = el.parentElement;
            let profileLink = null;
            let attempts = 0;
            while (container && attempts < 15) {
                profileLink = container.querySelector('a[href*="/in/"]');
                if (profileLink) break;
                container = container.parentElement;
                attempts++;
            }

            if (!profileLink) continue;

            const rawUrl = profileLink.href.split('?')[0].replace(/\\/$/, '');
            const name = ariaLabel.replace('Invite ', '').replace(' to connect', '')
                || profileLink.textContent.trim().split('\\n')[0].trim()
                || 'Unknown';

            profiles.push({
                name: name,
                url: rawUrl,
                button_text: actionType,
                aria_label: ariaLabel
            });
        }

        // Deduplicate by URL (keep first occurrence)
        const seen = new Set();
        return profiles.filter(p => {
            if (seen.has(p.url)) return false;
            seen.add(p.url);
            return true;
        });
    }""")


def click_connect_button(page, aria_label):
    """Click a Connect button by its aria-label, then handle the modal."""
    try:
        # Find the Connect element (could be <a> or <button>)
        btn = page.locator(f'[aria-label="{aria_label}"]').first
        if btn.count() == 0:
            print(f"  Could not find element with aria-label: {aria_label}")
            return False

        btn.scroll_into_view_if_needed()
        time.sleep(1)
        btn.evaluate("el => el.click()")
        time.sleep(3)

        # Check if a modal appeared
        modal = page.locator('div[role="dialog"]')
        if modal.count() == 0:
            # Sometimes LinkedIn sends connection directly without a modal
            print("  No modal appeared — checking if connected directly...")
            time.sleep(2)
            # Re-check for modal
            if page.locator('div[role="dialog"]').count() == 0:
                print("  Connected directly (no modal)")
                return True

        # Try "Send without a note" first
        send_without = modal.locator('button:has-text("Send without a note")')
        if send_without.count() > 0:
            send_without.click()
            time.sleep(2)
            return True

        # Try "Send now" or "Send"
        send_btn = modal.locator('button[aria-label="Send now"]')
        if send_btn.count() == 0:
            send_btn = modal.locator('button:has-text("Send")')
        if send_btn.count() > 0:
            send_btn.first.click()
            time.sleep(2)
            return True

        # Check if it's an "email required" modal — dismiss and skip
        email_input = modal.locator('input[type="email"], input[name="email"]')
        if email_input.count() > 0:
            print("  Email required to connect — skipping")
            dismiss = modal.locator('button[aria-label="Dismiss"], button:has-text("Cancel")')
            if dismiss.count() > 0:
                dismiss.first.click()
            return False

        # Debug: print what buttons are in the modal
        modal_buttons = modal.locator("button").all_inner_texts()
        print(f"  Unknown modal buttons: {modal_buttons}")
        dismiss = modal.locator('button[aria-label="Dismiss"], button:has-text("Cancel")')
        if dismiss.count() > 0:
            dismiss.first.click()
        return False

    except PlaywrightTimeout:
        print("  Timeout — skipping")
        try:
            dismiss = page.locator('button[aria-label="Dismiss"], button:has-text("Cancel")')
            if dismiss.count() > 0:
                dismiss.first.click()
        except Exception:
            pass
        return False
    except Exception as e:
        print(f"  Error: {e}")
        return False


def process_page(page, existing_connections, connection_count):
    """Process all search results on the current page."""
    profiles = get_profiles_on_page(page)
    connect_profiles = [p for p in profiles if p["button_text"] == "Connect"]
    other_profiles = [p for p in profiles if p["button_text"] != "Connect"]

    print(f"\nFound {len(profiles)} profiles ({len(connect_profiles)} with Connect button)")
    for p in other_profiles:
        print(f"  {p['name'][:30]} — {p['button_text']}")

    for profile in connect_profiles:
        if connection_count >= MAX_CONNECTIONS_PER_RUN:
            print(f"\nReached max connections ({MAX_CONNECTIONS_PER_RUN}). Stopping.")
            return connection_count

        # Safety check
        has_issue, reason = detect_safety_issues(page)
        if has_issue:
            print(f"\nSAFETY STOP: {reason}")
            sys.exit(1)

        name = profile["name"][:50]
        url = profile["url"]

        print(f"\n[{connection_count + 1}/{MAX_CONNECTIONS_PER_RUN}] {name}")
        print(f"  {url}")

        if url in existing_connections:
            print("  Already contacted — skipping")
            continue

        success = click_connect_button(page, profile["aria_label"])
        if success:
            connection_count += 1
            print(f"  Connected!")
            log_connection(name, url, "connected")
            existing_connections.add(url)
            random_delay(DELAY_BETWEEN_CONNECTIONS)
        else:
            print("  Failed to connect")
            log_connection(name, url, "error")

    return connection_count


def paginate(page):
    """Navigate to the next page of results."""
    try:
        next_btn = page.locator('button[data-testid="pagination-controls-next-button-visible"]')
        if next_btn.count() == 0:
            return False

        # Use JS click to bypass overlay elements
        next_btn.evaluate("el => el.click()")
        page.wait_for_load_state("domcontentloaded")
        time.sleep(8)
        random_delay(DELAY_AFTER_PAGINATION)
        return True
    except Exception as e:
        print(f"  Pagination error: {e}")
        return False


def main():
    print("LinkedIn Connection Automation")
    print("=" * 40)

    existing_connections = load_existing_connections()
    print(f"Loaded {len(existing_connections)} existing connections from log")

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.connect_over_cdp(CDP_URL)
        except Exception as e:
            print(f"\nERROR: Cannot connect to Arc browser.")
            print(f"Make sure Arc is running with remote debugging:")
            print(f"  /Volumes/Arc/Arc.app/Contents/MacOS/Arc --remote-debugging-port=9222")
            print(f"\nDetails: {e}")
            sys.exit(1)

        # Find an existing LinkedIn tab, or use the first available tab
        context = browser.contexts[0]
        page = None
        for p in context.pages:
            if "linkedin.com" in p.url:
                page = p
                print(f"  Using existing LinkedIn tab: {p.url[:60]}")
                break
        if page is None:
            if context.pages:
                page = context.pages[0]
                print(f"  No LinkedIn tab found, using: {page.url[:60]}")
            else:
                print("\nERROR: No open tabs found in Arc.")
                sys.exit(1)

        print(f"\nNavigating to search URL...")
        page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=60000)
        time.sleep(10)  # Let LinkedIn's JS render results

        print(f"  Current URL: {page.url}")

        # Check for login redirect
        if "login" in page.url or "checkpoint" in page.url:
            print("\nERROR: LinkedIn is asking you to log in. Log into LinkedIn in Arc first.")
            sys.exit(1)

        # Safety check
        has_issue, reason = detect_safety_issues(page)
        if has_issue:
            print(f"\nSAFETY STOP: {reason}")
            sys.exit(1)

        connection_count = 0
        page_num = 1

        while page_num <= MAX_PAGES and connection_count < MAX_CONNECTIONS_PER_RUN:
            print(f"\n--- Page {page_num} ---")
            connection_count = process_page(page, existing_connections, connection_count)

            if connection_count >= MAX_CONNECTIONS_PER_RUN:
                break

            if not paginate(page):
                print("\nNo more pages.")
                break

            page_num += 1

        print(f"\n{'=' * 40}")
        print(f"Done! Sent {connection_count} connection requests.")
        print(f"Log saved to {LOG_FILE}")


if __name__ == "__main__":
    main()
