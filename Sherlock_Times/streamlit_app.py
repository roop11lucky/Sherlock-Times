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
# CSS Grid Layout (Trello-style)
# ---------------------------
st.markdown("""
<style>
.grid-board {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-start;
  align-items: stretch;
  gap: 18px;
}

.card {
  flex: 1 1 calc(25% - 18px);
  min-width: 320px;
  max-width: 400px;
  background: #f8fafc;
  border-radius: 10px;
  padding: 15px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  display: flex;
  flex-direction: column;
  height: 520px;
  box-sizing: border-box;
}

.card h3 {
  margin-top: 0;
  margin-bottom: 5px;
  color: #0f172a;
}

.card p { margin: 3px 0; }

.card hr {
  border: none;
  border-top: 1px solid #e2e8f0;
  margin: 8px 0;
}

.scroll-area {
  flex-grow: 1;
  overflow-y: auto;
  padding-right: 5px;
}

.scroll-area::-webkit-scrollbar { width: 5px; }
.scroll-area::-webkit-scrollbar-thumb {
  background-color: #cbd5e1;
  border-radius: 4px;
}

@media (max-width: 1200px) {
  .card { flex: 1 1 calc(33.33% - 18px); }
}

@media (max-width: 900px) {
  .card { flex: 1 1 calc(50% - 18px); }
}

@media (max-width: 600px) {
  .card { flex: 1 1 100%; }
}
</style>
""", unsafe_allow_html=True)

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
    ],
    "products": [
        {"name": "OpenAI", "category": "Generative AI / API Platform",
         "focus": "GPT models, multimodal AI, API ecosystem, and enterprise integrations"},
        {"name": "ServiceNow", "category": "Digital Workflow / ITSM",
         "focus": "Flow Designer, platform automation, Now Assist, and AI integrations"},
        {"name": "Snowflake", "category": "Cloud Data Platform",
         "focus": "Snowpark, Data Marketplace, secure data sharing, and AI/ML workloads"},
        {"name": "Databricks", "category": "Data & AI Platform",
         "focus": "Lakehouse architecture, MLflow, Delta Live Tables, and Unity Catalog"},
        {"name": "Palantir", "category": "Enterprise AI / Data Intelligence",
         "focus": "Foundry, AIP, operational AI, and defense applications"},
        {"name": "Gemini AI", "category": "Multimodal AI Model",
         "focus": "Gemini models, multimodal reasoning, and integration with Google Workspace"},
        {"name": "Salesforce", "category": "CRM / Business Cloud",
         "focus": "Einstein AI, Data Cloud, automation, and GPT-powered CRM features"},
        {"name": "Nvidia", "category": "AI Hardware & Computing",
         "focus": "GPUs, CUDA SDKs, TensorRT, DGX servers, and AI Enterprise suite"}
    ]
}

DEFAULT_USER = {"admin": {"username": "sherlock", "password": "sherlock123"}}

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
    for key in ["companies", "persons", "products"]:
        if key not in state:
            state[key] = DEFAULT_STATE[key]
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

# ---------------------------
# Session Init (Always Load Latest)
# ---------------------------
st.session_state.state = load_state()
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# ---------------------------
# Header + Refresh
# ---------------------------
st.title(APP_TITLE)
colA, colB, colC = st.columns([1, 5, 1])
with colA:
    refresh_minutes = st.selectbox("⏱ Refresh every:", [0, 5, 15, 30, 60], index=0)
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
# Reload & Debug Controls
# ---------------------------
reload_col1, reload_col2 = st.columns([1, 1])
with reload_col1:
    if st.button("🔁 Reload from JSON"):
        st.session_state.state = load_state()
        st.success("✅ Reloaded dashboard data from app_state.json")

with reload_col2:
    with st.expander("📁 View Current Data (Debug)"):
        st.json(st.session_state.state)

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
    <div style='text-align:center;padding:12px;background:#f8fafc;border-radius:8px;margin-bottom:20px;'>
      <h2 style='margin-bottom:4px;'>{title}</h2>
      <p style='color:#475569;font-size:15px;'>{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)

# ---------------------------
# Grid Rendering (Fixed Alignment)
# ---------------------------
def render_entity_grid(items, build_info_html):
    if not items:
        st.info("No data available.")
        return
    html = "<div class='grid-board'>"
    for item in items:
        info_html = build_info_html(item)
        news = google_news_rss(item["name"], max_results=5)
        card_html = (
            "<div class='card'>"
            f"<h3>{item['name']}</h3>"
            f"{info_html}"
            "<hr><div class='scroll-area'>"
        )
        for n in news:
            title = n.get("title", "Untitled")
            summ = (n.get("summary") or "").strip()
            sent, _ = sentiment(f"{title}. {summ}")
            badge = badge_for_sentiment(sent)
            published = n.get("published", "")
            link = n.get("link", "#")
            preview = summ[:180] + ("…" if len(summ) > 180 else "")
            tile_html = (
                "<div style=\"border:1px solid #e2e8f0;border-radius:10px;"
                "box-shadow:0 1px 3px rgba(0,0,0,0.05);padding:12px;margin-bottom:10px;background:white;\">"
                "<div style=\"display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;\">"
                f"<div style=\"font-weight:600;font-size:14px;line-height:1.3;\">{title}</div>"
                f"<div>{badge}</div></div>"
                f"<div style=\"color:#475569;font-size:13px;min-height:40px;\">{preview}</div>"
                f"<div style=\"margin-top:8px;font-size:12px;color:#64748b;\">{published}</div>"
                "<div style=\"margin-top:8px;\">"
                f"<a href=\"{link}\" target=\"_blank\" "
                "style=\"text-decoration:none;background:#0ea5e9;color:white;"
                "padding:6px 10px;border-radius:8px;font-size:12px;\">Open</a></div></div>"
            )
            card_html += tile_html
        card_html += "</div></div>"
        html += card_html
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

