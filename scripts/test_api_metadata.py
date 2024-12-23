import os
import sys
import asyncio
from urllib.parse import quote  # URL 인코딩용
from dotenv import load_dotenv

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from news_collector.collectors.api_metadata_collector import APIMetadataCollector

async def get_search_count(collector, query):
    """
    Get the total number of search results for a given query.
    """
    try:
        encoded_query = quote(query)  # URL 인코딩
        url = f"https://openapi.naver.com/v1/search/news.json?query={encoded_query}&display=1&start=1"
        result = await collector._make_api_request(url)
        if result and 'total' in result:
            return result['total']
        return 0
    except Exception as e:
        print(f"Error occurred while fetching search count for '{query}': {e}")
        return 0

async def main():
    # Load environment variables
    load_dotenv()
    
    # Check if credentials are available
    client_id = os.getenv('NAVER_CLIENT_ID')
    client_secret = os.getenv('NAVER_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        print("Error: NAVER_CLIENT_ID and NAVER_CLIENT_SECRET must be set in .env file")
        return
        
    # Create collector instance with configuration
    config = {
        'client_id': client_id,
        'client_secret': client_secret
    }
    collector = APIMetadataCollector(config)

    try:
        # Use async context manager
        async with collector:
            # Define main keyword and sub keywords
            main_keyword = "카카오모빌리티"
            sub_keywords = ["공정위", "자율주행", "택시", "혁신"]

            # Get search count for main keyword
            main_count = await get_search_count(collector, main_keyword)
            print(f"Search count for '{main_keyword}': {main_count}")

            # Calculate and print proportions for sub keywords
            for sub_keyword in sub_keywords:
                full_keyword = f"{main_keyword} {sub_keyword}"
                sub_count = await get_search_count(collector, full_keyword)
                if main_count > 0:
                    proportion = sub_count / main_count
                    print(f"Search count for '{full_keyword}': {sub_count}, 비중: {proportion:.2%}")
                else:
                    print(f"No results found for '{main_keyword}', unable to calculate proportion for '{full_keyword}'.")
                
    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())


# import os
# import sys
# import asyncio
# from dotenv import load_dotenv

# # Add the project root to Python path
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# from news_collector.collectors.api_metadata_collector import APIMetadataCollector

# async def main():
#     # Load environment variables
#     load_dotenv()
    
#     # Check if credentials are available
#     client_id = os.getenv('NAVER_CLIENT_ID')
#     client_secret = os.getenv('NAVER_CLIENT_SECRET')
    
#     if not client_id or not client_secret:
#         print("Error: NAVER_CLIENT_ID and NAVER_CLIENT_SECRET must be set in .env file")
#         return
        
#     # Create collector instance with configuration
#     config = {
#         'client_id': os.getenv('NAVER_CLIENT_ID'),
#         'client_secret': os.getenv('NAVER_CLIENT_SECRET')
#     }
#     collector = APIMetadataCollector(config)
    



#     try:
#         # Use async context manager
#         async with collector:
#             # Make a single API request to see full response
#             keyword = "로저 페더러"
#             url = f"https://openapi.naver.com/v1/search/news.json?query={keyword}&display=5&start=1&sort=date"
#             result = await collector._make_api_request(url)
            
#             if result:
#                 print("\nFull API Response:")
#                 print("==================")
#                 import json
#                 print(json.dumps(result, indent=2, ensure_ascii=False))
#             else:
#                 print("No results returned from API")
                
#     except Exception as e:
#         print(f"Error occurred: {e}")

# if __name__ == "__main__":
#     asyncio.run(main())
