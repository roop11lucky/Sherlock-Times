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

# -------------------------------
# Config
# -------------------------------
st.set_page_config(page_title="Sherlock Times", page_icon="🕵️", layout="wide")

# Auto-refresh every X seconds
refresh_minutes = st.sidebar.selectbox("⏱ Refresh every:", [5, 15, 30, 60], index=1)
refresh_seconds = refresh_minutes * 60
st_autorefresh(interval=refresh_seconds * 1000, key="dashboard_refresh")

# Predefined entities (persistent watchlist)
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

# -------------------------------
# Location Config
# -------------------------------
LOCATIONS = ["Global", "IN", "US"]

if "client_locations" not in st.session_state:
    st.session_state.client_locations = {
        "Google": "IN",
        "Synopsys": "US",
        "Cisco": "US",
        "Ideal Living Management LLC": "Global",
        "Meta": "Global",
        "Tiger Graph": "Global",
        "NewFold": "Global",
        "Gigamon": "Global"
    }

st.sidebar.subheader("🌍 Client Location Mapping")
for client in st.session_state.entities:
    st.session_state.client_locations[client] = st.sidebar.selectbox(
        f"{client} Location",
        LOCATIONS,
        index=LOCATIONS.index(st.session_state.client_locations.get(client, "Global"))
    )

# Add new company to persistent watchlist
new_entity = st.sidebar.text_input("➕ Add Company to Watchlist")
if st.sidebar.button("Add") and new_entity:
    if new_entity not in st.session_state.entities:
        st.session_state.entities.append(new_entity)
        st.session_state.client_locations[new_entity] = "Global"
        st.success(f"Added {new_entity} to watchlist")
    else:
        st.warning(f"{new_entity} already exists!")

# Global override
override_loc = st.sidebar.selectbox("🌐 Override All Locations", ["Off", "Global", "IN", "US"], index=0)

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

def fetch_news_rss(entity, max_results=10):
    query = entity.replace(" ", "+")
    
    # Location handling
    if override_loc != "Off":
        loc = override_loc
    else:
        loc = st.session_state.client_locations.get(entity, "Global")

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
st.title("🕵️ Sherlock Times – Live Client News Dashboard")

# Always show last fetched in IST
tz = pytz.timezone("Asia/Kolkata")
last_fetched = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
st.markdown(f"⏱ **Last Fetched (IST):** {last_fetched}")
st.markdown(f"📅 **Today:** {datetime.now(tz).strftime('%A, %d %B %Y')}")

# -------------------------------
# Quick Search (One-time Company/Topic)
# -------------------------------
quick_search = st.text_input("🔍 Quick Search (One-time, not saved)")
if quick_search:
    st.subheader(f"📢 Quick Results for: {quick_search}")
    articles = fetch_news_rss(quick_search)
    for art in articles:
        sentiment, score = get_sentiment(art["summary"])
        sentiment_icon = "🟢" if sentiment == "Positive" else "🔴" if sentiment == "Negative" else "⚪"

        with st.expander(f"{sentiment_icon} {art['title']} ({art['published']})"):
            st.markdown(f"**Sentiment:** {sentiment} ({score:.2f})")
            st.write(art["summary"])

            snippet, summary, img = fetch_article_preview(art["link"])
            if summary:
                st.markdown("**📝 AI Summary:**")
                st.write(summary)
            if snippet:
                st.markdown("**📄 Snippet:**")
                st.write(snippet)
            if img:
                st.image(img, width=600)

            st.markdown(f"[🔗 Read full article]({art['link']})")

st.markdown("---")

# -------------------------------
# Persistent Clients Section
# -------------------------------
client_articles = {}
for entity in st.session_state.entities:
    client_articles[entity] = fetch_news_rss(entity)

selected_tags = st.sidebar.multiselect("🔖 Filter by Clients:", st.session_state.entities, default=st.session_state.entities)
search_query = st.sidebar.text_input("🔍 Global Search (keywords)")

for client, articles in client_articles.items():
    if client not in selected_tags:
        continue

    if search_query:
        articles = [a for a in articles if search_query.lower() in a["title"].lower()]

    if not articles:
        continue

    st.header(f"🏢 {client} ({st.session_state.client_locations[client]})")

    # Sentiment pie chart
    records = []
    for art in articles:
        sentiment, score = get_sentiment(art["summary"])
        records.append({"Title": art["title"], "Sentiment": sentiment, "Score": score, "Published": art["published"]})
    df = pd.DataFrame(records)

    chart = alt.Chart(df).mark_arc().encode(
        theta="count():Q",
        color="Sentiment:N"
    ).properties(title=f"{client} Sentiment Distribution")
    st.altair_chart(chart, use_container_width=True)

    # Articles
    for art in articles:
        sentiment, score = get_sentiment(art["summary"])
        sentiment_icon = "🟢" if sentiment == "Positive" else "🔴" if sentiment == "Negative" else "⚪"

        with st.expander(f"{sentiment_icon} {art['title']} ({art['published']})"):
            st.markdown(f"**Sentiment:** {sentiment} ({score:.2f})")
            st.write(art["summary"])

            snippet, summary, img = fetch_article_preview(art["link"])
            if summary:
                st.markdown("**📝 AI Summary:**")
                st.write(summary)
            if snippet:
                st.markdown("**📄 Snippet:**")
                st.write(snippet)
            if img:
                st.image(img, width=600)

            st.markdown(f"[🔗 Read full article]({art['link']})")
