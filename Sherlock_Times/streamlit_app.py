import os
import json
from datetime import datetime
from typing import Dict, List, Any, Tuple

import streamlit as st
import feedparser
import requests
from bs4 import BeautifulSoup
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from streamlit_autorefresh import st_autorefresh

# ---------------------------
# App Config
# ---------------------------
st.set_page_config(page_title="Sherlock Times", page_icon="🕵️", layout="wide")

APP_TITLE = "🕵️ Sherlock Times – Company, Person & Product News Dashboard"
DATA_PATH = os.path.join("data", "app_state.json")
USER_FILE = os.path.join("data", "users.json")

analyzer = SentimentIntensityAnalyzer()

# ---------------------------
# Default Seeds
# ---------------------------
DEFAULT_STATE = {
    "companies": [
        {"name": "Google", "location": "IN"},
        {"name": "Microsoft", "location": "US"}
    ],
    "persons": [
        {"name": "Sundar Pichai", "company": "Google"},
        {"name": "Satya Nadella", "company": "Microsoft"}
    ]
}

DEFAULT_USER = {
    "admin": {"username": "sherlock", "password": "sherlock123"}
}

# ---------------------------
# Product Information (no logos)
# ---------------------------
PRODUCTS = {
    "OpenAI": {
        "keywords": "OpenAI API OR ChatGPT OR GPT-5 OR DALL-E site:techcrunch.com OR site:venturebeat.com",
        "category": "Generative AI / API Platform",
        "focus": "GPT models, multimodal AI, API ecosystem, and enterprise integrations"
    },
    "ServiceNow": {
        "keywords": "ServiceNow Flow Designer OR ServiceNow ITSM OR ServiceNow release notes OR ServiceNow platform update",
        "category": "Digital Workflow / ITSM",
        "focus": "Flow Designer, platform automation, Now Assist, and AI integrations"
    },
    "Snowflake": {
        "keywords": "Snowflake Snowpark OR Snowflake Data Marketplace OR Snowflake Cortex OR Snowflake AI",
        "category": "Cloud Data Platform",
        "focus": "Snowpark, Data Marketplace, secure data sharing, and AI/ML workloads"
    },
    "Databricks": {
        "keywords": "Databricks Lakehouse OR MLflow OR Databricks Unity Catalog OR Databricks AI",
        "category": "Data & AI Platform",
        "focus": "Lakehouse architecture, MLflow, Delta Live Tables, and Unity Catalog"
    },
    "Palantir": {
        "keywords": "Palantir Foundry OR Palantir AIP OR Palantir Apollo OR Palantir AI Platform",
        "category": "Enterprise AI / Data Intelligence",
        "focus": "Foundry, AIP, operational AI, and defense applications"
    },
    "Gemini AI": {
        "keywords": "Google Gemini OR Gemini Pro OR Gemini Ultra OR Gemini Nano OR DeepMind Gemini",
        "category": "Multimodal AI Model",
        "focus": "Gemini models, multimodal reasoning, and integration with Google Workspace"
    },
    "Salesforce": {
        "keywords": "Salesforce Einstein OR Salesforce Data Cloud OR Service Cloud OR Slack GPT",
        "category": "CRM / Business Cloud",
        "focus": "Einstein AI, Data Cloud, automation, and GPT-powered CRM features"
    },
    "Nvidia": {
        "keywords": "Nvidia GPU OR CUDA OR RTX OR TensorRT OR Nvidia AI Enterprise",
        "category": "AI Hardware & Computing",
        "focus": "GPUs, CUDA SDKs, TensorRT, DGX servers, and AI Enterprise suite"
    }
}

# (Optional) Company logos (kept; remove if you’d like)
COMPANY_LOGOS = {
    "Google": "https://upload.wikimedia.org/wikipedia/commons/2/2f/Google_2015_logo.svg",
    "Microsoft": "https://upload.wikimedia.org/wikipedia/commons/4/44/Microsoft_logo.svg",
    "Amazon": "https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg",
    "Apple": "https://upload.wikimedia.org/wikipedia/commons/f/fa/Apple_logo_black.svg",
}

