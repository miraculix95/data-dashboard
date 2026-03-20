# data-dashboard

Streamlit multi-page dashboard with password protection, GitHub trend analysis, and AI-generated reports.

## Tech stack

Python, Streamlit, pandas, seaborn, matplotlib, fpdf2, openrouter API

## Pages

- **Home** — welcome screen
- **GitHub Trending** — top repos from the last 7 days via GitHub Search API, bar chart + data table, AI summary, PDF export

## Features

- Password-protected (via `st.secrets`)
- Data cached for 1 week, manual refresh button
- AI Summary: fetches README context for each repo, generates a trend analysis via OpenRouter LLM
- PDF export: AI summary + repo table with clickable GitHub links, README-based descriptions, credits footer
- Configurable model via `config.yaml` (Gemini, GPT-4o, Claude, DeepSeek, Grok, ...)
- Prompt template in `prompts/github_summary.md` — edit without touching code

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

Create `devhub/.env` (shared key store):

```env
OPENROUTER_API_KEY=your-key
```

## Configuration

Edit `config.yaml` to change LLM model, cache TTL, number of repos, output language:

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
```

## Prompt customization

Edit `prompts/github_summary.md` directly to change the analysis style, language, focus areas, or output format. Available placeholders: `{repo_list}`, `{lang_instruction}`, `{date}`.

## Production start (VPS)

```bash
cd devhub/data-dashboard
nohup .venv/bin/streamlit run app.py --server.port 8501 --server.headless true > streamlit.log 2>&1 &
```

Logs: `devhub/data-dashboard/streamlit.log`

## Version history

### v1.2 — 2026-03-20
- AI Summary: README-based context (2000 chars per repo) instead of GitHub description
- PDF table: clickable repo links, multi-line description column with text wrapping
- PDF footer with generation credits (model, date, source)
- Prompt extracted to `prompts/github_summary.md` for easy customization
- Unicode sanitizer for PDF output (handles Grok/Gemini special chars)

### v1.1 — 2026-03-20
- AI Summary feature via OpenRouter (configurable model)
- PDF export of AI summary + repo table
- README context fetching per repo via GitHub API
- `config.yaml` for model selection and settings
- Manual refresh button, cache TTL set to 1 week

### v1.0 — 2026-03-18
- Initial release
- GitHub Trending page: bar chart + data table
- Password protection via st.secrets
- Deployed at dashboard.ai-devhub-247.site
