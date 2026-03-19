import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import requests
from datetime import datetime, timedelta


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


@st.cache_data(ttl=3600)
def fetch_trending(language: str = "", limit: int = 15):
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
            "url": item["html_url"],
        }
        for item in items
    ])


col1, col2 = st.columns([2, 1])
with col1:
    language = st.text_input("Filter by language (optional)", placeholder="e.g. Python, TypeScript")
with col2:
    limit = st.slider("Number of repos", min_value=5, max_value=30, value=15)

with st.spinner("Fetching data from GitHub..."):
    try:
        df = fetch_trending(language=language.strip(), limit=limit)
    except Exception as e:
        st.error(f"GitHub API error: {e}")
        st.stop()

if df.empty:
    st.warning("No repositories found.")
    st.stop()

# Bar chart
st.subheader("Star counts")
fig, ax = plt.subplots(figsize=(12, 5))
sns.barplot(data=df, x="stars", y="repo", palette="viridis", ax=ax)
ax.set_xlabel("Stars")
ax.set_ylabel("")
ax.set_title("Trending GitHub Repositories (last 7 days)")
plt.tight_layout()
st.pyplot(fig)

# Data table
st.subheader("Data table")
st.dataframe(
    df[["repo", "stars", "forks", "language", "description"]],
    use_container_width=True,
    hide_index=True,
)
