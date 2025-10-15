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
# Product Information (Static)
# ---------------------------
PRODUCT_INFO = {
    "OpenAI": {
        "description": "Creator of ChatGPT, DALL·E, Whisper, and API platform for generative AI innovation.",
        "category": "Artificial Intelligence / NLP",
        "website": "https://openai.com",
        "logo": "https://upload.wikimedia.org/wikipedia/commons/4/4d/OpenAI_Logo.svg"
    },
    "ServiceNow": {
        "description": "Cloud-based workflow automation platform enabling digital transformation and enterprise service management.",
        "category": "Workflow Automation / ITSM",
        "website": "https://www.servicenow.com",
        "logo": "https://upload.wikimedia.org/wikipedia/commons/6/64/ServiceNow_logo.svg"
    },
    "Snowflake": {
        "description": "Cloud data warehouse enabling secure data sharing and analytics at scale.",
        "category": "Cloud Data Platform",
        "website": "https://www.snowflake.com",
        "logo": "https://upload.wikimedia.org/wikipedia/commons/f/ff/Snowflake_Logo.svg"
    },
    "Databricks": {
        "description": "Unified analytics platform for data engineering, machine learning, and AI collaboration built on Apache Spark.",
        "category": "Data & AI Platform",
        "website": "https://www.databricks.com",
        "logo": "https://upload.wikimedia.org/wikipedia/commons/5/5f/Databricks_logo.svg"
    },
    "Palantir": {
        "description": "Software company specializing in big data analytics and enterprise AI systems for decision intelligence.",
        "category": "Enterprise AI / Data Integration",
        "website": "https://www.palantir.com",
        "logo": "https://upload.wikimedia.org/wikipedia/commons/2/28/Palantir_Technologies_logo.svg"
    },
    "Gemini AI": {
        "description": "Google DeepMind’s next-generation multimodal AI model powering Gemini Pro, Gemini Ultra, and Gemini Nano.",
        "category": "AI / Multimodal LLM",
        "website": "https://deepmind.google/technologies/gemini/",
        "logo": "https://upload.wikimedia.org/wikipedia/commons/3/3c/Google_Gemini_logo.svg"
    },
    "Salesforce": {
        "description": "Customer Relationship Management (CRM) platform with AI, analytics, and automation capabilities.",
        "category": "CRM / Cloud Platform",
        "website": "https://www.salesforce.com",
        "logo": "https://upload.wikimedia.org/wikipedia/commons/f/f9/Salesforce.com_logo.svg"
    },
    "Nvidia": {
        "description": "Global leader in GPUs, AI computing, and data center platforms driving innovation in AI and visualization.",
        "category": "Semiconductors / AI Computing",
        "website": "https://www.nvidia.com",
        "logo": "https://upload.wikimedia.org/wikipedia/en/2/21/Nvidia_logo.svg"
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
def google_news_rss(query: str, region: str = "Global", max_results: int = 12) -> List[Dict[str, Any]]:
    q = requests.utils.quote(query)
    if region == "IN":
        hl, gl, ceid = "en-IN", "IN", "IN:en"
    elif region == "US":
        hl, gl, ceid = "en-US", "US", "US:en"
    else:
        hl, gl, ceid = "en", "US", "US:en"
    url = f"https://news.google.com/rss/search?q={q}&hl={hl}&gl={gl}&ceid={ceid}"
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


def render_tiles(items: List[Dict[str, Any]], cols: int = 3):
    if not items:
        st.info("No items found.")
        return
    for i in range(0, len(items), cols):
        row = st.columns(cols)
        for j, card in enumerate(items[i:i + cols]):
            with row[j]:
                title = card.get("title", "Untitled")
                summ = (card.get("summary") or "").strip()
                sent, score = sentiment(f"{title}. {summ}")
                st.markdown(
                    f"""
<div style="border:1px solid #e5e7eb;border-radius:12px;padding:14px;height:100%;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
    <div style="font-weight:600;font-size:15px;line-height:1.3;">{title}</div>
    <div>{badge_for_sentiment(sent)}</div>
  </div>
  <div style="color:#475569;font-size:13px;min-height:52px;">{summ[:220] + ('…' if len(summ)>220 else '')}</div>
  <div style="margin-top:10px;font-size:12px;color:#64748b;">
    {card.get('published','')}
  </div>
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

# ---------------------------
# Tabs
# ---------------------------
if st.session_state.is_admin:
    tab_persons, tab_companies, tab_products, tab_admin = st.tabs(["🧑 Persons", "🏢 Companies", "🧩 Products", "⚙️ Admin"])
else:
    tab_persons, tab_companies, tab_products = st.tabs(["🧑 Persons", "🏢 Companies", "🧩 Products"])
    tab_admin = None

# ---------------------------
# Tab 1: Persons
# ---------------------------
with tab_persons:
    persons = st.session_state.state.get("persons", [])
    st.subheader("Latest News about People")
    for p in persons:
        st.markdown(f"### 🧑 {p['name']} ({p.get('company','')})")
        person_news = google_news_rss(p["name"], region="Global", max_results=6)
        if p.get("company"):
            person_news += google_news_rss(f'{p["name"]} {p["company"]}', region="Global", max_results=6)
        render_tiles(person_news, cols=3)

# ---------------------------
# Tab 2: Companies
# ---------------------------
with tab_companies:
    companies = st.session_state.state.get("companies", [])
    st.subheader("Company-wise News")
    for c in companies:
        st.markdown(f"### 🏢 {c['name']} ({c.get('location','Global')})")
        news_items = google_news_rss(c["name"], region=c.get("location", "Global"), max_results=6)
        render_tiles(news_items, cols=3)

# ---------------------------
# Tab 3: Products
# ---------------------------
with tab_products:
    st.subheader("Product Intelligence Hub")

    selected_product = st.selectbox("Select Product", list(PRODUCT_INFO.keys()))
    info = PRODUCT_INFO[selected_product]

    col1, col2 = st.columns([1, 4])
    with col1:
        st.image(info["logo"], width=120)
    with col2:
        st.markdown(f"### {selected_product}")
        st.markdown(f"**Category:** {info['category']}")
        st.markdown(f"**Description:** {info['description']}")
        st.markdown(f"🌐 [Visit Website]({info['website']})")

    st.markdown("---")
    st.markdown(f"### 📰 Latest {selected_product} News")
    product_news = google_news_rss(selected_product, region="Global", max_results=6)
    render_tiles(product_news, cols=3)

# ---------------------------
# Tab 4: Admin (CRUD)
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
