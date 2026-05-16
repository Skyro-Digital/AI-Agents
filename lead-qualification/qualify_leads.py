import sys
import re
import time
import argparse
import urllib.parse
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from playwright.sync_api import sync_playwright


def parse_args():
    parser = argparse.ArgumentParser(description="Qualify e-commerce lead list")
    parser.add_argument("file", help="Path to CSV or XLSX lead list")
    parser.add_argument("--output-dir", help="Directory for output files (default: same as input)")
    return parser.parse_args()


def load_leads(file_path):
    path = Path(file_path)
    if not path.exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)
    if path.suffix.lower() == ".xlsx":
        return pd.read_excel(path)
    elif path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    else:
        print(f"Error: Unsupported file format: {path.suffix}")
        sys.exit(1)


def detect_columns(df):
    """Fuzzy-match column names for brand name, URL, and optional email."""
    brand_candidates = ["brand", "brand name", "company", "company name", "name", "store", "store name"]
    url_candidates = ["url", "website url", "website", "domain", "site", "web", "link"]
    email_candidates = ["email", "email address", "e-mail", "e-mail address"]

    cols_lower = {col.lower().strip(): col for col in df.columns}

    brand_col = next((cols_lower[c] for c in brand_candidates if c in cols_lower), None)
    url_col = next((cols_lower[c] for c in url_candidates if c in cols_lower), None)
    email_col = next((cols_lower[c] for c in email_candidates if c in cols_lower), None)

    if not brand_col or not url_col:
        print(f"Columns found: {list(df.columns)}")
        print("Error: Could not detect brand name and URL columns.")
        print("Expected names like: 'brand', 'name', 'url', 'website', 'domain'")
        sys.exit(1)

    return brand_col, url_col, email_col


def domain_from_email(email):
    """Extract domain from email address, ignoring common free providers."""
    if not email or not isinstance(email, str):
        return None
    email = email.strip().lower()
    if "@" not in email:
        return None
    domain = email.split("@")[-1]
    # Skip generic providers — not useful for site health check
    free_providers = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
                      "icloud.com", "aol.com", "protonmail.com", "me.com"}
    if domain in free_providers:
        return None
    return domain


def extract_domain(url):
    """Strip protocol, www, paths — return clean domain."""
    if not url or not isinstance(url, str):
        return None
    url = url.strip()
    if not url.startswith("http"):
        url = "https://" + url
    try:
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.lower().replace("www.", "")
        return domain or None
    except Exception:
        return None


def normalize_url(url):
    if not url or not isinstance(url, str):
        return None
    url = url.strip()
    return url if url.startswith("http") else "https://" + url


def check_site_health(url):
    """Returns True if site is reachable, False if dead."""
    url = normalize_url(url)
    if not url:
        return False
    try:
        resp = requests.get(
            url, timeout=10, allow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        )
        return resp.status_code < 400
    except Exception:
        return False


def scrape_meta_ads(brand_name, page):
    """
    Check Meta Ads Library for active ads.
    Returns "PASS" | "FAIL" | "UNKNOWN"
    """
    try:
        query = urllib.parse.quote(brand_name)
        url = f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&q={query}"
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(7000)

        text = page.evaluate("() => document.body.innerText")

        # No-results phrases — Facebook shows these in local language
        no_result_phrases = [
            "no ads match",
            "no hay ningún anuncio",       # Spanish
            "keine anzeigen",              # German
            "aucune publicité",            # French
        ]
        if any(phrase in text.lower() for phrase in no_result_phrases):
            return "FAIL"

        # Result count pattern — "~2.400 resultados" or "~1,200 results"
        if re.search(r"~?\d[\d.,]*\s*(?:resultados?|results?|anuncios?|ads?)", text, re.I):
            return "PASS"

        return "UNKNOWN"

    except Exception:
        return "UNKNOWN"


def decide(meta_result):
    if meta_result == "PASS":
        return "QUALIFIED"
    if meta_result == "FAIL":
        return "REMOVED"
    return "UNCERTAIN"


def print_progress(i, total, brand_name, status, detail):
    pct = (i / total) * 100
    print(f"[{i:3d}/{total}] ({pct:5.1f}%) {brand_name[:38]:<38} → {status:<10} [{detail}]")


