from pathlib import Path
import time

import streamlit as st
from dotenv import load_dotenv
import os
import requests
import urllib.parse
from authlib.integrations.requests_client import OAuth2Session
import extra_streamlit_components as stx

load_dotenv()

st.set_page_config(page_title="PDF Assistant", page_icon=None, layout="wide")

cookie_manager = stx.CookieManager(key="cookie_manager")

import time

# Prevent login screen from flashing on refresh by waiting for JS to load cookies
if "cookie_initialized" not in st.session_state:
    st.session_state.cookie_initialized = True
    time.sleep(0.5)
    st.rerun()

# ─── Auth Gate ───────────────────────────────────────────────────────────────────
_client_id = st.secrets.get("GOOGLE_CLIENT_ID") or os.getenv("GOOGLE_CLIENT_ID", "")
_client_secret = st.secrets.get("GOOGLE_CLIENT_SECRET") or os.getenv("GOOGLE_CLIENT_SECRET", "")
_redirect_uri = st.secrets.get("GOOGLE_REDIRECT_URI") or os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8501")

AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"

if "user" not in st.session_state:
    st.session_state.user = None

# 1. Restore from reliable cookie manager
if st.session_state.user is None:
    saved_user = cookie_manager.get("rag_user_session")
    if saved_user:
        st.session_state.user = saved_user

def get_oauth_session():
    return OAuth2Session(_client_id, _client_secret, scope="openid email profile", redirect_uri=_redirect_uri)

def handle_oauth():
    # If returning from OAuth, we will have a 'code' in query params
    query_params = st.query_params
    if "code" in query_params:
        code = query_params["code"]
        oauth = get_oauth_session()
        try:
            # Reconstruct the full redirect URL that Google sent back
            auth_response_url = f"{_redirect_uri}?{urllib.parse.urlencode(st.query_params)}"
            token = oauth.fetch_token(TOKEN_URL, authorization_response=auth_response_url)
            resp = oauth.get(USERINFO_URL)
            resp.raise_for_status()
            
            user_data = resp.json()
            st.session_state.user = user_data
            cookie_manager.set("rag_user_session", user_data, max_age=86400*30, secure=True, same_site="lax")
            
            # Clear query params so a refresh doesn't trigger oauth again
            st.query_params.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Authentication failed: {e}")

if st.session_state.user is None:
    handle_oauth()

