
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

def scrape_article_content(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Try extracting common article content containers
        article_tags = soup.find_all(['article', 'section', 'div'], class_=lambda x: x and 'content' in x.lower())
        if not article_tags:
            article_tags = soup.find_all(['p'])

        content = ' '.join(tag.get_text(separator=' ', strip=True) for tag in article_tags)
        return content.strip() if content else "No extractable article content found."

    except requests.exceptions.RequestException as e:
        return f"Request error for URL {url}: {e}"
    except Exception as e:
        return f"Unexpected error for URL {url}: {e}"

from duckduckgo_search import DDGS

def search_article_urls(topic, max_results=5):
    with DDGS() as ddgs:
        results = ddgs.text(topic, max_results=max_results)
        urls = [r['href'] for r in results if 'href' in r]
    return urls


def fetch_articles_for_topic(topic, max_articles=5):
    print(f"🔍 Searching for: {topic}")
    urls = search_article_urls(topic, max_results=max_articles)
    
    results = []
    for i, url in enumerate(urls):
        print(f"\n🔗 ({i+1}) Scraping: {url}")
        content = scrape_article_content(url)
        results.append({
            'url': url,
            'content': content[:1000] + ('...' if len(content) > 1000 else '')  # limit output
        })
    return results


if __name__ == "__main__":
    topic = "AI in healthcare"
    topic = "tenz valorant"

    articles = fetch_articles_for_topic(topic, max_articles=10)
    
    for idx, article in enumerate(articles, 1):
        print(f"\n--- Article {idx} ---")
        print(f"URL: {article['url']}")
        print(f"Content Preview:\n{article['content']}")
