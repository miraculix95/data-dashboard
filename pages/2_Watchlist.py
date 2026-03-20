import json
import streamlit as st
from pathlib import Path
from datetime import datetime

WATCHLIST_PATH = Path(__file__).parent.parent / "watchlist.json"


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

st.set_page_config(page_title="Watchlist", page_icon="🔖", layout="wide")
st.title("🔖 Watchlist")
st.caption("Repos die du im Auge behalten willst.")

if not WATCHLIST_PATH.exists() or WATCHLIST_PATH.read_text().strip() == "[]":
    st.info("Noch keine Repos auf der Watchlist. Geh zur GitHub Trending Seite und füge welche hinzu.")
    st.stop()

watchlist = json.loads(WATCHLIST_PATH.read_text())

# Remove button
to_remove = st.multiselect(
    "Repos entfernen",
    options=[w["repo"] for w in watchlist],
    placeholder="Auswählen zum Entfernen...",
)
if to_remove and st.button("🗑️ Ausgewählte entfernen"):
    watchlist = [w for w in watchlist if w["repo"] not in to_remove]
    WATCHLIST_PATH.write_text(json.dumps(watchlist, indent=2, ensure_ascii=False))
    st.success(f"{len(to_remove)} Repo(s) entfernt.")
    st.rerun()

st.divider()

for entry in watchlist:
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**[{entry['repo']}]({entry['url']})**")
        if entry.get("description"):
            st.caption(entry["description"])
    with col2:
        st.metric("Stars", f"{entry.get('stars', 0):,}")
        st.caption(f"Added: {entry.get('added', '—')}  ·  {entry.get('language', 'N/A')}")
    st.divider()
