# LinkedIn Connection Automation

Automates LinkedIn connection requests from search results using Playwright. Connects to your existing Arc browser session — no credentials in code.

## Requirements

- Python 3.8+
- Arc browser
- LinkedIn account (logged in via Arc)

## Installation

```bash
cd linkedin-automation
pip install -r requirements.txt
```

## Setup

### 1. Launch Arc with remote debugging

Quit Arc completely first, then relaunch with the debug flag:

```bash
/Volumes/Arc/Arc.app/Contents/MacOS/Arc --remote-debugging-port=9222
```

**Tip**: Add this alias to your `~/.zshrc` for convenience:
```bash
alias arc-debug='/Volumes/Arc/Arc.app/Contents/MacOS/Arc --remote-debugging-port=9222'
```

### 2. Verify it's working

```bash
curl http://localhost:9222/json/version
```

Should return JSON with browser version info.

### 3. Log into LinkedIn

Open LinkedIn in Arc and make sure you're logged in.

### 4. Run the script

```bash
python linkedin_connect.py
```

## Configuration

Edit `config.py` to adjust:

| Setting | Default | Description |
|---------|---------|-------------|
| `SEARCH_URL` | (preset) | LinkedIn search URL with filters |
| `MAX_CONNECTIONS_PER_RUN` | 15 | Stop after this many connections |
| `DELAY_BETWEEN_CONNECTIONS` | 30-90s | Random delay between each request |
| `MAX_PAGES` | 10 | Max search result pages to process |

## Safety

- **CAPTCHA detection**: Script stops immediately if a CAPTCHA appears
- **Rate limit detection**: Stops on "exceeded limit" or "slow down" warnings
- **Randomized delays**: All waits are randomized (never fixed intervals)
- **Duplicate detection**: Checks CSV log before connecting — safe to re-run

## Logs

Connections are logged to `logs/connections.csv`:

```
timestamp,name,profile_url,status
2026-02-19T14:23:45,John Smith,https://linkedin.com/in/johnsmith,connected
```

## Troubleshooting

**"Cannot connect to Arc browser"**
- Make sure Arc is running with `--remote-debugging-port=9222`
- Check with: `curl http://localhost:9222/json/version`

**"No results found"**
- Verify you're logged into LinkedIn in Arc
- Try opening the search URL manually in Arc first

**Script stops immediately**
- Check if LinkedIn is showing a CAPTCHA or rate limit warning
- Wait a few hours before trying again

## Limitations

- LinkedIn's weekly connection limit is ~100-200 requests
- Automation violates LinkedIn's ToS — use at your own risk
- Selectors may break if LinkedIn updates their UI
