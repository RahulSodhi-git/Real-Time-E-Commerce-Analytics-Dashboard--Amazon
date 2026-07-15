# Real-Time E-Commerce Analytics Dashboard — Amazon

Scrapes live product listings from **Amazon** across multiple categories using
**Playwright**, then serves the results in an interactive **Dash + Plotly**
dashboard that refreshes in the background — a real-time view of prices, ratings,
and product counts per category.

---

## What it does

1. **Scrape** — `scrape_amazon_products()` drives a headless Chromium browser
   (Playwright) over paginated Amazon search results, extracting product name,
   price, rating, and review count per category.
2. **Store** — results are collected into a pandas DataFrame and written to
   `amazon_master.xlsx`, timestamped on each run.
3. **Visualise** — a **Dash** app renders Plotly charts, with a background thread
   periodically re-scraping so the dashboard stays current.

---

## Getting started

```bash
pip install playwright pandas dash plotly openpyxl
playwright install chromium

python amazon_scrapper.py
```

The dashboard starts locally (default Dash port **8050**) → open
`http://127.0.0.1:8050`.

---

## Repository layout

```
amazon_scrapper.py     # Playwright scraper + Dash/Plotly dashboard
amazon_master.xlsx     # sample scraped output
```

---

## Notes

- Web scraping may be subject to a site's Terms of Service and is sensitive to
  markup changes — selectors may need updating over time. For educational use.
- The scraper launches a persistent browser profile directory on first run; that
  local profile is git-ignored.

---

## Tech stack

**Python** · **Playwright** · **Dash** · **Plotly** · **pandas**