if st.session_state.user is None:
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #111111 !important; color: #d4d4d4; }
    [data-testid="stDecoration"] { display: none; }
    #MainMenu { visibility: hidden; } footer { visibility: hidden; } header { background: transparent !important; }
    </style>
    """, unsafe_allow_html=True)
    st.markdown("""
    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:70vh;text-align:center">
        <h1 style="color:#ffffff;font-size:2.2rem;margin-bottom:8px">PDF Assistant</h1>
        <p style="color:#888888;font-size:1rem;margin-bottom:32px">Sign in to access your private document library</p>
    </div>
    """, unsafe_allow_html=True)
    col_l, col_c, col_r = st.columns([1, 0.6, 1])
    with col_c:
        oauth = get_oauth_session()
        auth_url, state = oauth.create_authorization_url(AUTHORIZATION_URL)
        st.link_button("Sign in with Google", url=auth_url, use_container_width=True, type="primary")
    st.stop()

# Logged-in user identity
user_email: str = st.session_state.user.get("email", "")
user_name: str = st.session_state.user.get("name", user_email)
user_picture: str = st.session_state.user.get("picture", "")


# ─── Custom CSS ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ── Base ── */
.stApp {
    background-color: #111111 !important;
    color: #d4d4d4;
    font-size: 15px;
}
[data-testid="stAppViewBlockContainer"] {
    padding-top: 2rem !important;
}

/* Hide Streamlit chrome */
[data-testid="stDecoration"] { display: none; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header { background: transparent !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background-color: #1a1a1a !important;
    border-right: 1px solid #2a2a2a;
}
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] .stMarkdown h1,
[data-testid="stSidebar"] .stMarkdown h2,
[data-testid="stSidebar"] .stMarkdown h3 {
    color: #b0b0b0 !important;
}

/* ── Hero strip ── */
.hero-strip {
    background: transparent;
    padding: 0 0 28px 0;
    margin-bottom: 32px;
}
.hero-strip h1 {
    font-size: 30px;
    font-weight: 700;
    color: #e8e8e8;
    margin: 0 0 8px 0;
    letter-spacing: -0.5px;
}
.hero-strip p {
    font-size: 16px;
    color: #6a6a6a;
    margin: 0;
    font-weight: 400;
}

/* ── Section label ── */
.section-label {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.10em;
    text-transform: uppercase;
    color: #555555;
    margin: 0 0 10px 0;
}

/* ── Metric ── */
[data-testid="stMetric"] {
    background: #1e1e1e;
    border: 1px solid #2a2a2a;
    border-radius: 6px;
    padding: 14px 18px;
}
[data-testid="stMetricValue"] {
    color: #e8e8e8 !important;
    font-weight: 700 !important;
    font-size: 28px !important;
}
[data-testid="stMetricLabel"] {
    color: #555555 !important;
    font-size: 10px !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

/* ── Tabs ── */
[data-testid="stTabs"] {
    border-bottom: 1px solid #2a2a2a;
}
[data-testid="stTabs"] button {
    font-family: 'Inter', sans-serif !important;
    font-size: 15px !important;
    font-weight: 500 !important;
    color: #555555 !important;
    padding: 10px 18px !important;
    border-radius: 0 !important;
    background: transparent !important;
    border: none !important;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: #e8e8e8 !important;
    border-bottom: 2px solid #888888 !important;
}
[data-testid="stTabs"] button:hover {
    color: #b0b0b0 !important;
}

/* ── Inputs ── */
[data-testid="stTextInput"] input {
    background-color: #1e1e1e !important;
    color: #d4d4d4 !important;
    border: 1px solid #333333 !important;
    border-radius: 6px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 15px !important;
    padding: 10px 14px !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: #555555 !important;
    box-shadow: 0 0 0 3px rgba(136,136,136,0.12) !important;
}
[data-testid="stTextInput"] input::placeholder {
    color: #444444 !important;
}

[data-testid="stSelectbox"] > div > div {
    background-color: #1e1e1e !important;
    border: 1px solid #333333 !important;
    border-radius: 6px !important;
    color: #d4d4d4 !important;
}

[data-testid="stNumberInput"] input {
    background-color: #1e1e1e !important;
    color: #d4d4d4 !important;
    border: 1px solid #333333 !important;
    border-radius: 6px !important;
}

/* ── Labels ── */
[data-testid="stTextInput"] label,
[data-testid="stSelectbox"] label,
[data-testid="stNumberInput"] label {
    color: #777777 !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    letter-spacing: 0.02em;
}

/* ── Q&A blocks ── */
.qa-question {
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    padding: 18px 22px;
    margin-bottom: 16px;
}
.qa-question .qa-label {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: #555555;
    margin-bottom: 8px;
}
.qa-question .qa-text {
    font-size: 16px;
    font-weight: 500;
    color: #e8e8e8;
    line-height: 1.5;
}
.qa-answer {
    background: #161616;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    padding: 22px 24px;
    margin-bottom: 16px;
}
.qa-answer .qa-label {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: #555555;
    margin-bottom: 10px;
}
.qa-answer .qa-text {
    font-size: 15px;
    color: #cccccc;
    line-height: 1.75;
}
.qa-sources {
    background: #151515;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    padding: 16px 22px;
}
.qa-sources .qa-label {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: #555555;
    margin-bottom: 10px;
}
.qa-sources .source-item {
    font-size: 13px;
    color: #888888;
    padding: 4px 0;
    border-bottom: 1px solid #222222;
    font-family: 'Inter', monospace;
}

/* ── Primary button (Search / Ingest) ── */
[data-testid="stFormSubmitButton"] button,
button[kind="primary"] {
    background: #2d2d2d !important;
    color: #e8e8e8 !important;
    border: 1px solid #404040 !important;
    border-radius: 6px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    letter-spacing: 0.03em !important;
    padding: 10px 24px !important;
    transition: background 0.15s ease, border-color 0.15s ease !important;
}
[data-testid="stFormSubmitButton"] button:hover,
button[kind="primary"]:hover {
    background: #383838 !important;
    border-color: #555555 !important;
}

/* ── Secondary / Delete button ── */
button[kind="secondary"] {
    background: transparent !important;
    color: #777777 !important;
    border: 1px solid #333333 !important;
    border-radius: 5px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    padding: 4px 12px !important;
    white-space: nowrap !important;
    min-width: 60px !important;
    transition: color 0.15s, border-color 0.15s !important;
}
button[kind="secondary"]:hover {
    color: #cccccc !important;
    border-color: #555555 !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: #1a1a1a !important;
    border: 1px dashed #333333 !important;
    border-radius: 8px !important;
}

/* ── Chat messages ── */
[data-testid="stChatMessage"] {
    background: #1a1a1a !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 8px !important;
}
[data-testid="stChatMessage"] p {
    color: #d4d4d4 !important;
    font-size: 14px !important;
    line-height: 1.6 !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: #1a1a1a !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 6px !important;
}
[data-testid="stExpander"] summary {
    color: #777777 !important;
    font-size: 13px !important;
}

/* ── Divider ── */
hr {
    border-color: #2a2a2a !important;
    margin: 20px 0 !important;
}

/* ── Alerts ── */
[data-testid="stAlert"] {
    background: #1e1e1e !important;
    border-radius: 6px !important;
    border: 1px solid #333333 !important;
    color: #aaaaaa !important;
}
[data-testid="stAlert"] p {
    color: #aaaaaa !important;
}

/* ── Spinner ── */
[data-testid="stSpinner"] p {
    color: #777777 !important;
    font-size: 13px !important;
}

/* ── Success message ── */
[data-testid="stSuccess"] {
    background: #1e1e1e !important;
    border: 1px solid #3a3a3a !important;
    color: #b0b0b0 !important;
    border-radius: 6px !important;
}
</style>
""", unsafe_allow_html=True)


