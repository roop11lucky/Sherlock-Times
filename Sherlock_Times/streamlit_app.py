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
st.set_page_config(page_title="🕵️ Sherlock Times", page_icon="🕵️", layout="wide")
APP_TITLE = "🕵️ Sherlock Times – Company, Person & Product News Dashboard"

# ---------------------------
# File Paths (auto-detect for Cloud)
# ---------------------------
possible_paths = [
    os.path.join(os.path.dirname(__file__), "data"),
    os.path.join(os.path.dirname(__file__), "..", "data")
]
DATA_DIR = next((p for p in possible_paths if os.path.exists(p)), possible_paths[0])
DATA_PATH = os.path.join(DATA_DIR, "app_state.json")
USER_FILE = os.path.join(DATA_DIR, "users.json")
os.makedirs(DATA_DIR, exist_ok=True)

# ---------------------------
# Analyzer
# ---------------------------
analyzer = SentimentIntensityAnalyzer()

# ---------------------------
# Default Data
# ---------------------------
DEFAULT_STATE = {
    "companies": [
        {"name": "Google", "location": "IN"},
        {"name": "Microsoft", "location": "US"}
    ],
    "persons": [
        {"name": "Sundar Pichai", "company": "Google"},
        {"name": "Satya Nadella", "company": "Microsoft"}
    ],
    "products": [
        {"name": "OpenAI", "category": "Generative AI / API Platform",
         "focus": "GPT models, multimodal AI, API ecosystem, and enterprise integrations"},
        {"name": "ServiceNow", "category": "Digital Workflow / ITSM",
         "focus": "Flow Designer, platform automation, Now Assist, and AI integrations"},
        {"name": "Snowflake", "category": "Cloud Data Platform",
         "focus": "Snowpark, Data Marketplace, secure data sharing, and AI/ML workloads"}
    ]
}
DEFAULT_USER = {"admin": {"username": "sherlock", "password": "sherlock123"}}

# ---------------------------
# Load / Save Helpers
# ---------------------------
def load_state() -> Dict[str, Any]:
    if not os.path.exists(DATA_PATH):
        save_state(DEFAULT_STATE)
        return DEFAULT_STATE
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            for key in ["companies", "persons", "products"]:
                if key not in data:
                    data[key] = DEFAULT_STATE[key]
            return data
        except Exception:
            return DEFAULT_STATE

