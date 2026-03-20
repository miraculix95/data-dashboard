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

WATCHLIST_PATH = Path(__file__).parent.parent / "watchlist.json"

LANGUAGES = [
    "", "Python", "TypeScript", "JavaScript", "Rust", "Go",
    "Java", "C++", "C", "C#", "Swift", "Kotlin", "Ruby", "PHP",
    "Shell", "Jupyter Notebook", "HTML", "Dart", "Scala", "Haskell",
]

TIME_OPTIONS = {"24h": 1, "7 Tage": 7, "30 Tage": 30}


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

# --- Refresh button ---
col_r, col_info = st.columns([1, 5])
with col_r:
    if st.button("🔄 Refresh", help="Clear cache and reload data"):
        st.cache_data.clear()
        st.rerun()
with col_info:
    ttl_days = CONFIG["github"]["cache_ttl_seconds"] // 86400
    st.caption(f"Data cached for {ttl_days} day(s). Use the button to force a reload.")


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
    return text.encode("latin-1", errors="ignore").decode("latin-1")


def _load_watchlist() -> list:
    if WATCHLIST_PATH.exists():
        return json.loads(WATCHLIST_PATH.read_text())
    return []


def _save_watchlist(entries: list):
    WATCHLIST_PATH.write_text(json.dumps(entries, indent=2, ensure_ascii=False))


def _send_telegram_pdf(pdf_bytes: bytes, filename: str, caption: str) -> str:
    """Send a PDF to the configured Telegram chat. Returns error string or empty string on success."""
    try:
        settings_path = Path(__file__).parent.parent.parent / ".claude" / "claudeclaw" / "settings.json"
        s = json.loads(settings_path.read_text())
        token = s["telegram"]["token"]
        chat_id = s["telegram"]["allowedUserIds"][0]
    except Exception as e:
        return f"Config error: {e}"
    try:
        import io
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendDocument",
            data={"chat_id": chat_id, "caption": caption},
            files={"document": (filename, io.BytesIO(pdf_bytes), "application/pdf")},
            timeout=30,
        )
        resp.raise_for_status()
        return ""
    except Exception as e:
        return str(e)


def _generate_cover_image(language: str, date: str) -> bytes | None:
    """Generate a cover image via FAL (Flux Schnell). Returns JPEG bytes or None on failure."""
    api_key = os.getenv("FAL_KEY")
    if not api_key:
        return None
    prompt = (
        f"Abstract digital artwork representing open source software development and AI technology trends. "
        f"GitHub repositories, code, data visualization, glowing nodes and network connections. "
        f"Dark background, deep blue and violet tones, futuristic, professional, minimalist, high quality. "
        f"No text, no letters, no words."
        + (f" Focus on {language} programming ecosystem." if language else "")
    )
    try:
        resp = requests.post(
            "https://fal.run/fal-ai/flux/schnell",
            headers={"Authorization": f"Key {api_key}", "Content-Type": "application/json"},
            json={"prompt": prompt, "image_size": "landscape_16_9", "num_images": 1},
            timeout=45,
        )
        resp.raise_for_status()
        image_url = resp.json()["images"][0]["url"]
        img_resp = requests.get(image_url, timeout=20)
        img_resp.raise_for_status()
        return img_resp.content
    except Exception:
        return None


