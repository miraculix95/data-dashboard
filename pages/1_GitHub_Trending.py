import os
import sys
import json
import yaml
import requests
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import streamlit as st
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Load shared .env from devhub root
load_dotenv(Path(__file__).parent.parent.parent / ".env")

# Load config
CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"
with open(CONFIG_PATH) as f:
    CONFIG = yaml.safe_load(f)


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

st.set_page_config(page_title="GitHub Trending", page_icon="⭐", layout="wide")
st.title("⭐ GitHub Trending Repositories")
st.caption("Top repositories by stars — created in the last 7 days")

# --- Refresh button ---
col_r, col_info = st.columns([1, 5])
with col_r:
    if st.button("🔄 Refresh", help="Clear cache and reload data"):
        st.cache_data.clear()
        st.rerun()
with col_info:
    ttl_days = CONFIG["github"]["cache_ttl_seconds"] // 86400
    st.caption(f"Data is cached for {ttl_days} day(s). Use the button to force a reload.")


def _sanitize(text: str) -> str:
    """Replace Unicode chars unsupported by Helvetica (latin-1) with ASCII equivalents."""
    replacements = {
        "\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"',
        "\u2014": "--", "\u2013": "-", "\u2022": "-", "\u2026": "...",
        "\u2192": "->", "\u2190": "<-", "\u2194": "<->",
        "\u2665": "<3", "\u2764": "<3", "\u00b7": ".", "\u2713": "v",
        "\u00e4": "ae", "\u00f6": "oe", "\u00fc": "ue",
        "\u00c4": "Ae", "\u00d6": "Oe", "\u00dc": "Ue", "\u00df": "ss",
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    # Drop anything still outside latin-1 silently
    return text.encode("latin-1", errors="ignore").decode("latin-1")


def _build_summary_pdf(df, summary_md: str, date: str, model: str, readmes: dict = None) -> bytes:
    """Generate a PDF from the summary markdown and repo table."""
    import io
    import re
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pdf.set_margins(20, 20, 20)

    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(30, 30, 30)
    pdf.multi_cell(0, 10, "GitHub Trending - AI Summary", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(0, 6, f"Generated: {date}  |  Model: {model}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)

    plain = re.sub(r"#{1,6}\s*", "", summary_md)
    plain = re.sub(r"\*\*(.+?)\*\*", r"\1", plain)
    plain = re.sub(r"\*(.+?)\*", r"\1", plain)
    plain = re.sub(r"`(.+?)`", r"\1", plain)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(50, 50, 50)
    for line in plain.split("\n"):
        line = _sanitize(line.strip())
        if not line:
            pdf.ln(3)
            continue
        pdf.multi_cell(0, 6, line, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(30, 30, 30)
    pdf.multi_cell(0, 8, "Top Repositories", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Col widths sum to 170mm (= page width minus margins)
    col_widths = [55, 18, 18, 24, 55]
    headers = ["Repo", "Stars", "Forks", "Language", "Description"]
    ROW_H = 8

    # Header row
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(220, 220, 220)
    pdf.set_text_color(30, 30, 30)
    for h, w in zip(headers, col_widths):
        pdf.cell(w, ROW_H, h, border=1, fill=True)
    pdf.ln()

    pdf.set_font("Helvetica", "", 8)
    for i, row in df.iterrows():
        fill_color = (248, 248, 248) if i % 2 == 0 else (255, 255, 255)
        pdf.set_fill_color(*fill_color)
        pdf.set_text_color(60, 60, 60)

        # Use README excerpt as description if available, fall back to GitHub description
        readme_text = (readmes or {}).get(row["repo"], "")
        desc = readme_text if readme_text else str(row["description"])
        vals = [
            _sanitize(row["repo"][:28]),
            f"{row['stars']:,}",
            f"{row['forks']:,}",
            _sanitize(str(row["language"])[:13]),
            _sanitize(desc[:200]),
        ]

        x_start = pdf.get_x()
        y_start = pdf.get_y()

        # Draw single-line cells for first 4 columns (repo col gets a clickable link)
        repo_url = str(row.get("url", ""))
        for j, (val, w) in enumerate(zip(vals[:-1], col_widths[:-1])):
            link = repo_url if j == 0 else ""
            pdf.set_text_color(0, 0, 200) if j == 0 else pdf.set_text_color(60, 60, 60)
            pdf.cell(w, ROW_H, val, border=1, fill=True, link=link)
        pdf.set_text_color(60, 60, 60)

        # Multi-cell for description (wraps automatically)
        x_desc = pdf.get_x()
        pdf.multi_cell(
            col_widths[-1], ROW_H, vals[-1],
            border=1, fill=True,
            new_x=XPos.LEFT, new_y=YPos.NEXT,
            max_line_height=ROW_H,
        )
        row_bottom = pdf.get_y()

        # Extend borders of single-line cells to match description height
        if row_bottom > y_start + ROW_H:
            x = x_start
            for w in col_widths[:-1]:
                pdf.rect(x, y_start, w, row_bottom - y_start)
                x += w

        pdf.set_xy(x_start, row_bottom)

    # Credits footer
    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(160, 160, 160)
    pdf.multi_cell(
        0, 5,
        f"Generated by Tom (ClaudeClaw) | dashboard.ai-devhub-247.site | Model: {_sanitize(model)} | {date}",
        new_x=XPos.LMARGIN, new_y=YPos.NEXT
    )

    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()


# --- Fetch trending repos + READMEs ---
TTL = CONFIG["github"]["cache_ttl_seconds"]

@st.cache_data(ttl=TTL)
def fetch_readme(repo_full_name: str, max_chars: int = 2000) -> str:
    """Fetch and decode the README for a repo. Returns first max_chars characters."""
    try:
        import base64
        url = f"https://api.github.com/repos/{repo_full_name}/readme"
        resp = requests.get(url, headers={"Accept": "application/vnd.github+json"}, timeout=8)
        if resp.status_code != 200:
            return ""
        content = base64.b64decode(resp.json().get("content", "")).decode("utf-8", errors="ignore")
        # Strip markdown syntax and take first max_chars
        import re
        content = re.sub(r"!\[.*?\]\(.*?\)", "", content)   # remove images
        content = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", content)  # links → text
        content = re.sub(r"#{1,6}\s*", "", content)
        content = re.sub(r"```[\s\S]*?```", "", content)
        content = re.sub(r"\s+", " ", content).strip()
        return content[:max_chars]
    except Exception:
        return ""


@st.cache_data(ttl=TTL)
def fetch_trending(language: str = "", limit: int = 10):
    since = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
    query = f"created:>{since}"
    if language:
        query += f" language:{language}"
    url = "https://api.github.com/search/repositories"
    params = {"q": query, "sort": "stars", "order": "desc", "per_page": limit}
    headers = {"Accept": "application/vnd.github+json"}
    resp = requests.get(url, params=params, headers=headers, timeout=10)
    resp.raise_for_status()
    items = resp.json().get("items", [])
    return pd.DataFrame([
        {
            "repo": item["full_name"],
            "stars": item["stargazers_count"],
            "forks": item["forks_count"],
            "language": item.get("language") or "N/A",
            "description": item.get("description") or "",
            "topics": ", ".join(item.get("topics", [])),
            "url": item["html_url"],
        }
        for item in items
    ])


# --- Controls ---
col1, col2 = st.columns([2, 1])
with col1:
    language = st.text_input("Filter by language (optional)", placeholder="e.g. Python, TypeScript")
with col2:
    limit = st.slider("Number of repos", min_value=5, max_value=30, value=CONFIG["github"]["default_limit"])

with st.spinner("Fetching data from GitHub..."):
    try:
        df = fetch_trending(language=language.strip(), limit=limit)
    except Exception as e:
        st.error(f"GitHub API error: {e}")
        st.stop()

if df.empty:
    st.warning("No repositories found.")
    st.stop()

# --- Bar chart ---
st.subheader("Star counts")
fig, ax = plt.subplots(figsize=(12, 5))
sns.barplot(data=df, x="stars", y="repo", palette="viridis", ax=ax)
ax.set_xlabel("Stars")
ax.set_ylabel("")
ax.set_title("Trending GitHub Repositories (last 7 days)")
plt.tight_layout()
st.pyplot(fig)

# --- Data table ---
st.subheader("Data table")
st.dataframe(
    df[["repo", "stars", "forks", "language", "description"]],
    use_container_width=True,
    hide_index=True,
)


# --- AI Summary ---
if CONFIG["summary"]["enabled"]:
    st.divider()
    st.subheader("🤖 AI Summary")

    top_n = CONFIG["summary"]["top_n"]
    lang_out = CONFIG["summary"]["language"]
    model = CONFIG["llm"]["model"]
    st.caption(f"Model: `{model}` · Top {top_n} repos · Language: {lang_out.upper()}")

    if st.button("✨ Generate AI Summary"):
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            st.error("OPENROUTER_API_KEY not found in .env")
            st.stop()

        top_df = df.head(top_n)

        # Fetch READMEs for richer context
        readmes = {}
        with st.spinner("Fetching README context for top repos..."):
            for _, row in top_df.iterrows():
                readmes[row["repo"]] = fetch_readme(row["repo"])

        repo_list_parts = []
        for i, (_, row) in enumerate(top_df.iterrows()):
            entry = (
                f"{i+1}. **{row['repo']}** ({row['stars']:,} ⭐, {row['language']})\n"
                f"   Description: {row['description']}"
            )
            if row["topics"]:
                entry += f"\n   Topics: {row['topics']}"
            readme = readmes.get(row["repo"], "")
            if readme:
                entry += f"\n   README excerpt: {readme}"
            repo_list_parts.append(entry)
        repo_list = "\n\n".join(repo_list_parts)

        lang_instruction = (
            "Schreibe den Bericht auf Deutsch." if lang_out == "de"
            else "Write the report in English."
        )

        prompt_template = (Path(__file__).parent.parent / "prompts" / "github_summary.md").read_text()
        prompt = prompt_template.format(
            lang_instruction=lang_instruction,
            date=datetime.utcnow().strftime("%d.%m.%Y"),
            repo_list=repo_list,
        )

        with st.spinner(f"Asking {model}..."):
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
                        "max_tokens": CONFIG["llm"]["max_tokens"],
                        "temperature": CONFIG["llm"]["temperature"],
                    },
                    timeout=60,
                )
                resp.raise_for_status()
                summary_md = resp.json()["choices"][0]["message"]["content"]

            except Exception as e:
                st.error(f"LLM error: {e}")
                st.stop()

        # Store in session state so it persists without re-generating
        st.session_state["summary_md"] = summary_md
        st.session_state["summary_date"] = datetime.utcnow().strftime("%d.%m.%Y %H:%M UTC")
        st.session_state["summary_readmes"] = readmes

    # Display summary if available
    if "summary_md" in st.session_state:
        summary_md = st.session_state["summary_md"]
        summary_date = st.session_state.get("summary_date", "")

        st.markdown(summary_md)
        st.caption(f"Generated: {summary_date} · Model: {model}")

        # PDF download
        saved_readmes = st.session_state.get("summary_readmes", {})
        pdf_bytes = _build_summary_pdf(df.head(top_n), summary_md, summary_date, model, readmes=saved_readmes)
        st.download_button(
            label="📄 Download as PDF",
            data=pdf_bytes,
            file_name=f"github-trending-summary-{datetime.utcnow().strftime('%Y-%m-%d')}.pdf",
            mime="application/pdf",
        )