# ---------------------------
# Storage
# ---------------------------
def load_state() -> Dict[str, Any]:
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    if not os.path.exists(DATA_PATH):
        save_state(DEFAULT_STATE)
        return DEFAULT_STATE
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        state = json.load(f)
    if not state.get("companies") and not state.get("persons"):
        save_state(DEFAULT_STATE)
        return DEFAULT_STATE
    return state


def save_state(state: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def load_users():
    os.makedirs(os.path.dirname(USER_FILE), exist_ok=True)
    if not os.path.exists(USER_FILE):
        with open(USER_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_USER, f, indent=2)
        return DEFAULT_USER
    with open(USER_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


users = load_users()

# ---------------------------
# Helpers
# ---------------------------
def google_news_rss(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    q = requests.utils.quote(query)
    url = f"https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
    feed = feedparser.parse(url)
    items = []
    for e in feed.entries[:max_results]:
        items.append({
            "title": e.title,
            "link": e.link,
            "published": getattr(e, "published", ""),
            "summary": BeautifulSoup(getattr(e, "summary", ""), "html.parser").get_text()
        })
    return items


def sentiment(text: str) -> Tuple[str, float]:
    s = analyzer.polarity_scores(text or "")
    c = s["compound"]
    if c >= 0.05:
        return "Positive", c
    if c <= -0.05:
        return "Negative", c
    return "Neutral", c


def badge_for_sentiment(label: str) -> str:
    colors = {"Positive": "#22c55e", "Neutral": "#64748b", "Negative": "#ef4444"}
    return f'<span style="background:{colors[label]};color:white;padding:2px 8px;border-radius:999px;font-size:12px;">{label}</span>'


def render_tiles(items: List[Dict[str, Any]]):
    for card in items:
        title = card.get("title", "Untitled")
        summ = (card.get("summary") or "").strip()
        sent, _ = sentiment(f"{title}. {summ}")
        st.markdown(
            f"""
<div style="border:1px solid #e2e8f0;border-radius:10px;
box-shadow:0 1px 3px rgba(0,0,0,0.05);padding:12px;margin-bottom:10px;background:white;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
    <div style="font-weight:600;font-size:14px;line-height:1.3;">{title}</div>
    <div>{badge_for_sentiment(sent)}</div>
  </div>
  <div style="color:#475569;font-size:13px;min-height:40px;">{summ[:180] + ('…' if len(summ)>180 else '')}</div>
  <div style="margin-top:8px;font-size:12px;color:#64748b;">{card.get('published','')}</div>
  <div style="margin-top:8px;">
    <a href="{card.get('link','#')}" target="_blank"
       style="text-decoration:none;background:#0ea5e9;color:white;
       padding:6px 10px;border-radius:8px;font-size:12px;">Open</a>
  </div>
</div>
            """,
            unsafe_allow_html=True,
        )

# ---------------------------
# Session & State
# ---------------------------
if "state" not in st.session_state:
    st.session_state.state = load_state()
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# ---------------------------
# Header + Auto-refresh
# ---------------------------
st.title(APP_TITLE)

colA, colB, colC = st.columns([1, 5, 1])
with colA:
    refresh_minutes = st.selectbox("⏱ Refresh every:", [0, 5, 15, 30, 60], index=0, help="0 = No auto-refresh")
    if refresh_minutes > 0:
        st_autorefresh(interval=refresh_minutes * 60 * 1000, key="auto_refresh")

with colB:
    tz_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.caption(f"⏱ Last Fetched: {tz_now}")

with colC:
    if not st.session_state.is_admin:
        with st.expander("🔐 Admin Login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.button("Login"):
                stored = users.get("admin", {})
                if username == stored.get("username") and password == stored.get("password"):
                    st.session_state.is_admin = True
                    st.success("✅ Admin login successful!")
                else:
                    st.error("❌ Invalid credentials")
    else:
        if st.button("🚪 Logout"):
            st.session_state.is_admin = False
            st.success("Logged out")

st.markdown("---")

# Horizontal scroll for boards
st.markdown("<style>div[data-testid='stHorizontalBlock']{overflow-x:auto;}</style>", unsafe_allow_html=True)

# ---------------------------
# Tabs
# ---------------------------
if st.session_state.is_admin:
    tab_persons, tab_companies, tab_products, tab_admin = st.tabs(["🧑 Persons", "🏢 Companies", "🧩 Products", "⚙️ Admin"])
else:
    tab_persons, tab_companies, tab_products = st.tabs(["🧑 Persons", "🏢 Companies", "🧩 Products"])
    tab_admin = None

# ---------------------------
# Unified header helper
# ---------------------------
def board_header(title: str, subtitle: str):
    st.markdown(f"""
    <div style='text-align:center;padding:12px;background:#f8fafc;
    border-radius:8px;margin-bottom:20px;'>
      <h2 style='margin-bottom:4px;'>{title}</h2>
      <p style='color:#475569;font-size:15px;'>{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)

# ---------------------------
# Tab 1: Persons
# ---------------------------
with tab_persons:
    board_header("🧑 Person Intelligence Board", "🔍 Latest updates from influential tech leaders.")
    persons = st.session_state.state.get("persons", [])
    if not persons:
        st.info("No persons added yet.")
    else:
        cols = st.columns(min(len(persons), 4))
        for idx, p in enumerate(persons):
            with cols[idx % 4]:
                st.markdown(f"### {p['name']}")
                st.caption(f"**Company:** {p.get('company','-')}")
                st.markdown("---")
                news = google_news_rss(p["name"], max_results=5)
                render_tiles(news)

# ---------------------------
# Tab 2: Companies
# ---------------------------
with tab_companies:
    board_header("🏢 Company Intelligence Board", "📈 Live updates from major tech organizations.")
    companies = st.session_state.state.get("companies", [])
    if not companies:
        st.info("No companies added yet.")
    else:
        cols = st.columns(min(len(companies), 4))
        for idx, c in enumerate(companies):
            with cols[idx % 4]:
                # Company logo (kept) — remove these 3 lines if you don't want any logos at all
                logo = COMPANY_LOGOS.get(c["name"])
                if logo:
                    st.image(logo, width=80)
                st.markdown(f"### {c['name']}")
                st.caption(f"**Region:** {c.get('location','Global')}")
                st.markdown("---")
                news = google_news_rss(c["name"], max_results=6)
                render_tiles(news)

# ---------------------------
# Tab 3: Products (no logos)
# ---------------------------
with tab_products:
    board_header("🧩 Product Intelligence Board", "📊 Real-time updates and trends from top tech products.")
    product_names = list(PRODUCTS.keys())
    cols = st.columns(min(len(product_names), 4))
    for idx, pname in enumerate(product_names):
        info = PRODUCTS[pname]
        with cols[idx % 4]:
            # No logo here (per your request)
            st.markdown(f"### {pname}")
            st.caption(f"**Category:** {info['category']}")
            st.caption(f"**Focus:** {info['focus']}")
            st.markdown("---")
            news = google_news_rss(info["keywords"], max_results=5)
            render_tiles(news)

# ---------------------------
# Tab 4: Admin (unchanged)
# ---------------------------
if tab_admin:
    with tab_admin:
        st.subheader("⚙️ Admin Panel")
        st.markdown("### 🏢 Manage Companies")
        comp_name = st.text_input("➕ New Company Name")
        comp_loc = st.selectbox("Location", ["Global", "IN", "US"], key="comp_loc")
        if st.button("Add Company"):
            st.session_state.state["companies"].append({"name": comp_name, "location": comp_loc})
            save_state(st.session_state.state)
            st.success(f"Added {comp_name} ({comp_loc})")
