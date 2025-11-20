from pipeline_veille import Config
import requests
import json

# Re-implement search to see errors
def debug_search(q):
    url = "https://www.googleapis.com/customsearch/v1"
    # Config.SEARCH_PERIOD is 'y1' from my previous edit, or I can set it here
    params = {'q': q, 'key': Config.GOOGLE_API_KEY, 'cx': Config.SEARCH_ENGINE_ID, 'dateRestrict': 'y1'}
    
    print(f"   > Requesting: {url} with params (hidden key)")
    # Don't print key
    
    try:
        res = requests.get(url, params=params)
        data = res.json()
        
        if 'error' in data:
            print(f"   ❌ API ERROR: {data['error']}")
            return []
            
        if 'items' not in data:
            print(f"   ⚠️ No 'items' in response. Full response keys: {list(data.keys())}")
            if 'spelling' in data: print(f"      Spelling suggestion: {data['spelling']}")
            return []
            
        return data['items']
    except Exception as e:
        print(f"   ❌ EXCEPTION: {e}")
        return []

print(f">>> DEBUG SEARCH TOOL (VERBOSE) <<<")
keywords = ['Arrêté ICPE 2560', 'Déchets métaux']

for k in keywords:
    print(f"\n--- Keyword: {k} ---")
    results = debug_search(k)
    print(f"Raw results found: {len(results)}")
