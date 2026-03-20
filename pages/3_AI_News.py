import os
import re
import yaml
import json
import requests
import streamlit as st
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"
with open(CONFIG_PATH) as f:
    CONFIG = yaml.safe_load(f)

NEWS_CFG = CONFIG["news"]
LLM_CFG = CONFIG["llm"]
TTL = NEWS_CFG["cache_ttl_seconds"]


def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        st.error("Wrong password")
        return False
    return True


if not check_password():
    st.stop()

st.set_page_config(page_title="AI News", page_icon="📰", layout="wide")
st.title("📰 AI News")
st.caption("Top AI-Artikel aus HackerNews, The Decoder und VentureBeat — gefiltert und zusammengefasst.")

col_r, col_info = st.columns([1, 5])
with col_r:
    if st.button("🔄 Refresh", help="Cache leeren und neu laden"):
        st.cache_data.clear()
        st.rerun()
with col_info:
    ttl_h = TTL // 3600
    st.caption(f"Wird alle {ttl_h} Stunden aktualisiert.")


def _firecrawl_scrape(url: str, max_chars: int = 8000) -> str:
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        return ""
    try:
        resp = requests.post(
            "https://api.firecrawl.dev/v1/scrape",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"url": url, "formats": ["markdown"]},
            timeout=30,
        )
        resp.raise_for_status()
        md = resp.json().get("data", {}).get("markdown", "")
        return md[:max_chars]
    except Exception:
        return ""


@st.cache_data(ttl=TTL)
def fetch_hackernews(min_score: int = 100, limit: int = 20) -> list[dict]:
    """Fetch top HackerNews stories filtered by min score."""
    try:
        top_ids = requests.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json", timeout=10
        ).json()[:50]
        stories = []
        for sid in top_ids:
            item = requests.get(
                f"https://hacker-news.firebaseio.com/v0/item/{sid}.json", timeout=5
            ).json()
            if item and item.get("score", 0) >= min_score and item.get("url"):
                stories.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "score": item.get("score", 0),
                    "comments": item.get("descendants", 0),
                    "source": "HackerNews",
                })
            if len(stories) >= limit:
                break
        return stories
    except Exception:
        return []


@st.cache_data(ttl=TTL)
def fetch_the_decoder() -> list[dict]:
    """Scrape The Decoder main page and extract article links."""
    md = _firecrawl_scrape("https://the-decoder.de", max_chars=12000)
    if not md:
        return []
    articles = []
    # Extract markdown links: [Title](URL)
    for m in re.finditer(r'\[([^\]]{20,120})\]\((https://the-decoder\.de/[^\)]+)\)', md):
        title, url = m.group(1).strip(), m.group(2).strip()
        if "/author/" in url or "/tag/" in url or "/category/" in url:
            continue
        if any(a["url"] == url for a in articles):
            continue
        articles.append({"title": title, "url": url, "score": 0, "comments": 0, "source": "The Decoder"})
        if len(articles) >= 15:
            break
    return articles


@st.cache_data(ttl=TTL)
def fetch_venturebeat() -> list[dict]:
    """Scrape VentureBeat AI section."""
    md = _firecrawl_scrape("https://venturebeat.com/category/ai/", max_chars=12000)
    if not md:
        return []
    articles = []
    for m in re.finditer(r'\[([^\]]{20,120})\]\((https://venturebeat\.com/[^\)]+)\)', md):
        title, url = m.group(1).strip(), m.group(2).strip()
        if any(skip in url for skip in ["/author/", "/tag/", "/category/", "page/"]):
            continue
        if any(a["url"] == url for a in articles):
            continue
        articles.append({"title": title, "url": url, "score": 0, "comments": 0, "source": "VentureBeat"})
        if len(articles) >= 15:
            break
    return articles


def _llm_filter_and_summarize(articles: list[dict], top_n: int, language: str, model: str) -> list[dict]:
    """Send article list to LLM — returns filtered + annotated list."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return articles[:top_n]

    lang_instruction = "Antworte auf Deutsch." if language == "de" else "Answer in English."
    today = datetime.now(timezone.utc).strftime("%d.%m.%Y")

    article_list = "\n".join(
        f"{i+1}. [{a['source']}] {a['title']} — {a['url']}"
        + (f" (Score: {a['score']})" if a["score"] else "")
        for i, a in enumerate(articles)
    )

    prompt = f"""Du bist ein KI-Redakteur. Heute ist der {today}.

{lang_instruction}

Hier sind aktuelle Artikel aus KI/Tech-Medien:

{article_list}

Wähle die {top_n} relevantesten Artikel aus — Fokus auf AI, LLMs, Open Source, Dev-Tools. Keine Business-Floskeln, keine reinen Finanzierungs-News, keine Clickbait-Titel.

Antworte AUSSCHLIESSLICH als JSON-Array, kein Text davor oder danach:

[
  {{
    "title": "Originaltitel",
    "url": "https://...",
    "source": "HackerNews|The Decoder|VentureBeat",
    "summary": "2-3 Saetze: Was ist die Kerninformation? Warum relevant?"
  }}
]"""

    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://dashboard.ai-devhub-247.site",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2000,
                "temperature": 0.3,
            },
            timeout=60,
        )
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"].strip()
        # Strip markdown code block if present
        raw = re.sub(r"^```(?:json)?\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
        return json.loads(raw)
    except Exception:
        return [{"title": a["title"], "url": a["url"], "source": a["source"], "summary": ""} for a in articles[:top_n]]


# --- Fetch all sources ---
all_articles = []

if NEWS_CFG["sources"].get("hackernews"):
    with st.spinner("HackerNews..."):
        hn = fetch_hackernews()
        all_articles.extend(hn)

if NEWS_CFG["sources"].get("the_decoder"):
    with st.spinner("The Decoder..."):
        td = fetch_the_decoder()
        all_articles.extend(td)

if NEWS_CFG["sources"].get("venturebeat"):
    with st.spinner("VentureBeat AI..."):
        vb = fetch_venturebeat()
        all_articles.extend(vb)

if not all_articles:
    st.warning("Keine Artikel gefunden. Firecrawl-Key prüfen.")
    st.stop()

# --- LLM filter ---
st.divider()
st.subheader(f"🤖 Top {NEWS_CFG['top_n']} Artikel — KI-kuratiert")
st.caption(f"Model: `{LLM_CFG['model']}` · {len(all_articles)} Artikel aus {sum([NEWS_CFG['sources'].get(s, False) for s in ['hackernews','the_decoder','venturebeat']])} Quellen")

with st.spinner(f"Filtere mit {LLM_CFG['model']}..."):
    filtered = _llm_filter_and_summarize(
        all_articles,
        top_n=NEWS_CFG["top_n"],
        language=NEWS_CFG["language"],
        model=LLM_CFG["model"],
    )

# --- Display ---
SOURCE_COLORS = {
    "HackerNews": "🟠",
    "The Decoder": "🔵",
    "VentureBeat": "🟢",
}

for article in filtered:
    icon = SOURCE_COLORS.get(article.get("source", ""), "⚪")
    st.markdown(f"### {icon} [{article['title']}]({article['url']})")
    if article.get("summary"):
        st.write(article["summary"])
    st.caption(f"Quelle: {article.get('source', '—')}")
    st.divider()

st.caption(
    f"Generiert: {datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M UTC')} · "
    f"Quellen: HackerNews, The Decoder, VentureBeat AI"
)
