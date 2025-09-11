import requests
import os

API_KEY = os.getenv("NEWS_API_KEY")  # export NEWS_API_KEY="your_api_key"

def fetch_news_for_entity(entity: str, max_results=5):
    url = f"https://newsapi.org/v2/everything?q={entity}&language=en&sortBy=publishedAt&pageSize={max_results}&apiKey={API_KEY}"
    resp = requests.get(url)
    
    if resp.status_code == 200:
        data = resp.json()
        articles = []
        for art in data.get("articles", []):
            articles.append({
                "title": art["title"],
                "url": art["url"],
                "publishedAt": art["publishedAt"].split("T")[0],
                "source": art["source"]["name"]
            })
        return articles
    else:
        return []