# ─── Helpers ─────────────────────────────────────────────────────────────────────

def save_uploaded_pdf(file) -> Path:
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    file_path = uploads_dir / file.name
    file_path.write_bytes(file.getbuffer())
    return file_path


def _inngest_api_base() -> str:
    return os.getenv("INNGEST_API_BASE", "http://127.0.0.1:8288/v1")


def _send_inngest_event(name: str, data: dict) -> dict:
    event_key = os.getenv("INNGEST_EVENT_KEY")
    if event_key:
        # Production: send to Inngest Cloud
        url = f"https://inn.gs/e/{event_key}"
    else:
        # Local Development: send to local Inngest CLI
        base_url = _inngest_api_base()
        if base_url.endswith("/v1"):
            base_url = base_url[:-3]
        url = f"{base_url}/e/local"
        
    resp = requests.post(url, json={"name": name, "data": data})
    resp.raise_for_status()
    return resp.json()


def _backend_url() -> str:
    if os.getenv("INNGEST_EVENT_KEY"):
        return "https://rag-pdf-assistant-1jkt.onrender.com"
    return "http://127.0.0.1:8000"


def send_rag_ingest_sync(uploaded_file, user_id: str) -> None:
    url = f"{_backend_url()}/api/ingest"
    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
    data = {"user_id": user_id}
    resp = requests.post(url, files=files, data=data)
    if not resp.ok:
        st.error(f"Backend Error: {resp.status_code} - {resp.text}")
        st.stop()


def fetch_user_sources(user_id: str) -> list[str]:
    """Fetch source names for this user from the backend."""
    try:
        resp = requests.get(f"{_backend_url()}/api/list_sources", params={"user_id": user_id}, timeout=10)
        resp.raise_for_status()
        raw = resp.json().get("sources", [])
        # Strip the user prefix so UI shows only the filename
        prefix = f"{user_id}/"
        return [s[len(prefix):] if s.startswith(prefix) else s for s in raw]
    except Exception:
        return []


