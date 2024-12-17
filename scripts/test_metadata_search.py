import asyncio
import json
import os
import sys
from datetime import datetime
import pytz
from bs4 import BeautifulSoup
import aiohttp

# Add the project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from news_collector.collectors.utils.date import DateUtils
from news_collector.collectors.utils.text import TextUtils
from news_collector.collectors.utils.url import UrlUtils

class SimpleSearchCollector:
    """간단한 테스트를 위한 검색 기반 메타데이터 수집기"""
    
    def __init__(self):
        self.session = None
        self.KST = pytz.timezone('Asia/Seoul')
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    async def init_session(self):
        """Initialize aiohttp session"""
        if not self.session:
            self.session = aiohttp.ClientSession(headers=self.headers)
    
    async def collect(self, keyword: str, max_articles: int = 5):
        """검색을 통한 뉴스 메타데이터 수집"""
        await self.init_session()
        
        # Naver News Search URL
        encoded_keyword = keyword.replace(' ', '+')
        url = f"https://search.naver.com/search.naver?where=news&query={encoded_keyword}&sort=1"
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Find news articles
                    articles = []
                    news_items = soup.select('.news_wrap')[:max_articles]
                    
                    for item in news_items:
                        # Extract title
                        title_elem = item.select_one('.news_tit')
                        title = title_elem.get('title', '') if title_elem else ''
                        link = title_elem.get('href', '') if title_elem else ''
                        
                        # Extract description
                        desc_elem = item.select_one('.news_dsc')
                        description = desc_elem.get_text(strip=True) if desc_elem else ''
                        
                        # Extract press and date
                        info_group = item.select('.info_group')
                        press = ''
                        published_at = ''
                        
                        if info_group:
                            # First info_group contains press name
                            press_elem = info_group[0].select_one('.press')
                            if press_elem:
                                press = press_elem.get_text(strip=True)
                            
                            # Find date in all info spans
                            for group in info_group:
                                for info in group.select('.info'):
                                    text = info.get_text(strip=True)
                                    if '분 전' in text or '시간 전' in text or '일 전' in text:
                                        published_at = text
                                        break
                        
                        article = {
                            'title': title,
                            'description': description,
                            'link': link,
                            'press': press,
                            'published_at': published_at,
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
                    return None
        except Exception as e:
            print(f"Error during collection: {str(e)}")
            return None
        finally:
            if self.session:
                await self.session.close()

async def main():
    """검색 기반 메타데이터 수집기 테스트"""
    collector = SimpleSearchCollector()
    
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
