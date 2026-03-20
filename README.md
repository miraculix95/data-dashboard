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

## Production start (VPS)

The app runs as a background process on port 8501, proxied through Caddy.

```bash
cd devhub/data-dashboard
nohup .venv/bin/streamlit run app.py --server.port 8501 --server.headless true > streamlit.log 2>&1 &
```

The process does **not** survive server reboots automatically. To restart after a reboot, run the command above manually — or set up a systemd service if permanent persistence is needed.

Current PID and log location are tracked in `devhub/docs/running-services.md`.

Logs: `devhub/data-dashboard/streamlit.log`