def _build_summary_pdf(df, summary_md: str, date: str, model: str, repo_summaries: dict = None, repo_details: dict = None, cover_image: bytes = None, language: str = "") -> bytes:
    """Generate a PDF from the summary markdown and repo table."""
    import io
    import re
    import tempfile
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)

    # --- Cover page ---
    pdf.add_page()
    pdf.set_margins(0, 0, 0)

    if cover_image:
        try:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp.write(cover_image)
                tmp_path = tmp.name
            # Full-width image, top half of page
            pdf.image(tmp_path, x=0, y=0, w=210, h=105)
            import os as _os
            _os.unlink(tmp_path)
        except Exception:
            pass

    # Title overlay
    pdf.set_xy(20, 115)
    pdf.set_margins(20, 20, 20)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(30, 30, 30)
    pdf.multi_cell(0, 12, "GitHub Trending", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(80, 80, 80)
    pdf.multi_cell(0, 8, "AI Summary Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(6)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(0, 6, f"Generated: {date}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.multi_cell(0, 6, f"Model: {_sanitize(model)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    if language:
        pdf.multi_cell(0, 6, f"Language filter: {language}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Content starts on page 2
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

    col_widths = [55, 18, 18, 24, 55]
    headers = ["Repo", "Stars", "Forks", "Language", "Description"]
    ROW_H = 8

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

        desc = (repo_summaries or {}).get(row["repo"], str(row["description"]))
        vals = [
            _sanitize(row["repo"][:28]),
            f"{row['stars']:,}",
            f"{row['forks']:,}",
            _sanitize(str(row["language"])[:13]),
            _sanitize(desc[:200]),
        ]

        x_start = pdf.get_x()
        y_start = pdf.get_y()

        repo_url = str(row.get("url", ""))
        for j, (val, w) in enumerate(zip(vals[:-1], col_widths[:-1])):
            link = repo_url if j == 0 else ""
            pdf.set_text_color(0, 0, 200) if j == 0 else pdf.set_text_color(60, 60, 60)
            pdf.cell(w, ROW_H, val, border=1, fill=True, link=link)
        pdf.set_text_color(60, 60, 60)

        pdf.multi_cell(
            col_widths[-1], ROW_H, vals[-1],
            border=1, fill=True,
            new_x=XPos.LEFT, new_y=YPos.NEXT,
            max_line_height=ROW_H,
        )
        row_bottom = pdf.get_y()

        if row_bottom > y_start + ROW_H:
            x = x_start
            for w in col_widths[:-1]:
                pdf.rect(x, y_start, w, row_bottom - y_start)
                x += w

        pdf.set_xy(x_start, row_bottom)

    # --- Appendix: per-repo details ---
    if repo_details:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(30, 30, 30)
        pdf.multi_cell(0, 10, "Anhang: Projektbeschreibungen", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)

        for i, row in df.iterrows():
            detail = repo_details.get(row["repo"], "")
            if not detail:
                continue
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(0, 0, 180)
            repo_url = str(row.get("url", ""))
            pdf.multi_cell(0, 7, _sanitize(row["repo"]), new_x=XPos.LMARGIN, new_y=YPos.NEXT, link=repo_url)
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(50, 50, 50)
            pdf.multi_cell(0, 6, _sanitize(detail), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(4)

    # Credits footer
    pdf.ln(4)
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
        import re
        content = re.sub(r"!\[.*?\]\(.*?\)", "", content)
        content = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", content)
        content = re.sub(r"#{1,6}\s*", "", content)
        content = re.sub(r"```[\s\S]*?```", "", content)
        content = re.sub(r"\s+", " ", content).strip()
        return content[:max_chars]
    except Exception:
        return ""


@st.cache_data(ttl=TTL)
def fetch_trending(language: str = "", limit: int = 10, days: int = 7):
    since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
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
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    lang_labels = ["Alle"] + LANGUAGES[1:]
    lang_choice = st.selectbox("Sprache", lang_labels, index=0)
    language = "" if lang_choice == "Alle" else lang_choice
with col2:
    limit = st.slider("Anzahl Repos", min_value=5, max_value=30, value=CONFIG["github"]["default_limit"])
with col3:
    time_label = st.radio("Zeitraum", list(TIME_OPTIONS.keys()), index=1, horizontal=True)
    days = TIME_OPTIONS[time_label]

st.caption(f"Top {limit} Repos · Sprache: {lang_choice} · Erstellt in den letzten {days} Tag(en)")

with st.spinner("Fetching data from GitHub..."):
    try:
        df = fetch_trending(language=language, limit=limit, days=days)
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
ax.set_title(f"Trending GitHub Repositories ({time_label})")
plt.tight_layout()
st.pyplot(fig)

# --- Data table ---
st.subheader("Data table")
st.dataframe(
    df[["repo", "stars", "forks", "language", "description"]],
    use_container_width=True,
    hide_index=True,
)

# --- Watchlist ---
st.subheader("Zur Watchlist hinzufügen")
watchlist = _load_watchlist()
watchlist_repos = {w["repo"] for w in watchlist}
repo_options = df["repo"].tolist()
already_watched = [r for r in repo_options if r in watchlist_repos]
to_add = st.multiselect(
    "Repos auswählen",
    options=repo_options,
    default=already_watched,
    help="Ausgewählte Repos werden in der Watchlist gespeichert",
)
if st.button("💾 Watchlist speichern"):
    # Remove repos from current fetch that are deselected, keep others
    remaining = [w for w in watchlist if w["repo"] not in watchlist_repos or w["repo"] in to_add]
    existing_repos = {w["repo"] for w in remaining}
    for repo in to_add:
        if repo not in existing_repos:
            row = df[df["repo"] == repo].iloc[0]
            remaining.append({
                "repo": repo,
                "url": row["url"],
                "stars": int(row["stars"]),
                "language": row["language"],
                "description": row["description"],
                "added": datetime.utcnow().strftime("%Y-%m-%d"),
            })
    _save_watchlist(remaining)
    st.success(f"Watchlist gespeichert — {len(remaining)} Repo(s)")


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

        readmes = {}
        with st.spinner("Fetching README context for top repos..."):
            for _, row in top_df.iterrows():
                readmes[row["repo"]] = fetch_readme(row["repo"])

        repo_list_parts = []
        repo_names = []
        for i, (_, row) in enumerate(top_df.iterrows()):
            repo_names.append(row["repo"])
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

        repo_summary_placeholders = "\n".join(
            f"{name}|||[Einzeiler hier]" for name in repo_names
        )
        repo_detail_placeholders = "\n".join(
            f"{name}|||[Detailbeschreibung hier]" for name in repo_names
        )

        lang_instruction = (
            "Schreibe den Bericht auf Deutsch." if lang_out == "de"
            else "Write the report in English."
        )

        prompt_template = (Path(__file__).parent.parent / "prompts" / "github_summary.md").read_text()
        prompt = prompt_template.format(
            lang_instruction=lang_instruction,
            date=datetime.utcnow().strftime("%d.%m.%Y"),
            repo_list=repo_list,
            repo_summary_placeholders=repo_summary_placeholders,
            repo_detail_placeholders=repo_detail_placeholders,
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
                raw_response = resp.json()["choices"][0]["message"]["content"]

            except Exception as e:
                st.error(f"LLM error: {e}")
                st.stop()

        # Parse structured blocks from the response
        repo_summaries = {}
        repo_details = {}

        def _parse_kv_block(text: str) -> dict:
            result = {}
            for line in text.strip().splitlines():
                if "|||" in line:
                    key, _, val = line.partition("|||")
                    result[key.strip()] = val.strip()
            return result

        if "---REPO_DETAILS---" in raw_response:
            before_details, _, details_block = raw_response.partition("---REPO_DETAILS---")
            details_text = details_block.split("---")[0]
            repo_details = _parse_kv_block(details_text)
            raw_response = before_details

        if "---REPO_SUMMARIES---" in raw_response:
            parts = raw_response.split("---REPO_SUMMARIES---", 1)
            summary_md = parts[0].strip()
            repo_summaries = _parse_kv_block(parts[1])
        else:
            summary_md = raw_response.strip()

        # Generate cover image via FAL
        with st.spinner("Generiere Titelgrafik (FAL Flux)..."):
            cover_image = _generate_cover_image(language=language, date=datetime.utcnow().strftime("%d.%m.%Y"))

        st.session_state["summary_md"] = summary_md
        st.session_state["summary_date"] = datetime.utcnow().strftime("%d.%m.%Y %H:%M UTC")
        st.session_state["repo_summaries"] = repo_summaries
        st.session_state["repo_details"] = repo_details
        st.session_state["cover_image"] = cover_image

    # Display summary if available
    if "summary_md" in st.session_state:
        summary_md = st.session_state["summary_md"]
        summary_date = st.session_state.get("summary_date", "")

        st.markdown(summary_md)
        st.caption(f"Generated: {summary_date} · Model: {model}")

        saved_summaries = st.session_state.get("repo_summaries", {})
        saved_details = st.session_state.get("repo_details", {})
        saved_cover = st.session_state.get("cover_image")

        if saved_cover:
            st.image(saved_cover, caption="AI-generierte Titelgrafik (Flux Schnell)", use_container_width=True)

        try:
            pdf_bytes = _build_summary_pdf(
                df.head(top_n), summary_md, summary_date, model,
                repo_summaries=saved_summaries, repo_details=saved_details,
                cover_image=saved_cover, language=language,
            )
        except Exception as e:
            st.error(f"PDF generation failed: {e}")
            pdf_bytes = None

        if pdf_bytes:
            pdf_filename = f"github-trending-summary-{datetime.utcnow().strftime('%Y-%m-%d')}.pdf"
            col_dl, col_tg = st.columns([1, 1])
            with col_dl:
                st.download_button(
                    label="📄 Download as PDF",
                    data=pdf_bytes,
                    file_name=pdf_filename,
                    mime="application/pdf",
                )
            with col_tg:
                if st.button("📨 Per Telegram senden"):
                    with st.spinner("Sende PDF..."):
                        err = _send_telegram_pdf(
                            pdf_bytes,
                            pdf_filename,
                            f"GitHub Trending Report — {summary_date}",
                        )
                    if err:
                        st.error(f"Telegram-Fehler: {err}")
                    else:
                        st.success("PDF gesendet!")
