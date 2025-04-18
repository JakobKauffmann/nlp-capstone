from duckduckgo_search import DDGS

ddgs = DDGS()

def search_articles(topic, max_results=5):
    results = ddgs.text(topic, max_results=max_results)
    articles = []
    for r in results:
        articles.append({
            "title": r.get("title"),
            "href": r.get("href"),
            "body": r.get("body")
        })

    #needs to scrape the 5 hrefs
    #with the 5 article contents we can get bias/summ/sent
    return articles