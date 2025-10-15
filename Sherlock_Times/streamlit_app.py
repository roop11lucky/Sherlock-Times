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
# Product Information
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


def render_tiles(items: List[Dict[str, Any]], cols: int = 1):
    if not items:
        st.info("No items found.")
        return
    for card in items:
        title = card.get("title", "Untitled")
        summ = (card.get("summary") or "").strip()
        sent, score = sentiment(f"{title}. {summ}")
        st.markdown(
            f"""
<div style="border:1px solid #e5e7eb;border-radius:12px;padding:14px;margin-bottom:10px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
    <div style="font-weight:600;font-size:14px;line-height:1.3;">{title}</div>
    <div>{badge_for_sentiment(sent)}</div>
  </div>
  <div style="color:#475569;font-size:13px;min-height:40px;">{summ[:200] + ('…' if len(summ)>200 else '')}</div>
  <div style="margin-top:8px;font-size:12px;color:#64748b;">{card.get('published','')}</div>
  <div style="margin-top:8px;">
    <a href="{card.get('link','#')}" target="_blank" style="text-decoration:none;background:#0ea5e9;color:white;padding:6px 10px;border-radius:8px;font-size:12px;">Open</a>
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

# Enable horizontal scroll for Kanban layout
st.markdown(
    "<style>div[data-testid='stHorizontalBlock']{overflow-x:auto;}</style>",
    unsafe_allow_html=True,
)

# ---------------------------
# Tabs
# ---------------------------
if st.session_state.is_admin:
    tab_persons, tab_companies, tab_products, tab_admin = st.tabs(["🧑 Persons", "🏢 Companies", "🧩 Products", "⚙️ Admin"])
else:
    tab_persons, tab_companies, tab_products = st.tabs(["🧑 Persons", "🏢 Companies", "🧩 Products"])
    tab_admin = None

# ---------------------------
# Tab 1: Persons (Trello-style)
# ---------------------------
with tab_persons:
    persons = st.session_state.state.get("persons", [])
    st.subheader("🧑 Person Intelligence Board")

    if not persons:
        st.info("No persons added yet.")
    else:
        cols = st.columns(len(persons))
        for idx, p in enumerate(persons):
            with cols[idx]:
                st.markdown(f"### 🧑 {p['name']}")
                st.caption(f"**Company:** {p.get('company','-')}")
                st.markdown("---")

                person_news = google_news_rss(p["name"], max_results=4)
                if p.get("company"):
                    person_news += google_news_rss(f'{p["name"]} {p["company"]}', max_results=2)

                render_tiles(person_news, cols=1)

# ---------------------------
# Tab 2: Companies (Trello-style)
# ---------------------------
with tab_companies:
    companies = st.session_state.state.get("companies", [])
    st.subheader("🏢 Company Intelligence Board")

    if not companies:
        st.info("No companies added yet.")
    else:
        cols = st.columns(len(companies))
        for idx, c in enumerate(companies):
            with cols[idx]:
                st.markdown(f"### 🏢 {c['name']}")
                st.caption(f"**Region:** {c.get('location','Global')}")
                st.markdown("---")

                news_items = google_news_rss(c["name"], max_results=6)
                render_tiles(news_items, cols=1)

# ---------------------------
# Tab 3: Products (Trello-style)
# ---------------------------
with tab_products:
    st.subheader("🧩 Product Intelligence Board")
    st.caption("📊 Real-time updates and trends from top tech products.")

    product_names = list(PRODUCTS.keys())
    cols = st.columns(len(product_names))

    for idx, product_name in enumerate(product_names):
        info = PRODUCTS[product_name]
        with cols[idx]:
            st.markdown(f"### 🧩 {product_name}")
            st.caption(f"**Category:** {info['category']}")
            st.caption(f"**Focus:** {info['focus']}")
            st.markdown("---")

            query = info["keywords"]
            product_news = google_news_rss(query, max_results=5)
            render_tiles(product_news, cols=1)

# ---------------------------
# Tab 4: Admin Panel (unchanged)
# ---------------------------
if tab_admin:
    with tab_admin:
        st.subheader("⚙️ Admin Panel")

        # Manage Companies
        st.markdown("### 🏢 Manage Companies")
        comp_name = st.text_input("➕ New Company Name")
        comp_loc = st.selectbox("Location", ["Global", "IN", "US"], key="comp_loc")
        if st.button("Add Company"):
            st.session_state.state["companies"].append({"name": comp_name, "location": comp_loc})
            save_state(st.session_state.state)
            st.success(f"Added {comp_name} ({comp_loc})")

        if st.session_state.state["companies"]:
            st.markdown("#### ✏️ Edit / Delete Company")
            selected = st.selectbox("Select Company", [c["name"] for c in st.session_state.state["companies"]])
            idx = next((i for i, c in enumerate(st.session_state.state["companies"]) if c["name"] == selected), None)
            if idx is not None:
                company = st.session_state.state["companies"][idx]
                new_name = st.text_input("Company Name", value=company["name"], key="edit_comp_name")
                new_loc = st.selectbox("Location", ["Global", "IN", "US"],
                                       index=["Global", "IN", "US"].index(company.get("location", "Global")),
                                       key="edit_comp_loc")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Save Changes", key="save_comp"):
                        company["name"] = new_name
                        company["location"] = new_loc
                        save_state(st.session_state.state)
                        st.success("Company updated successfully!")
                with col2:
                    if st.button("Delete", key="delete_comp"):
                        st.session_state.state["companies"].pop(idx)
                        save_state(st.session_state.state)
                        st.warning("Company deleted!")

        # Manage Persons
        st.markdown("### 🧑 Manage Persons")
        person_name = st.text_input("➕ New Person Name")
        company_link = st.text_input("Associated Company")
        if st.button("Add Person"):
            st.session_state.state["persons"].append({"name": person_name, "company": company_link})
            save_state(st.session_state.state)
            st.success(f"Added {person_name} (Company: {company_link})")

        if st.session_state.state["persons"]:
            st.markdown("#### ✏️ Edit / Delete Person")
            selected_p = st.selectbox("Select Person", [p["name"] for p in st.session_state.state["persons"]])
            idx_p = next((i for i, p in enumerate(st.session_state.state["persons"]) if p["name"] == selected_p), None)
            if idx_p is not None:
                person = st.session_state.state["persons"][idx_p]
                new_pname = st.text_input("Person Name", value=person["name"], key="edit_person_name")
                new_plink = st.text_input("Associated Company", value=person.get("company", ""), key="edit_person_link")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Save Changes", key="save_person"):
                        person["name"] = new_pname
                        person["company"] = new_plink
                        save_state(st.session_state.state)
                        st.success("Person updated successfully!")
                with col2:
                    if st.button("Delete", key="delete_person"):
                        st.session_state.state["persons"].pop(idx_p)
                        save_state(st.session_state.state)
                        st.warning("Person deleted!")
