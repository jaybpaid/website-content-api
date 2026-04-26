# API Factory – Website Content API

## Status

**Built**:
- FastAPI wrapper (`main.py`) – receives URLs, calls Apify Website Content Crawler, returns LLM‑ready text chunks + metadata
- Dockerfile for containerized deployment
- Landing page (`index.html`) with pricing tiers
- `.env` with Apify token

**Blocked**:
- Apify API returning 401 on `/acts/apify~website-content-crawler/runs`. Token may lack permission to run public Actors.
- Need to either (a) create a private Actor in our account, or (b) use a different actor we own.

## Next Steps

| Step | Action |
|------|--------|
| 1 | **Debug token** – verify token has `actor:run` scope for public Actors, or create a private Actor |
| 2 | **Switch actor** – use `apify/web-scraper` (generic) or our own Actor |
| 3 | **Test endpoint** – confirm `/scrape` returns chunks |
| 4 | **Add x402** – integrate micropayments via mpp.best |
| 5 | **Deploy** – push to Railway / Hetzner |
| 6 | **Launch** – post on r/webscraping, Product Hunt, Discord |

## Quick Fix

Try the generic `apify/web-scraper` actor (ID: `apify~web-scraper`) which has lower usage limits but may work with our token.

```python
ACTOR_ID = "apify~web-scraper"
```

Or create a private Actor from a template:

```bash
apify create website-content-api --template website-content-crawler
```

## Files

- `main.py` – FastAPI entry point
- `requirements.txt` – Python dependencies
- `Dockerfile` – container definition
- `index.html` – landing page
- `.env` – API token (do not commit)