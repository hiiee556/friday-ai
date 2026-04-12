import sys
from ddgs import DDGS
from googlesearch import search

def test_engines(query):
    print(f"--- Testing DuckDuckGo for: {query} ---")
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=3)]
            for i, r in enumerate(results):
                print(f"{i+1}. {r.get('title')}")
                print(f"   {r.get('body')[:100]}...")
    except Exception as e:
        print(f"DDGS Error: {e}")

    print(f"\n--- Testing Google for: {query} ---")
    try:
        google_results = search(query, num_results=3, advanced=True)
        for i, r in enumerate(google_results):
            print(f"{i+1}. {r.title}")
            print(f"   {r.description[:100]}...")
    except Exception as e:
        print(f"Google Error: {e}")

if __name__ == "__main__":
    test_engines("current price of gold India April 2026")