# ---------------------------
# Tabs Rendering
# ---------------------------
with tab_persons:
    board_header("🧑 Person Intelligence Board", "🔍 Latest updates from influential tech leaders.")
    render_entity_grid(st.session_state.state["persons"], lambda p: f"<p><b>Company:</b> {p.get('company','-')}</p>")

with tab_companies:
    board_header("🏢 Company Intelligence Board", "📈 Live updates from major tech organizations.")
    render_entity_grid(st.session_state.state["companies"], lambda c: f"<p><b>Region:</b> {c.get('location','Global')}</p>")

with tab_products:
    board_header("🧩 Product Intelligence Board", "📊 Real-time updates and trends from top tech products.")
    render_entity_grid(st.session_state.state["products"], lambda p: f"<p><b>Category:</b> {p.get('category','')}</p><p><b>Focus:</b> {p.get('focus','')}</p>")

# ---------------------------
# Admin Tab
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
            selected = st.selectbox("Select Company", [c["name"] for c in st.session_state.state["companies"]])
            idx = next((i for i, c in enumerate(st.session_state.state["companies"]) if c["name"] == selected), None)
            if idx is not None:
                new_name = st.text_input("Edit Company Name", value=selected)
                new_loc = st.selectbox("Edit Location", ["Global", "IN", "US"], key="edit_comp_loc")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Save Company Changes"):
                        st.session_state.state["companies"][idx] = {"name": new_name, "location": new_loc}
                        save_state(st.session_state.state)
                        st.success("✅ Company updated!")
                with col2:
                    if st.button("Delete Company"):
                        st.session_state.state["companies"].pop(idx)
                        save_state(st.session_state.state)
                        st.warning("🗑️ Company deleted.")
        st.markdown("---")

        # Manage Persons
        st.markdown("### 🧑 Manage Persons")
        person_name = st.text_input("➕ New Person Name")
        company_link = st.text_input("Associated Company")
        if st.button("Add Person"):
            st.session_state.state["persons"].append({"name": person_name, "company": company_link})
            save_state(st.session_state.state)
            st.success(f"Added {person_name} (Company: {company_link})")

        if st.session_state.state["persons"]:
            selected_p = st.selectbox("Select Person", [p["name"] for p in st.session_state.state["persons"]])
            idx_p = next((i for i, p in enumerate(st.session_state.state["persons"]) if p["name"] == selected_p), None)
            if idx_p is not None:
                new_pname = st.text_input("Edit Person Name", value=selected_p)
                new_plink = st.text_input("Edit Associated Company", value=st.session_state.state["persons"][idx_p].get("company", ""))
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Save Person Changes"):
                        st.session_state.state["persons"][idx_p] = {"name": new_pname, "company": new_plink}
                        save_state(st.session_state.state)
                        st.success("✅ Person updated!")
                with col2:
                    if st.button("Delete Person"):
                        st.session_state.state["persons"].pop(idx_p)
                        save_state(st.session_state.state)
                        st.warning("🗑️ Person deleted.")
        st.markdown("---")

        # Manage Products
        st.markdown("### 🧩 Manage Products")
        prod_name = st.text_input("➕ New Product Name")
        prod_cat = st.text_input("Category")
        prod_focus = st.text_area("Focus Area")
        if st.button("Add Product"):
            st.session_state.state["products"].append({"name": prod_name, "category": prod_cat, "focus": prod_focus})
            save_state(st.session_state.state)
            st.success(f"Added product: {prod_name}")

        if st.session_state.state["products"]:
            selected_prod = st.selectbox("Select Product", [p["name"] for p in st.session_state.state["products"]])
            idx_prod = next((i for i, p in enumerate(st.session_state.state["products"]) if p["name"] == selected_prod), None)
            if idx_prod is not None:
                prod = st.session_state.state["products"][idx_prod]
                new_pname = st.text_input("Edit Product Name", value=prod["name"])
                new_cat = st.text_input("Edit Category", value=prod.get("category", ""))
                new_focus = st.text_area("Edit Focus", value=prod.get("focus", ""))
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Save Product Changes"):
                        st.session_state.state["products"][idx_prod] = {"name": new_pname, "category": new_cat, "focus": new_focus}
                        save_state(st.session_state.state)
                        st.success("✅ Product updated!")
                with col2:
                    if st.button("Delete Product"):
                        st.session_state.state["products"].pop(idx_prod)
                        save_state(st.session_state.state)
                        st.warning("🗑️ Product deleted.")
