import streamlit as st


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

st.set_page_config(page_title="Data Dashboard", page_icon="📊", layout="wide")

st.title("📊 Data Dashboard")
st.markdown(
    """
    Welcome to the Data Dashboard. Use the sidebar to navigate between pages.

    **Available pages:**
    - **GitHub Trending** — Top trending repositories on GitHub, visualized with star counts.
    """
)
