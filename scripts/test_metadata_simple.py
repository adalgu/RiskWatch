import asyncio
import json
import os
import sys
from datetime import datetime
import pytz

# Add the project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from news_collector.collectors.utils.date import DateUtils
from news_collector.collectors.utils.text import TextUtils
from news_collector.collectors.utils.url import UrlUtils

class SimpleMetadataCollector:
    """간단한 테스트를 위한 메타데이터 수집기"""
    
    def __init__(self):
        self.session = None
        self.KST = pytz.timezone('Asia/Seoul')
        # Naver API 인증 정보
        self.client_id = os.getenv('NAVER_CLIENT_ID')
        self.client_secret = os.getenv('NAVER_CLIENT_SECRET')
        
        if not self.client_id or not self.client_secret:
            print("Warning: NAVER_CLIENT_ID 또는 NAVER_CLIENT_SECRET 환경변수가 설정되지 않았습니다.")
    
    async def init_session(self):
        """Initialize aiohttp session"""
        import aiohttp
        if not self.session:
            self.session = aiohttp.ClientSession(
                headers={
                    "X-Naver-Client-Id": self.client_id,
                    "X-Naver-Client-Secret": self.client_secret
                }
            )
    
    async def collect(self, keyword: str, max_articles: int = 5):
        """간단한 뉴스 메타데이터 수집"""
        if not self.client_id or not self.client_secret:
            print("Error: Naver API 인증 정보가 필요합니다.")
            return None
            
        await self.init_session()
        
        # Naver News Search API URL
        encoded_keyword = keyword.replace(' ', '+')
        url = f"https://openapi.naver.com/v1/search/news.json?query={encoded_keyword}&display={max_articles}&sort=date"
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    # Process articles
                    articles = []
                    for item in result.get('items', []):
                        article = {
                            'title': TextUtils.clean_html(item['title']),
                            'description': TextUtils.clean_html(item['description']),
                            'link': item['link'],
                            'published_at': item['pubDate'],
                            'collected_at': DateUtils.format_date(
                                datetime.now(self.KST), 
                                '%Y-%m-%dT%H:%M:%S%z', 
                                timezone=self.KST
                            )
                        }
                        articles.append(article)
                    
                    return {
                        'articles': articles,
                        'total': len(articles),
                        'keyword': keyword
                    }
                else:
                    print(f"Error: Status code {response.status}")
                    if response.status == 401:
                        print("인증 실패: Client ID와 Secret을 확인해주세요.")
                    return None
        except Exception as e:
            print(f"Error during collection: {str(e)}")
            return None
        finally:
            if self.session:
                await self.session.close()

async def main():
    """간단한 메타데이터 수집기 테스트"""
    # 환경변수 설정 확인
    if not os.getenv('NAVER_CLIENT_ID') or not os.getenv('NAVER_CLIENT_SECRET'):
        print("\nNaver API 인증 정보가 필요합니다.")
        print("다음 환경변수를 설정해주세요:")
        print("export NAVER_CLIENT_ID='your_client_id'")
        print("export NAVER_CLIENT_SECRET='your_client_secret'")
        return

    collector = SimpleMetadataCollector()
    
    try:
        result = await collector.collect(
            keyword='삼성전자',
            max_articles=5
        )
        if result:
            print("\n=== 수집 결과 ===")
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("수집 실패")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