def save_outputs(df, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    qualified = df[df["qualification_status"].isin(["QUALIFIED", "UNCERTAIN"])].copy()
    removed = df[df["qualification_status"] == "REMOVED"].copy()

    q_path = output_dir / "qualified_leads.csv"
    r_path = output_dir / "removed_leads.csv"
    qualified.to_csv(q_path, index=False)
    removed.to_csv(r_path, index=False)

    return q_path, r_path


def print_summary(df, q_path, elapsed):
    total = len(df)
    qualified = (df["qualification_status"] == "QUALIFIED").sum()
    uncertain = (df["qualification_status"] == "UNCERTAIN").sum()
    removed = (df["qualification_status"] == "REMOVED").sum()
    removed_no_ads = ((df["qualification_status"] == "REMOVED") & (df["removal_reason"] == "No active ads")).sum()
    removed_dead = ((df["qualification_status"] == "REMOVED") & (df["removal_reason"] == "Site offline")).sum()
    removed_invalid = ((df["qualification_status"] == "REMOVED") & (df["removal_reason"] == "Invalid URL")).sum()

    mins, secs = divmod(int(elapsed), 60)
    date_str = datetime.now().strftime("%Y-%m-%d")

    print(f"\nLead Qualification Complete — {date_str}")
    print("─" * 47)
    print(f"Total leads processed:   {total:4d}")
    print(f"Qualified (running ads): {qualified:4d}  ({qualified/total*100:.1f}%)")
    print(f"Uncertain (kept):        {uncertain:4d}  ({uncertain/total*100:.1f}%)")
    print(f"Removed:                 {removed:4d}  ({removed/total*100:.1f}%)")
    if removed_no_ads > 0:
        print(f"  └─ No active ads:      {removed_no_ads:4d}")
    if removed_dead > 0:
        print(f"  └─ Site offline:       {removed_dead:4d}")
    if removed_invalid > 0:
        print(f"  └─ Invalid URL:        {removed_invalid:4d}")
    print("─" * 47)
    print(f"Time taken: {mins}m {secs}s")
    print(f"Output: {q_path}")


def main():
    args = parse_args()
    df = load_leads(args.file)
    brand_col, url_col, email_col = detect_columns(df)

    print(f"Loaded {len(df)} leads from {args.file}")
    print(f"Columns: brand='{brand_col}', url='{url_col}'" + (f", email='{email_col}'" if email_col else ""))

    df["meta_ads_result"] = "UNKNOWN"
    df["qualification_status"] = "UNCERTAIN"
    df["removal_reason"] = ""

    # --- Pass 1: Group all rows by email domain ---
    # All contacts sharing a domain belong to the same company.
    # We qualify once per unique domain, then propagate to all contacts.
    company_groups = {}  # {email_domain: {"name": str|None, "url": str|None, "indices": [int]}}
    solo_rows = []       # (idx, brand_name, url) — has brand name but no email domain
    empty_indices = []   # rows with no brand name and no usable email

    for idx, row in df.iterrows():
        brand_name = str(row[brand_col]).strip()
        raw_url = row[url_col]
        url = str(raw_url).strip() if pd.notna(raw_url) else ""
        if url.lower() in ("nan", "none"):
            url = ""
        email = str(row[email_col]).strip() if email_col and pd.notna(row[email_col]) else ""
        email_domain = domain_from_email(email)
        is_blank = brand_name.lower() in ("nan", "", "none")

        if email_domain:
            if email_domain not in company_groups:
                company_groups[email_domain] = {"name": None, "url": None, "indices": []}
            company_groups[email_domain]["indices"].append(idx)
            if not is_blank and company_groups[email_domain]["name"] is None:
                company_groups[email_domain]["name"] = brand_name
            if url and company_groups[email_domain]["url"] is None:
                company_groups[email_domain]["url"] = url
        elif not is_blank:
            solo_rows.append((idx, brand_name, url))
        else:
            empty_indices.append(idx)

    # Mark truly empty rows immediately
    for idx in empty_indices:
        df.at[idx, "qualification_status"] = "REMOVED"
        df.at[idx, "removal_reason"] = "No brand name"

    total_unique = len(company_groups) + len(solo_rows)
    est_mins = max(1, total_unique * 10 // 60)
    print(f"Unique companies to check: {total_unique} (~{est_mins} min)")
    print(f"Total contacts (rows):     {len(df)}")
    print(f"Empty rows (skipped):      {len(empty_indices)}\n")

    start_time = time.time()
    i = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()

        # --- Pass 2a: Qualify each company group ---
        for domain, group in company_groups.items():
            i += 1
            name = group["name"] or domain
            url = group["url"] or f"https://{domain}"
            indices = group["indices"]

            if not check_site_health(url):
                meta_result, status, reason = "UNKNOWN", "REMOVED", "Site offline"
            else:
                meta_result = scrape_meta_ads(name, page)
                time.sleep(1.5)
                status = decide(meta_result)
                reason = "No active ads" if status == "REMOVED" else ""

            for idx in indices:
                df.at[idx, "meta_ads_result"] = meta_result
                df.at[idx, "qualification_status"] = status
                df.at[idx, "removal_reason"] = reason

            pct = (i / total_unique) * 100
            contacts = len(indices)
            print(f"[{i:3d}/{total_unique}] ({pct:5.1f}%) {name[:35]:<35} → {status:<10} [Ads:{meta_result}] ({contacts} contact{'s' if contacts > 1 else ''})")

        # --- Pass 2b: Solo rows (brand name but no email domain) ---
        for idx, brand_name, url in solo_rows:
            i += 1
            if url and not check_site_health(url):
                meta_result, status, reason = "UNKNOWN", "REMOVED", "Site offline"
            else:
                meta_result = scrape_meta_ads(brand_name, page)
                time.sleep(1.5)
                status = decide(meta_result)
                reason = "No active ads" if status == "REMOVED" else ""

            df.at[idx, "meta_ads_result"] = meta_result
            df.at[idx, "qualification_status"] = status
            df.at[idx, "removal_reason"] = reason

            pct = (i / total_unique) * 100
            print(f"[{i:3d}/{total_unique}] ({pct:5.1f}%) {brand_name[:35]:<35} → {status:<10} [Ads:{meta_result}]")

        browser.close()

    elapsed = time.time() - start_time
    output_dir = args.output_dir or str(Path(args.file).parent)
    q_path, _ = save_outputs(df, output_dir)
    print_summary(df, q_path, elapsed)


if __name__ == "__main__":
    main()
