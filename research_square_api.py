import asyncio
from sdk.tools.utils_tools import quick_ai_search
from sdk.tools.docs_tools import resolve_library_id, query_library_docs

async def main():
    # Research Square API in parallel
    results = await asyncio.gather(
        quick_ai_search("Square API developer documentation 2025 2026 OAuth flow merchant authorization catalog orders payments endpoints"),
        quick_ai_search("Square API read catalog items transactions orders payments inventory Python SDK connect app marketplace"),
        quick_ai_search("Square API webhooks events real-time sync orders catalog changes inventory updates"),
        quick_ai_search("Square API rate limits pagination cursor best practices batch endpoints"),
        quick_ai_search("Square API sandbox testing developer account create application OAuth scopes permissions"),
    )
    
    for i, r in enumerate(results):
        print(f"\n{'='*80}")
        print(f"SEARCH {i+1}")
        print(f"{'='*80}")
        print(r.search_response)

asyncio.run(main())
