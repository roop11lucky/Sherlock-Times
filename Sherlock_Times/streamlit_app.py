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
# Sidebar Global Filters
# -------------------------------
refresh_minutes = st.sidebar.selectbox("⏱ Refresh every:", [5, 15, 30, 60], index=1)
refresh_seconds = refresh_minutes * 60
st_autorefresh(interval=refresh_seconds * 1000, key="dashboard_refresh")

override_loc = st.sidebar.selectbox("🌍 Override All Locations", ["Off", "Global", "IN", "US"], index=0)
global_search = st.sidebar.text_input("🔍 Global Search (keywords)")

# -------------------------------
# File Paths
# -------------------------------
BASE_DIR = os.path.dirname(__file__)
COMPANY_FILE = os.path.join(BASE_DIR, "data", "companies.txt")
PERSON_FILE = os.path.join(BASE_DIR, "data", "persons.txt")

# -------------------------------
# Load Entities (Companies / Persons)
# -------------------------------
def load_entities(filename):
    entities, locations = [], {}
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if "|" in line:
                    name, loc = line.split("|", 1)
                else:
                    name, loc = line, "Global"
                entities.append(name.strip())
                locations[name.strip()] = loc.strip()
    else:
        st.error(f"⚠️ File {filename} not found!")
    return entities, locations

if "entities" not in st.session_state or "client_locations" not in st.session_state:
    st.session_state.entities, st.session_state.client_locations = load_entities(COMPANY_FILE)

if "persons" not in st.session_state or "person_locations" not in st.session_state:
    st.session_state.persons, st.session_state.person_locations = load_entities(PERSON_FILE)

# -------------------------------
# Helper Functions
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

def fetch_article_preview(url):
    try:
        article = Article(url)
        article.download()
        article.parse()
        article.nlp()
        snippet = article.text[:500] + "..." if article.text else None
        summary = article.summary if article.summary else snippet
        img = article.top_image
        if img and ("gstatic" in img or "googleusercontent" in img):
            img = None
        return snippet, summary, img
    except:
        return None, None, None

# Sentiment Analysis
analyzer = SentimentIntensityAnalyzer()
def get_sentiment(text):
    score = analyzer.polarity_scores(text)
    compound = score["compound"]
    if compound >= 0.05:
        return "Positive", compound
    elif compound <= -0.05:
        return "Negative", compound
    else:
        return "Neutral", compound

# -------------------------------
# Dashboard Header
# -------------------------------
st.title("🕵️ Sherlock Times – Live News Dashboard")

tz = pytz.timezone("Asia/Kolkata")
last_fetched = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
st.markdown(f"⏱ **Last Fetched (IST):** {last_fetched}")
st.markdown(f"📅 **Today:** {datetime.now(tz).strftime('%A, %d %B %Y')}")

# -------------------------------
# Tabs: Companies & Persons
# -------------------------------
tab1, tab2 = st.tabs(["🏢 Companies", "🧑 Persons"])

