import streamlit as st
import feedparser
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from newspaper import Article
import requests
from bs4 import BeautifulSoup
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import pandas as pd
import altair as alt
import pytz
import os

# -------------------------------
# Config
# -------------------------------
st.set_page_config(page_title="Sherlock Times", page_icon="🕵️", layout="wide")

# -------------------------------
# Top Filters (proper top row, no sidebar)
# -------------------------------
st.markdown("### 🔧 Dashboard Controls")

col1, col2, col3 = st.columns([1, 1, 2], gap="large")

with col1:
    refresh_minutes = st.selectbox("⏱ Refresh every:", [5, 15, 30, 60], index=1)
    refresh_seconds = refresh_minutes * 60
    st_autorefresh(interval=refresh_seconds * 1000, key="dashboard_refresh")

with col2:
    override_loc = st.selectbox("🌍 Location Override", ["Off", "Global", "IN", "US"], index=0)

with col3:
    global_search = st.text_input("🔍 Global Search (applies to all)", placeholder="Type keyword...")

# -------------------------------
# File Paths
# -------------------------------
BASE_DIR = os.path.dirname(__file__)
COMPANY_FILE = os.path.join(BASE_DIR, "data", "companies.txt")
PERSON_FILE  = os.path.join(BASE_DIR, "data", "persons.txt")

# -------------------------------
# Load Entities
# -------------------------------
def load_entities(filename):
    entities, locations = [], {}
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line:
                    continue
                if "|" in line:
                    name, loc = line.split("|", 1)
                else:
                    name, loc = line, "Global"
                name, loc = name.strip(), loc.strip()
                entities.append(name)
                locations[name] = loc
    return entities, locations

if "entities" not in st.session_state or "client_locations" not in st.session_state:
    st.session_state.entities, st.session_state.client_locations = load_entities(COMPANY_FILE)

if "persons" not in st.session_state or "person_locations" not in st.session_state:
    st.session_state.persons, st.session_state.person_locations = load_entities(PERSON_FILE)

# -------------------------------
# Helpers
# -------------------------------
def resolve_redirect(url):
    try:
        r = requests.get(url, allow_redirects=True, timeout=5)
        return r.url
    except:
        return url

def clean_html(raw_html):
    try:
        soup = BeautifulSoup(raw_html, "html.parser")
        return soup.get_text()
    except:
        return raw_html

def fetch_news_rss(entity, loc="Global", max_results=10):
    if override_loc != "Off":
        loc = override_loc
    query = entity.replace(" ", "+")
    if loc == "IN":
        lang, gl, ceid = "en-IN", "IN", "IN:en"
    elif loc == "US":
        lang, gl, ceid = "en-US", "US", "US:en"
    else:
        lang, gl, ceid = "en", "US", "US:en"
    url = f"https://news.google.com/rss/search?q={query}&hl={lang}&gl={gl}&ceid={ceid}"
    feed = feedparser.parse(url)
    articles = []
    for entry in feed.entries[:max_results]:
        real_url = resolve_redirect(entry.link)
        summary = clean_html(entry.get("summary", ""))
        articles.append({
            "title": entry.title,
            "link": real_url,
            "published": entry.published,
            "tags": [entity],
            "summary": summary[:500],
            "location": loc
        })
    return articles

# -------------------------------
# Sentiment
# -------------------------------
analyzer = SentimentIntensityAnalyzer()
def get_sentiment(text):
    score = analyzer.polarity_scores(text)
    c = score["compound"]
    if c >= 0.05:
        return "Positive", c
    elif c <= -0.05:
        return "Negative", c
    return "Neutral", c

# -------------------------------
# Header
# -------------------------------
st.title("🕵️ Sherlock Times – Live News Dashboard")
tz = pytz.timezone("Asia/Kolkata")
last_fetched = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
st.markdown(f"⏱ **Last Fetched (IST):** {last_fetched}")
st.markdown(f"📅 **Today:** {datetime.now(tz).strftime('%A, %d %B %Y')}")

# -------------------------------
# Tabs
# -------------------------------
tab1, tab2 = st.tabs(["🏢 Companies", "🧑 Persons"])