def send_rag_query_event(question: str, top_k: int, source_id: str = None) -> str:
    payload = _send_inngest_event(
        "rag/query_pdf_ai",
        {"question": question, "top_k": top_k, "source_id": source_id},
    )
    ids = payload.get("ids")
    if ids and len(ids) > 0:
        return ids[0]
    return payload.get("id")


def fetch_runs(event_id: str) -> list[dict]:
    event_key = os.getenv("INNGEST_EVENT_KEY")
    if event_key:
        # Production: poll Inngest Cloud REST API
        url = f"https://api.inngest.com/v1/events/{event_id}/runs"
        headers = {"Authorization": f"Bearer {os.getenv('INNGEST_REST_API_KEY', '')}"}
        resp = requests.get(url, headers=headers)
    else:
        # Local development
        url = f"{_inngest_api_base()}/events/{event_id}/runs"
        resp = requests.get(url)
        
    resp.raise_for_status()
    return resp.json().get("data", [])


def wait_for_run_output(event_id: str, timeout_s: float = 120.0, poll_interval_s: float = 0.5) -> dict:
    start = time.time()
    last_status = None
    while True:
        runs = fetch_runs(event_id)
        if runs:
            run = runs[0]
            status = run.get("status")
            last_status = status or last_status
            if status in ("Completed", "Succeeded", "Success", "Finished"):
                return run.get("output") or {}
            if status in ("Failed", "Cancelled"):
                raise RuntimeError(f"Function run {status}")
        if time.time() - start > timeout_s:
            raise TimeoutError(f"Timed out (last status: {last_status})")
        time.sleep(poll_interval_s)


# ─── PDF List ─────────────────────────────────────────────────────────────────────

# Load user's document list from backend
pdf_filenames: list[str] = fetch_user_sources(user_email)

# Session state for post-rerun feedback
if "last_ingested" not in st.session_state:
    st.session_state.last_ingested = None


# ─── Sidebar ──────────────────────────────────────────────────────────────────────