def save_state(state: Dict[str, Any]) -> None:
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def load_users():
    if not os.path.exists(USER_FILE):
        with open(USER_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_USER, f, indent=2)
        return DEFAULT_USER
    with open(USER_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

users = load_users()

# ---------------------------
# News + Sentiment
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
# Header + Auto-refresh + Login
# ---------------------------
st.title(APP_TITLE)
colA, colB, colC = st.columns([1, 5, 1])
with colA:
    refresh_minutes = st.selectbox("⏱ Refresh every:", [0, 5, 15, 30, 60], index=2, help="0 = No auto-refresh")
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

def board_header(title: str, subtitle: str):
    st.markdown(f"""
    <div style='text-align:center;padding:12px;background:#f8fafc;
    border-radius:8px;margin-bottom:20px;'>
      <h2 style='margin-bottom:4px;'>{title}</h2>
      <p style='color:#475569;font-size:15px;'>{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)

# ---------------------------
# Persons Tab
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
# Companies Tab
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
                st.markdown(f"### {c['name']}")
                st.caption(f"**Region:** {c.get('location','Global')}")
                st.markdown("---")
                news = google_news_rss(c["name"], max_results=6)
                render_tiles(news)

# ---------------------------
# Products Tab
# ---------------------------
with tab_products:
    board_header("🧩 Product Intelligence Board", "📊 Real-time updates and trends from top tech products.")
    products = st.session_state.state.get("products", [])
    if not products:
        st.info("No products added yet.")
    else:
        cols = st.columns(min(len(products), 4))
        for idx, p in enumerate(products):
            with cols[idx % 4]:
                st.markdown(f"### {p['name']}")
                st.caption(f"**Category:** {p.get('category','')}")
                st.caption(f"**Focus:** {p.get('focus','')}")
                st.markdown("---")
                news = google_news_rss(p["name"], max_results=5)
                render_tiles(news)

# ---------------------------
# Admin Tab
# ---------------------------
if tab_admin:
    with tab_admin:
        st.subheader("⚙️ Admin Panel")
        st.caption("All changes are saved to data/app_state.json automatically.")

        state = st.session_state.state

        # Companies
        st.markdown("### 🏢 Manage Companies")
        comp_name = st.text_input("➕ New Company Name")
        comp_loc = st.selectbox("Location", ["Global", "IN", "US"], key="comp_loc")
        if st.button("Add Company"):
            state["companies"].append({"name": comp_name, "location": comp_loc})
            save_state(state)
            st.success(f"Added {comp_name} ({comp_loc})")

        if state["companies"]:
            selected = st.selectbox("Select Company", [c["name"] for c in state["companies"]])
            idx = next((i for i, c in enumerate(state["companies"]) if c["name"] == selected), None)
            if idx is not None:
                new_name = st.text_input("Edit Company Name", value=selected)
                new_loc = st.selectbox("Edit Location", ["Global", "IN", "US"], key="edit_comp_loc")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Save Company Changes"):
                        state["companies"][idx] = {"name": new_name, "location": new_loc}
                        save_state(state)
                        st.success("✅ Company updated!")
                with col2:
                    if st.button("Delete Company"):
                        state["companies"].pop(idx)
                        save_state(state)
                        st.warning("🗑️ Company deleted.")

        st.markdown("---")

        # Persons
        st.markdown("### 🧑 Manage Persons")
        person_name = st.text_input("➕ New Person Name")
        company_link = st.text_input("Associated Company")
        if st.button("Add Person"):
            state["persons"].append({"name": person_name, "company": company_link})
            save_state(state)
            st.success(f"Added {person_name} (Company: {company_link})")

        if state["persons"]:
            selected_p = st.selectbox("Select Person", [p["name"] for p in state["persons"]])
            idx_p = next((i for i, p in enumerate(state["persons"]) if p["name"] == selected_p), None)
            if idx_p is not None:
                new_pname = st.text_input("Edit Person Name", value=selected_p)
                new_plink = st.text_input("Edit Associated Company", value=state["persons"][idx_p].get("company", ""))
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Save Person Changes"):
                        state["persons"][idx_p] = {"name": new_pname, "company": new_plink}
                        save_state(state)
                        st.success("✅ Person updated!")
                with col2:
                    if st.button("Delete Person"):
                        state["persons"].pop(idx_p)
                        save_state(state)
                        st.warning("🗑️ Person deleted.")

        st.markdown("---")

        # Products
        st.markdown("### 🧩 Manage Products")
        prod_name = st.text_input("➕ New Product Name")
        prod_cat = st.text_input("Category")
        prod_focus = st.text_area("Focus Area")
        if st.button("Add Product"):
            state["products"].append({"name": prod_name, "category": prod_cat, "focus": prod_focus})
            save_state(state)
            st.success(f"Added product: {prod_name}")

        if state["products"]:
            selected_prod = st.selectbox("Select Product", [p["name"] for p in state["products"]])
            idx_prod = next((i for i, p in enumerate(state["products"]) if p["name"] == selected_prod), None)
            if idx_prod is not None:
                prod = state["products"][idx_prod]
                new_pname = st.text_input("Edit Product Name", value=prod["name"])
                new_cat = st.text_input("Edit Category", value=prod.get("category", ""))
                new_focus = st.text_area("Edit Focus", value=prod.get("focus", ""))
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Save Product Changes"):
                        state["products"][idx_prod] = {
                            "name": new_pname,
                            "category": new_cat,
                            "focus": new_focus
                        }
                        save_state(state)
                        st.success("✅ Product updated!")
                with col2:
                    if st.button("Delete Product"):
                        state["products"].pop(idx_prod)
                        save_state(state)
                        st.warning("🗑️ Product deleted.")
