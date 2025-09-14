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
# Sidebar: Global Filters
# -------------------------------
refresh_minutes = st.sidebar.selectbox("⏱ Refresh every:", [5, 15, 30, 60], index=1)
refresh_seconds = refresh_minutes * 60
st_autorefresh(interval=refresh_seconds * 1000, key="dashboard_refresh")

override_loc = st.sidebar.selectbox("🌍 Override All Locations", ["Off", "Global", "IN", "US"], index=0)
global_search = st.sidebar.text_input("🔍 Global Search (filters both tabs)")

# -------------------------------
# File Paths
# -------------------------------
BASE_DIR = os.path.dirname(__file__)
COMPANY_FILE = os.path.join(BASE_DIR, "data", "companies.txt")
PERSON_FILE  = os.path.join(BASE_DIR, "data", "persons.txt")

# -------------------------------
# Load Entities (Companies / Persons)
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
    else:
        st.error(f"⚠️ File {filename} not found!")
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
    # Respect global override if set
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

# Sentiment
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

    # Per-tab selection
    selected_companies = st.multiselect(
        "📌 Select Companies to Display",
        st.session_state.entities,
        default=st.session_state.entities
    )

    # Quick Search (one-time; NOT saved)
    quick_search_company = st.text_input("🔎 Quick Search Company (one-time, not saved)")
    if quick_search_company:
        st.markdown(f"**📢 Quick Results for:** {quick_search_company}")
        quick_articles = fetch_news_rss(quick_search_company)
        for art in quick_articles:
            sentiment, score = get_sentiment(art["summary"])
            icon = "🟢" if sentiment == "Positive" else "🔴" if sentiment == "Negative" else "⚪"
            with st.expander(f"{icon} {art['title']} ({art['published']})"):
                st.markdown(f"**Sentiment:** {sentiment} ({score:.2f})")
                st.write(art["summary"])
                snip, summ, img = fetch_article_preview(art["link"])
                if summ: st.markdown("**📝 AI Summary:**"); st.write(summ)
                if img:  st.image(img, width=600)
                st.markdown(f"[🔗 Read full article]({art['link']})")
        st.divider()

    # Fetch & filter articles for selected companies
    client_articles = {}
    for entity in selected_companies:
        loc = st.session_state.client_locations.get(entity, "Global")
        arts = fetch_news_rss(entity, loc)
        if global_search:
            arts = [a for a in arts if global_search.lower() in a["title"].lower()]
        client_articles[entity] = arts

    # Summary table (clickable)
    summary_rows = []
    for client, arts in client_articles.items():
        if not arts:
            continue
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
        df_sum = pd.DataFrame(summary_rows)
        st.subheader("📊 Company Summary (click client to jump)")
        st.write(df_sum.to_markdown(index=False), unsafe_allow_html=True)

    # Per-company sections
    for client, arts in client_articles.items():
        if not arts:
            continue
        st.markdown(f"<a name='{client.replace(' ', '_')}'></a>", unsafe_allow_html=True)
        st.header(f"🏢 {client} ({st.session_state.client_locations.get(client, 'Global')})")

        recs = []
        for a in arts:
            s, sc = get_sentiment(a["summary"])
            recs.append({"Title": a["title"], "Sentiment": s, "Score": sc})
        df = pd.DataFrame(recs)

        if not df.empty:
            chart = alt.Chart(df).mark_arc().encode(
                theta="count():Q", color="Sentiment:N"
            ).properties(title=f"{client} Sentiment Distribution")
            st.altair_chart(chart, use_container_width=True)

        for a in arts:
            s, sc = get_sentiment(a["summary"])
            icon = "🟢" if s == "Positive" else "🔴" if s == "Negative" else "⚪"
            with st.expander(f"{icon} {a['title']} ({a['published']})"):
                st.markdown(f"**Sentiment:** {s} ({sc:.2f})")
                st.write(a["summary"])
                snip, summ, img = fetch_article_preview(a["link"])
                if summ: st.markdown("**📝 AI Summary:**"); st.write(summ)
                if img:  st.image(img, width=600)
                st.markdown(f"[🔗 Read full article]({a['link']})")

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

    # Quick Search (one-time; NOT saved)
    quick_search_person = st.text_input("🔎 Quick Search Person (one-time, not saved)")
    if quick_search_person:
        st.markdown(f"**📢 Quick Results for:** {quick_search_person}")
        quick_articles = fetch_news_rss(quick_search_person)
        for art in quick_articles:
            sentiment, score = get_sentiment(art["summary"])
            icon = "🟢" if sentiment == "Positive" else "🔴" if sentiment == "Negative" else "⚪"
            with st.expander(f"{icon} {art['title']} ({art['published']})"):
                st.markdown(f"**Sentiment:** {sentiment} ({score:.2f})")
                st.write(art["summary"])
                snip, summ, img = fetch_article_preview(art["link"])
                if summ: st.markdown("**📝 AI Summary:**"); st.write(summ)
                if img:  st.image(img, width=600)
                st.markdown(f"[🔗 Read full article]({art['link']})")
        st.divider()

    # Fetch & filter articles for selected persons
    person_articles = {}
    for person in selected_persons:
        loc = st.session_state.person_locations.get(person, "Global")
        arts = fetch_news_rss(person, loc)
        if global_search:
            arts = [a for a in arts if global_search.lower() in a["title"].lower()]
        person_articles[person] = arts

    # Summary table (clickable)
    summary_rows = []
    for person, arts in person_articles.items():
        if not arts:
            continue
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
        df_sum = pd.DataFrame(summary_rows)
        st.subheader("📊 Persons Summary (click name to jump)")
        st.write(df_sum.to_markdown(index=False), unsafe_allow_html=True)

    # Per-person sections
    for person, arts in person_articles.items():
        if not arts:
            continue
        st.markdown(f"<a name='{person.replace(' ', '_')}'></a>", unsafe_allow_html=True)
        st.header(f"🧑 {person} ({st.session_state.person_locations.get(person, 'Global')})")

        recs = []
        for a in arts:
            s, sc = get_sentiment(a["summary"])
            recs.append({"Title": a["title"], "Sentiment": s, "Score": sc})
        df = pd.DataFrame(recs)

        if not df.empty:
            chart = alt.Chart(df).mark_arc().encode(
                theta="count():Q", color="Sentiment:N"
            ).properties(title=f"{person} Sentiment Distribution")
            st.altair_chart(chart, use_container_width=True)

        for a in arts:
            s, sc = get_sentiment(a["summary"])
            icon = "🟢" if s == "Positive" else "🔴" if s == "Negative" else "⚪"
            with st.expander(f"{icon} {a['title']} ({a['published']})"):
                st.markdown(f"**Sentiment:** {s} ({sc:.2f})")
                st.write(a["summary"])
                snip, summ, img = fetch_article_preview(a["link"])
                if summ: st.markdown("**📝 AI Summary:**"); st.write(summ)
                if img:  st.image(img, width=600)
                st.markdown(f"[🔗 Read full article]({a['link']})")
