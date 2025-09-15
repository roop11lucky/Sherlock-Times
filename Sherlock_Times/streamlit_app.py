import os
import json
from datetime import datetime
from typing import Dict, List, Any, Tuple

import streamlit as st
import pandas as pd
import altair as alt
import feedparser
import requests
from bs4 import BeautifulSoup
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from streamlit_autorefresh import st_autorefresh

# ---------------------------
# App Config
# ---------------------------
st.set_page_config(page_title="Sherlock Times", page_icon="🕵️", layout="wide")

APP_TITLE = "🕵️ Sherlock Times – Company & Person News Dashboard"
DATA_PATH = os.path.join("data", "app_state.json")

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "sherlock-admin-123")

# Optional finance
try:
    import yfinance as yf
    HAS_YFIN = True
except Exception:
    HAS_YFIN = False

analyzer = SentimentIntensityAnalyzer()

# ---------------------------
# Default seed state
# ---------------------------
DEFAULT_STATE = {
    "companies": [
        {
            "name": "Google",
            "location": "IN",
            "ticker": "GOOGL",
            "careers_url": "https://careers.google.com/",
            "website": "https://about.google/",
            "competitors": ["Microsoft", "Amazon"]
        },
        {
            "name": "Microsoft",
            "location": "US",
            "ticker": "MSFT",
            "careers_url": "https://careers.microsoft.com/",
            "website": "https://www.microsoft.com/",
            "competitors": ["Google", "Amazon"]
        }
    ],
    "persons": [
        {"name": "Sundar Pichai", "company": "Google"},
        {"name": "Satya Nadella", "company": "Microsoft"}
    ]
}


# ---------------------------
# Storage
# ---------------------------
def load_state() -> Dict[str, Any]:
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    if not os.path.exists(DATA_PATH):
        save_state(DEFAULT_STATE)
        return json.loads(json.dumps(DEFAULT_STATE))

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        state = json.load(f)

    # Auto-seed if empty
    if not state.get("companies") and not state.get("persons"):
        save_state(DEFAULT_STATE)
        return json.loads(json.dumps(DEFAULT_STATE))

    return state


def save_state(state: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


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

colA, colB = st.columns([1, 5])
with colA:
    refresh_minutes = st.selectbox("⏱ Refresh every:", [0, 5, 15, 30, 60], index=0,
                                   help="0 = No auto-refresh")
    if refresh_minutes > 0:
        st_autorefresh(interval=refresh_minutes * 60 * 1000, key="auto_refresh")

with colB:
    tz_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.caption(f"⏱ Last Fetched: {tz_now}")

st.markdown("---")

# ---------------------------
# Tabs
# ---------------------------
tab_persons, tab_companies = st.tabs(["🧑 Persons", "🏢 Companies"])

with tab_persons:
    persons = st.session_state.state.get("persons", [])
    st.subheader("Latest News about People")
    person_news = []
    for p in persons:
        person_news += google_news_rss(p["name"], region="Global", max_results=6)
        if p.get("company"):
            person_news += google_news_rss(f'{p["name"]} {p["company"]}', region="Global", max_results=6)
    render_tiles(person_news, cols=3)

with tab_companies:
    companies = st.session_state.state.get("companies", [])
    st.subheader("Global News (All Companies)")
    all_news = []
    for c in companies:
        all_news += google_news_rss(c["name"], region=c.get("location", "Global"), max_results=6)
    render_tiles(all_news, cols=3)