with st.sidebar:
    # ── User info ──
    img_html = f'<img src="{user_picture}" style="width: 36px; height: 36px; border-radius: 50%; object-fit: cover; border: 1px solid #333;">' if user_picture else ""
    st.markdown(f"""
    <div style="padding:12px 0 12px 0; display: flex; align-items: center; gap: 12px;">
        {img_html}
        <div>
            <div style="font-size:13px;font-weight:600;color:#ffffff;line-height:1.2">{user_name}</div>
            <div style="font-size:11px;color:#888888;margin-top:2px;line-height:1.2">{user_email}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Logout", use_container_width=True, type="secondary"):
        st.session_state.user = None
        cookie_manager.delete("rag_user_session")
        st.rerun()
    st.divider()

    st.markdown("## Document Library")
    st.divider()

    if not pdf_filenames:
        st.info("No documents uploaded yet.")
    else:
        st.metric("Documents indexed", len(pdf_filenames))
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<p class="section-label">Manage files</p>', unsafe_allow_html=True)
        for fname in pdf_filenames:
            full_source_id = f"{user_email}/{fname}"
            col1, col2 = st.columns([0.65, 0.35], vertical_alignment="center")
            col1.markdown(
                f"<span style='font-size:12px;font-weight:500;color:#aaaaaa;word-break:break-all'>{fname}</span>",
                unsafe_allow_html=True,
            )
            if col2.button("Delete", key=f"del_{fname}", type="secondary"):
                try:
                    from vector_db import QdrantStorage
                    QdrantStorage().delete_by_source(full_source_id)
                    st.toast(f"Removed {fname}")
                    time.sleep(0.4)
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

    st.divider()
    st.markdown(
        '<p style="font-size:11px;color:#3a3a3a">Qdrant · OpenRouter · Google Auth</p>',
        unsafe_allow_html=True,
    )


# ─── Hero Strip ───────────────────────────────────────────────────────────────────

st.markdown("""
<div class="hero-strip">
    <h1>PDF Assistant</h1>
    <p>Upload documents and ask questions. Answers are grounded in your own files.</p>
</div>
""", unsafe_allow_html=True)


# ─── Main Tabs ────────────────────────────────────────────────────────────────────

tab_chat, tab_upload = st.tabs(["Ask Questions", "Upload Document"])


# ── Upload Tab ────────────────────────────────────────────────────────────────────

with tab_upload:
    st.markdown('<p class="section-label" style="margin-top:24px">Select a PDF to ingest</p>', unsafe_allow_html=True)
    uploaded = st.file_uploader(
        "PDF",
        type=["pdf"],
        accept_multiple_files=False,
        label_visibility="collapsed",
    )
    if uploaded is not None:
        col_btn, _ = st.columns([0.2, 0.8])
        with col_btn:
            if st.button("Ingest Document", type="primary"):
                with st.spinner("Processing document..."):
                    send_rag_ingest_sync(uploaded, user_id=user_email)
                st.session_state.last_ingested = uploaded.name
                st.rerun()

    if st.session_state.last_ingested:
        st.success(f"Successfully ingested: {st.session_state.last_ingested}")
        st.session_state.last_ingested = None


# ── Chat Tab ──────────────────────────────────────────────────────────────────────

with tab_chat:
    st.markdown('<p class="section-label" style="margin-top:24px">Ask a question</p>', unsafe_allow_html=True)

    with st.form("rag_query_form"):
        question = st.text_input(
            "Question",
            placeholder="e.g. What is the main argument in Chapter 2?",
            label_visibility="collapsed",
        )
        col1, col2 = st.columns([0.6, 0.4], vertical_alignment="bottom")
        with col1:
            pdf_options = ["All Documents"] + pdf_filenames
            selected_pdf = st.selectbox("Source", pdf_options)
        with col2:
            top_k = st.number_input(
                "Chunks to retrieve",
                min_value=1, max_value=20, value=5, step=1,
                help="Number of text chunks retrieved from the vector database.",
            )
        submitted = st.form_submit_button("Search", type="primary", use_container_width=True)

    if submitted and question.strip():
        with st.spinner("Searching documents..."):
            # Build the scoped source_id if user selected a specific file
            if selected_pdf == "All Documents":
                source_id = None
            else:
                source_id = f"{user_email}/{selected_pdf}"
            try:
                resp = requests.post(
                    f"{_backend_url()}/api/query",
                    json={"question": question.strip(), "top_k": int(top_k), "source_id": source_id, "user_id": user_email},
                    timeout=120,
                )
                resp.raise_for_status()
                output = resp.json()
                answer = output.get("answer", "")
                raw_sources = output.get("sources", [])
                # Strip user prefix from displayed sources
                prefix = f"{user_email}/"
                sources = [s[len(prefix):] if s.startswith(prefix) else s for s in raw_sources]
            except Exception as e:
                st.error(f"Error querying backend: {e}")
                answer = "Error generating answer."
                sources = []

        # Scroll to answer
        st.components.v1.html("""
        <script>
            window.parent.document.querySelector('[data-testid="stMainBlockContainer"]')
                ?.scrollTo({ top: 99999, behavior: 'smooth' });
        </script>
        """, height=0)

        # Question block
        st.markdown(f"""
        <div class="qa-question">
            <div class="qa-label">Question</div>
            <div class="qa-text">{question}</div>
        </div>
        """, unsafe_allow_html=True)

        # Answer block
        st.markdown(f"""
        <div class="qa-answer">
            <div class="qa-label">Answer</div>
            <div class="qa-text">{answer or "No answer generated."}</div>
        </div>
        """, unsafe_allow_html=True)

        # Sources block — always shown inline
        if sources:
            sources_html = "".join(
                f'<div class="source-item">{s}</div>' for s in sources
            )
            st.markdown(f"""
            <div class="qa-sources">
                <div class="qa-label">Sources</div>
                {sources_html}
            </div>
            """, unsafe_allow_html=True)
