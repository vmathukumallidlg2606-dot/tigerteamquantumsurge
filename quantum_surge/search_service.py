import logging
try:
    from ddgs import DDGS
except ImportError:  # Fallback to legacy package name if installed
    from duckduckgo_search import DDGS

class SearchService:
    @staticmethod
    def search_recent_threats(topic_name: str) -> str:
        """Queries DuckDuckGo for recent real-world attacks/vulnerabilities relating to the topic."""
        query = f"recent {topic_name} cybersecurity attack news"
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=3))
                if results:
                    context_snippets = []
                    for idx, res in enumerate(results, 1):
                        title = res.get("title", "Threat Context")
                        snippet = res.get("body", "")
                        context_snippets.append(f"[{idx}] {title}: {snippet}")
                    return "\n\n".join(context_snippets)
        except Exception as e:
            logging.error(f"DuckDuckGo search error: {e}")
            
        return "No recent search logs available for this topic. Rely on standard Security+ threat database scenarios."
