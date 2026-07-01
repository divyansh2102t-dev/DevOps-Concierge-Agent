import httpx
from bs4 import BeautifulSoup
import urllib.parse

def web_search(query: str, max_results: int = 5):
    """
    Search the web for the given query and return the top organic results.
    Includes title, direct destination URL, and description snippet.
    """
    # DuckDuckGo HTML-only search endpoint (extremely fast, zero JavaScript, no CAPTCHAs)
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        with httpx.Client() as client:
            response = client.get(url, headers=headers, timeout=8.0)
            
        if response.status_code != 200:
            return {
                "success": False, 
                "error": f"Search engine returned status code {response.status_code}"
            }
            
        soup = BeautifulSoup(response.text, "html.parser")
        results = []
        
        # DuckDuckGo HTML results are wrapped in elements with the class '.result'
        result_elements = soup.select(".result")
        for idx, result in enumerate(result_elements):
            if idx >= max_results:
                break
                
            title_el = result.select_one(".result__title .result__a")
            snippet_el = result.select_one(".result__snippet")
            
            if title_el:
                title = title_el.get_text(strip=True)
                href = title_el.get("href", "")
                
                # 1. Make URL absolute if it starts with //
                if href.startswith("//"):
                    href = "https:" + href
                
                # 2. Extract and decode the actual destination URL from the redirect wrapper
                if "/l/?uddg=" in href:
                    parsed_href = urllib.parse.urlparse(href)
                    query_params = urllib.parse.parse_qs(parsed_href.query)
                    if "uddg" in query_params:
                        href = query_params["uddg"][0]
                
                snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                results.append({
                    "title": title,
                    "url": href,
                    "snippet": snippet
                })
                
        if not results:
            return {
                "success": True, 
                "results": [], 
                "message": "No search results found."
            }
            
        return {
            "success": True, 
            "results": results
        }
        
    except Exception as e:
        return {
            "success": False, 
            "error": f"Failed to complete search: {str(e)}"
        }

if __name__ == "__main__":
    # Quick self-test when run directly
    print("Testing search...")
    res = web_search("Divyansh Tiwari portfolio")
    print(res)