# -------------------------------
# Tab 1: Companies
# -------------------------------
with tab1:
    st.subheader("🏢 Company Dashboard")

    client_articles = {}
    for entity in st.session_state.entities:
        loc = st.session_state.client_locations.get(entity, "Global")
        arts = fetch_news_rss(entity, loc)
        if global_search:
            arts = [a for a in arts if global_search.lower() in a["title"].lower()]
        client_articles[entity] = arts

    # Summary table
    summary_rows = []
    for client, arts in client_articles.items():
        if not arts: continue
        pos = neu = neg = 0
        for a in arts:
            s, _ = get_sentiment(a["summary"])
            if s == "Positive": pos += 1
            elif s == "Negative": neg += 1
            else: neu += 1
        summary_rows.append({
            "Client": f"[{client}](#{client.replace(' ', '_')})",
            "Location": st.session_state.client_locations.get(client, "Global"),
            "Articles": len(arts),
            "Positive": pos,
            "Neutral": neu,
            "Negative": neg,
            "Last Updated": last_fetched
        })

    if summary_rows:
        st.subheader("📊 Companies Summary")
        df_sum = pd.DataFrame(summary_rows)
        st.write(df_sum.to_markdown(index=False), unsafe_allow_html=True)

        # ➕ Add New Company right after table
        new_company = st.text_input("➕ Add a new Company (session only)", key="company_input")
        if st.button("Add Company", key="company_btn") and new_company:
            if new_company not in st.session_state.entities:
                st.session_state.entities.append(new_company)
                st.session_state.client_locations[new_company] = "Global"
                st.success(f"Added {new_company} to session watchlist")
            else:
                st.warning(f"{new_company} already exists")

    # Per-company sections
    for client, arts in client_articles.items():
        if not arts: continue
        st.markdown(f"<a name='{client.replace(' ', '_')}'></a>", unsafe_allow_html=True)
        st.header(f"🏢 {client}")
        for a in arts:
            s, sc = get_sentiment(a["summary"])
            icon = "🟢" if s == "Positive" else "🔴" if s == "Negative" else "⚪"
            with st.expander(f"{icon} {a['title']} ({a['published']})"):
                st.markdown(f"**Sentiment:** {s} ({sc:.2f})")
                st.write(a["summary"])
                st.markdown(f"[🔗 Read full article]({a['link']})")

# -------------------------------
# Tab 2: Persons
# -------------------------------
with tab2:
    st.subheader("🧑 Persons Dashboard")

    person_articles = {}
    for person in st.session_state.persons:
        loc = st.session_state.person_locations.get(person, "Global")
        arts = fetch_news_rss(person, loc)
        if global_search:
            arts = [a for a in arts if global_search.lower() in a["title"].lower()]
        person_articles[person] = arts

    summary_rows = []
    for person, arts in person_articles.items():
        if not arts: continue
        pos = neu = neg = 0
        for a in arts:
            s, _ = get_sentiment(a["summary"])
            if s == "Positive": pos += 1
            elif s == "Negative": neg += 1
            else: neu += 1
        summary_rows.append({
            "Person": f"[{person}](#{person.replace(' ', '_')})",
            "Location": st.session_state.person_locations.get(person, "Global"),
            "Articles": len(arts),
            "Positive": pos,
            "Neutral": neu,
            "Negative": neg,
            "Last Updated": last_fetched
        })

    if summary_rows:
        st.subheader("📊 Persons Summary")
        df_sum = pd.DataFrame(summary_rows)
        st.write(df_sum.to_markdown(index=False), unsafe_allow_html=True)

        # ➕ Add New Person right after table
        new_person = st.text_input("➕ Add a new Person (session only)", key="person_input")
        if st.button("Add Person", key="person_btn") and new_person:
            if new_person not in st.session_state.persons:
                st.session_state.persons.append(new_person)
                st.session_state.person_locations[new_person] = "Global"
                st.success(f"Added {new_person} to session watchlist")
            else:
                st.warning(f"{new_person} already exists")

    for person, arts in person_articles.items():
        if not arts: continue
        st.markdown(f"<a name='{person.replace(' ', '_')}'></a>", unsafe_allow_html=True)
        st.header(f"🧑 {person}")
        for a in arts:
            s, sc = get_sentiment(a["summary"])
            icon = "🟢" if s == "Positive" else "🔴" if s == "Negative" else "⚪"
            with st.expander(f"{icon} {a['title']} ({a['published']})"):
                st.markdown(f"**Sentiment:** {s} ({sc:.2f})")
                st.write(a["summary"])
                st.markdown(f"[🔗 Read full article]({a['link']})")
