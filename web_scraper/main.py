import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin # Added urljoin
import time # Added for potential delays

# Consider a more robust user agent
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def scrape_article_content(url):
    """
    Scrapes the main textual content from a given news article URL.
    Improved with basic error handling and content extraction logic.
    """
    try:
        # Add http scheme if missing
        parsed_url = urlparse(url)
        if not parsed_url.scheme:
            url = 'https://' + url

        response = requests.get(url, headers=HEADERS, timeout=15) # Increased timeout
        response.raise_for_status() # Check for HTTP errors

        # Check content type - proceed only if likely HTML
        content_type = response.headers.get('content-type', '').lower()
        if 'html' not in content_type:
            return f"Error: URL {url} does not point to an HTML page (Content-Type: {content_type})."

        soup = BeautifulSoup(response.content, 'lxml') # Use lxml for better parsing

        # Remove common non-content elements
        for element in soup(['script', 'style', 'nav', 'footer', 'aside', 'header', 'form', 'button', 'input', 'select', 'textarea']):
            element.decompose()

        # --- Content Extraction Logic ---
        # 1. Try common article tags/classes
        potential_containers = soup.find_all(['article', 'main', 'section'])
        if not potential_containers:
            # 2. Try divs with common content-related IDs or classes
            potential_containers = soup.find_all('div', id=lambda x: x and ('content' in x or 'article' in x or 'post' in x or 'body' in x))
            if not potential_containers:
                 potential_containers = soup.find_all('div', class_=lambda x: x and any(c in x for c in ['content', 'article', 'post', 'body', 'story', 'main']))

        # 3. If specific containers found, prioritize the largest one
        best_container = None
        if potential_containers:
            best_container = max(potential_containers, key=lambda tag: len(tag.get_text(strip=True)))

        # 4. Extract text: from best container or fallback to body paragraphs
        if best_container:
            # Get text, ensuring paragraphs are separated
            paragraphs = best_container.find_all('p')
            content = '\n\n'.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
        else:
            # Fallback: Get all paragraphs from the body, filter short ones
            print(f"Warning: Could not find specific article container for {url}. Falling back to body paragraphs.")
            all_paragraphs = soup.find_all('p')
            content = '\n\n'.join(p.get_text(strip=True) for p in all_paragraphs if len(p.get_text(strip=True)) > 50) # Min paragraph length

        # Basic cleanup
        content = content.strip()

        if not content:
            return f"Error: No extractable article content found at {url} after filtering."

        print(f"Successfully scraped ~{len(content)} characters from {url}")
        return content

    except requests.exceptions.Timeout:
        return f"Error: Request timed out for URL {url}."
    except requests.exceptions.HTTPError as e:
        return f"Error: HTTP error {e.response.status_code} for URL {url}."
    except requests.exceptions.RequestException as e:
        return f"Error: Request error for URL {url}: {e}"
    except Exception as e:
        # Log the full traceback for unexpected errors
        print(f"Unexpected scraping error for URL {url}:")
        traceback.print_exc()
        return f"Error: Unexpected error during scraping: {e}"


# --- DuckDuckGo Search Functions ---
# Ensure duckduckgo_search library is installed: pip install -U duckduckgo_search
try:
    from duckduckgo_search import DDGS
except ImportError:
    print("Error: duckduckgo_search library not found. Please install it: pip install -U duckduckgo_search")
    # Define dummy functions or raise error if DDGS is critical
    def search_article_urls(topic, max_results=5): return []
    DDGS = None


def search_article_urls(topic, max_results=5):
    """Searches DuckDuckGo for article URLs related to a topic."""
    if DDGS is None:
         return [] # Return empty list if library failed to import

    urls = []
    try:
        print(f"Searching DuckDuckGo for: {topic} (max_results={max_results})")
        # Use DDGS context manager
        with DDGS(headers=HEADERS, timeout=20) as ddgs:
            # Iterate through results - text search often yields good news links
            for r in ddgs.text(topic, max_results=max_results * 2): # Fetch more to filter later if needed
                if 'href' in r:
                    # Basic filtering: avoid common non-article domains if needed
                    # parsed_href = urlparse(r['href'])
                    # if parsed_href.netloc and 'youtube.com' not in parsed_href.netloc and 'wikipedia.org' not in parsed_href.netloc:
                    urls.append(r['href'])
                if len(urls) >= max_results:
                    break # Stop once we have enough URLs
        print(f"Found {len(urls)} potential URLs.")
        return urls
    except Exception as e:
        print(f"Error during DuckDuckGo search for '{topic}': {e}")
        return [] # Return empty list on error


def fetch_articles_for_topic(topic, max_articles=5):
    """Searches for a topic and scrapes content for the found URLs."""
    print(f"--- Fetching and scraping articles for topic: {topic} ---")
    urls = search_article_urls(topic, max_results=max_articles)

    results = []
    if not urls:
        print("No URLs found for the topic.")
        return results

    for i, url in enumerate(urls):
        print(f"\n🔗 ({i+1}/{len(urls)}) Scraping: {url}")
        # Add a small delay between requests to be polite
        time.sleep(0.5)
        content = scrape_article_content(url)
        results.append({
            'url': url,
            'content': content # Return full content or error message
        })
        # Optional: Stop early if enough successful scrapes occur
        # successful_scrapes = sum(1 for r in results if 'error' not in r.get('content', '').lower())
        # if successful_scrapes >= max_articles:
        #     break

    print(f"--- Finished processing for topic: {topic} ---")
    return results


# Example usage (for testing the scraper directly)
if __name__ == "__main__":
    test_topic = "latest developments in AI regulation"
    test_url = "https://www.theverge.com/2023/10/30/23938040/biden-ai-executive-order-safety-security-fairness" # Example URL

    print("\n--- Testing Topic Search & Scrape ---")
    articles = fetch_articles_for_topic(test_topic, max_articles=2)
    for idx, article in enumerate(articles, 1):
        print(f"\n--- Article {idx} ---")
        print(f"URL: {article['url']}")
        content_preview = article.get('content', 'N/A')
        if isinstance(content_preview, str):
             print(f"Content Preview (first 300 chars):\n{content_preview[:300]}...")
        else:
             print(f"Content: {content_preview}")


    print("\n\n--- Testing Single URL Scrape ---")
    content = scrape_article_content(test_url)
    if isinstance(content, str) and "error" not in content.lower():
         print(f"Scraped content from {test_url} (first 300 chars):\n{content[:300]}...")
    else:
         print(f"Scraping result for {test_url}: {content}")
