# data-dashboard

Streamlit multi-page dashboard with password protection.

## Tech stack

Python, Streamlit, pandas, seaborn, matplotlib

## Pages

- **Home** — welcome screen
- **GitHub Trending** — top repos from the last 7 days via GitHub Search API, bar chart + data table

## Run locally

```bash
uv venv .venv
uv pip install pandas seaborn matplotlib streamlit requests
streamlit run app.py
```

## Environment

Create `.streamlit/secrets.toml`:

```toml
password = "your-password"
```