# -------------------------------
# Tab 1: Companies
# -------------------------------
with tab1:
    st.subheader("🏢 Company Dashboard")

    selected_companies = st.multiselect(
        "📌 Select Companies to Display",
        st.session_state.entities,
        default=st.session_state.entities
    )

    # Fetch Articles
    client_articles = {}
    for entity in selected_companies:
        loc = st.session_state.client_locations.get(entity, "Global")
        client_articles[entity] = fetch_news_rss(entity, loc)

    # Summary Table
    summary_records = []
    for client, articles in client_articles.items():
        if global_search:
            articles = [a for a in articles if global_search.lower() in a["title"].lower()]
        if not articles:
            continue
        pos = neu = neg = 0
        for art in articles:
            sentiment, _ = get_sentiment(art["summary"])
            if sentiment == "Positive": pos += 1
            elif sentiment == "Negative": neg += 1
            else: neu += 1
        summary_records.append({
            "Client": f"[{client}](#{client.replace(' ', '_')})",
            "Location": st.session_state.client_locations.get(client, "Global"),
            "Articles": len(articles),
            "Positive": pos,
            "Neutral": neu,
            "Negative": neg,
            "Last Updated": last_fetched
        })
    if summary_records:
        df_summary = pd.DataFrame(summary_records)
        st.write(df_summary.to_markdown(index=False), unsafe_allow_html=True)

    # Per-Company Sections
    for client, articles in client_articles.items():
        if global_search:
            articles = [a for a in articles if global_search.lower() in a["title"].lower()]
        if not articles:
            continue
        st.markdown(f"<a name='{client.replace(' ', '_')}'></a>", unsafe_allow_html=True)
        st.header(f"🏢 {client} ({st.session_state.client_locations[client]})")

        records = []
        for art in articles:
            sentiment, score = get_sentiment(art["summary"])
            records.append({"Title": art["title"], "Sentiment": sentiment, "Score": score})
        df = pd.DataFrame(records)
        if not df.empty:
            chart = alt.Chart(df).mark_arc().encode(
                theta="count():Q", color="Sentiment:N"
            ).properties(title=f"{client} Sentiment Distribution")
            st.altair_chart(chart, use_container_width=True)

        for art in articles:
            sentiment, score = get_sentiment(art["summary"])
            sentiment_icon = "🟢" if sentiment == "Positive" else "🔴" if sentiment == "Negative" else "⚪"
            with st.expander(f"{sentiment_icon} {art['title']} ({art['published']})"):
                st.markdown(f"**Sentiment:** {sentiment} ({score:.2f})")
                st.write(art["summary"])
                snippet, summary, img = fetch_article_preview(art["link"])
                if summary: st.markdown("**📝 AI Summary:**"); st.write(summary)
                if img: st.image(img, width=600)
                st.markdown(f"[🔗 Read full article]({art['link']})")

# -------------------------------
# Tab 2: Persons
# -------------------------------
with tab2:
    st.subheader("🧑 Persons Dashboard")

    selected_persons = st.multiselect(
        "📌 Select Persons to Display",
        st.session_state.persons,
        default=st.session_state.persons
    )

    # Fetch Articles
    person_articles = {}
    for person in selected_persons:
        loc = st.session_state.person_locations.get(person, "Global")
        person_articles[person] = fetch_news_rss(person, loc)

    # Summary Table
    summary_records = []
    for person, articles in person_articles.items():
        if global_search:
            articles = [a for a in articles if global_search.lower() in a["title"].lower()]
        if not articles:
            continue
        pos = neu = neg = 0
        for art in articles:
            sentiment, _ = get_sentiment(art["summary"])
            if sentiment == "Positive": pos += 1
            elif sentiment == "Negative": neg += 1
            else: neu += 1
        summary_records.append({
            "Person": f"[{person}](#{person.replace(' ', '_')})",
            "Location": st.session_state.person_locations.get(person, "Global"),
            "Articles": len(articles),
            "Positive": pos,
            "Neutral": neu,
            "Negative": neg,
            "Last Updated": last_fetched
        })
    if summary_records:
        df_summary = pd.DataFrame(summary_records)
        st.write(df_summary.to_markdown(index=False), unsafe_allow_html=True)

    # Per-Person Sections
    for person, articles in person_articles.items():
        if global_search:
            articles = [a for a in articles if global_search.lower() in a["title"].lower()]
        if not articles:
            continue
        st.markdown(f"<a name='{person.replace(' ', '_')}'></a>", unsafe_allow_html=True)
        st.header(f"🧑 {person} ({st.session_state.person_locations[person]})")

        records = []
        for art in articles:
            sentiment, score = get_sentiment(art["summary"])
            records.append({"Title": art["title"], "Sentiment": sentiment, "Score": score})
        df = pd.DataFrame(records)
        if not df.empty:
            chart = alt.Chart(df).mark_arc().encode(
                theta="count():Q", color="Sentiment:N"
            ).properties(title=f"{person} Sentiment Distribution")
            st.altair_chart(chart, use_container_width=True)

        for art in articles:
            sentiment, score = get_sentiment(art["summary"])
            sentiment_icon = "🟢" if sentiment == "Positive" else "🔴" if sentiment == "Negative" else "⚪"
            with st.expander(f"{sentiment_icon} {art['title']} ({art['published']})"):
                st.markdown(f"**Sentiment:** {sentiment} ({score:.2f})")
                st.write(art["summary"])
                snippet, summary, img = fetch_article_preview(art["link"])
                if summary: st.markdown("**📝 AI Summary:**"); st.write(summary)
                if img: st.image(img, width=600)
                st.markdown(f"[🔗 Read full article]({art['link']})")
