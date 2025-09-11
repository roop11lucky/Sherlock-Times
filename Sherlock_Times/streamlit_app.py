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

# -------------------------------
# Config
# -------------------------------
st.set_page_config(page_title="Sherlock Times", page_icon="🕵️", layout="wide")

# Auto-refresh every X seconds
refresh_minutes = st.sidebar.selectbox("⏱ Refresh every:", [5, 15, 30, 60], index=1)
refresh_seconds = refresh_minutes * 60
st_autorefresh(interval=refresh_seconds * 1000, key="dashboard_refresh")

# Predefined entities (your updated list)
if "entities" not in st.session_state:
    st.session_state.entities = [
        "Google", 
        "Synopsys", 
        "Tiger Graph", 
        "Meta", 
        "Ideal Living Management LLC", 
        "NewFold", 
        "Cisco", 
        "Gigamon"
    ]

# Add new entity
new_entity = st.sidebar.text_input("➕ Add new client/tech/domain")
if st.sidebar.button("Add Entity") and new_entity:
    if new_entity not in st.session_state.entities:
        st.session_state.entities.append(new_entity)
        st.success(f"Added {new_entity}")
    else:
        st.warning(f"{new_entity} already exists in the watchlist!")

# -------------------------------
# Helper Functions
# -------------------------------
def resolve_redirect(url):
    """Follow Google News redirect to get the real article link."""
    try:
        r = requests.get(url, allow_redirects=True, timeout=5)
        return r.url
    except:
        return url

def clean_html(raw_html):
    """Remove HTML tags from RSS summary."""
    try:
        soup = BeautifulSoup(raw_html, "html.parser")
        return soup.get_text()
    except:
        return raw_html

def fetch_news_rss(entity, max_results=10):
    """Fetch news headlines from Google News RSS and resolve redirects."""
    query = entity.replace(" ", "+")
    url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
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
            "summary": summary[:500]  # ✅ Limit summary length
        })
    return articles

def fetch_article_preview(url):
    """Try extracting snippet + image from article."""
    try:
        article = Article(url)
        article.download()
        article.parse()
        snippet = article.text[:500] + "..." if article.text else None
        img = article.top_image
        if img and ("gstatic" in img or "googleusercontent" in img):
            img = None
        return snippet, img
    except:
        return None, None

# Sentiment Analysis
analyzer = SentimentIntensityAnalyzer()
def get_sentiment(text):
    """Return sentiment label + score using VADER."""
    score = analyzer.polarity_scores(text)
    compound = score["compound"]
    if compound >= 0.05:
        return "Positive", compound
    elif compound <= -0.05:
        return "Negative", compound
    else:
        return "Neutral", compound

# -------------------------------
# Dashboard
# -------------------------------
st.title("🕵️ Sherlock Times – Live Client News Dashboard")

# Fetch all articles
client_articles = {}
for entity in st.session_state.entities:
    client_articles[entity] = fetch_news_rss(entity)

# Sidebar filters
all_tags = st.session_state.entities
selected_tags = st.sidebar.multiselect("🔖 Filter by Clients:", all_tags, default=all_tags)
search_query = st.sidebar.text_input("🔍 Global Search (keywords)")

# -------------------------------
# Display by Client
# -------------------------------
for client, articles in client_articles.items():
    if client not in selected_tags:
        continue

    # Apply global search
    if search_query:
        articles = [a for a in articles if search_query.lower() in a["title"].lower()]

    if not articles:
        continue

    st.header(f"🏢 {client}")

    # Build DataFrame for sentiment summary
    records = []
    for art in articles:
        sentiment, score = get_sentiment(art["summary"])
        records.append({
            "Title": art["title"],
            "Sentiment": sentiment,
            "Score": score,
            "Published": art["published"]
        })
    df = pd.DataFrame(records)

    # Chart (pie sentiment distribution)
    chart = alt.Chart(df).mark_arc().encode(
        theta="count():Q",
        color="Sentiment:N"
    ).properties(title=f"{client} Sentiment Distribution")
    st.altair_chart(chart, use_container_width=True)

    # Articles list
    for art in articles:
        with st.expander(f"📰 {art['title']} ({art['published']})"):
            sentiment, score = get_sentiment(art["summary"])
            if sentiment == "Positive":
                st.markdown(f"**Sentiment:** 🟢 {sentiment} ({score:.2f})")
            elif sentiment == "Negative":
                st.markdown(f"**Sentiment:** 🔴 {sentiment} ({score:.2f})")
            else:
                st.markdown(f"**Sentiment:** ⚪ {sentiment} ({score:.2f})")

            st.write(art["summary"])

            snippet, img = fetch_article_preview(art["link"])
            if snippet:
                st.write(snippet)
            if img:
                st.image(img, width=600)

            st.markdown(f"[🔗 Read full article]({art['link']})")
