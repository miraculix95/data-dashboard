# data-dashboard

Streamlit multi-page dashboard with AI-powered analysis, curated news feed, and PDF reporting.

Live: [dashboard.ai-devhub-247.site](https://dashboard.ai-devhub-247.site)

## Pages

- **Home** — welcome screen
- **GitHub Trending** — top repos by stars, AI summary, PDF export with appendix, watchlist
- **Watchlist** — saved repos with management
- **AI News** — top AI articles from HackerNews, The Decoder, VentureBeat — LLM-curated

## Tech stack

Python, Streamlit, pandas, seaborn, matplotlib, fpdf2, OpenRouter API, Firecrawl

## Features

- Password-protected via `st.secrets`
- **GitHub Trending**: language dropdown (20 languages), time filter (24h/7d/30d), repo limit slider
- **AI Summary**: fetches README context (2000 chars/repo), generates trend analysis + per-repo summaries via OpenRouter LLM
- **PDF export**: AI analysis + repo table with clickable links + appendix with 5–8 sentence per-repo descriptions
- **Telegram send**: PDF directly to chat via button (no manual download)
- **Watchlist**: mark repos from the trending feed, persisted as JSON
- **AI News**: Firecrawl scrapes The Decoder + VentureBeat, HackerNews via public API — LLM filters top 8 articles with summaries, 4h cache
- Configurable model via `config.yaml` (Gemini, GPT-4o, Claude, Grok, DeepSeek, ...)
- Prompt templates in `prompts/` — edit without touching code

## Run locally

```bash
uv venv .venv
uv pip install pandas seaborn matplotlib streamlit requests pyyaml python-dotenv fpdf2
streamlit run app.py
```

## Environment variables

Create `.streamlit/secrets.toml`:

```toml
password = "your-password"
```

Create `devhub/.env`:

```env
OPENROUTER_API_KEY=your-key
FIRECRAWL_API_KEY=your-key   # required for AI News page
```

## Configuration

`config.yaml`:

```yaml
llm:
  model: google/gemini-2.0-flash-001   # or gpt-4o, claude-sonnet-4-5, grok-3-mini, ...
  max_tokens: 5000

github:
  cache_ttl_seconds: 604800   # 1 week
  default_limit: 10

summary:
  top_n: 10
  language: de   # de or en

news:
  cache_ttl_seconds: 14400   # 4 hours
  top_n: 8
  language: de
  sources:
    hackernews: true
    the_decoder: true
    venturebeat: true
```

## Production start (VPS)

```bash
cd devhub/data-dashboard
nohup .venv/bin/streamlit run app.py --server.port 8501 --server.headless true > streamlit.log 2>&1 &
```

## Version history

### v1.5 — 2026-03-20
- AI News page: HackerNews (API) + The Decoder + VentureBeat (Firecrawl) — LLM-curated feed
- `FIRECRAWL_API_KEY` added as dependency for news scraping

### v1.4 — 2026-03-20
- Language filter: dropdown with 20 languages
- Time filter: 24h / 7 Tage / 30 Tage radio buttons
- Telegram send button: PDF directly to chat
- Watchlist: multiselect + dedicated Watchlist page

### v1.3 — 2026-03-20
- Per-repo detail summaries (5–8 sentences) as PDF appendix
- Clickable repo headings in appendix

### v1.2 — 2026-03-20
- README-based context (2000 chars per repo) for better AI analysis
- PDF table: clickable links, multi-line description with text wrapping
- PDF footer with generation credits
- Prompt extracted to `prompts/github_summary.md`
- Unicode sanitizer for PDF output

### v1.1 — 2026-03-20
- AI Summary via OpenRouter (configurable model)
- PDF export of AI summary + repo table
- `config.yaml` for model selection and settings
- Manual refresh button, 1-week cache

### v1.0 — 2026-03-18
- Initial release: GitHub Trending page with bar chart + data table
- Password protection, deployed at dashboard.ai-devhub-247.site
