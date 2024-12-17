# NAVER_CLIENT_ID=NWWGuLdEI4NM3gGu9QiV NAVER_CLIENT_SECRET=Js6xhYYwtn python scripts/test_metadata_docker.py --method API --keyword "카카오모빌리티" --max_articles 1000
# NAVER_CLIENT_ID=NWWGuLdEI4NM3gGu9QiV NAVER_CLIENT_SECRET=Js6xhYYwtn python scripts/test_metadata_docker.py --method API --keyword "카카오" --max_articles 5

import asyncio
import json
import os
import sys
from datetime import datetime
import pytz
import argparse

# Add the project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from news_collector.collectors.metadata import MetadataCollector

async def main():
    """Docker 환경에서 메타데이터 수집기 테스트"""
    parser = argparse.ArgumentParser(description='네이버 뉴스 메타데이터 수집기 (Docker 환경)')
    parser.add_argument('--method', choices=['API', 'SEARCH'], default='API',
                      help='수집 방식 (API 또는 SEARCH)')
    parser.add_argument('--keyword', required=True, help='검색 키워드')
    parser.add_argument('--max_articles', type=int, default=5,
                      help='수집할 최대 기사 수')
    args = parser.parse_args()

    # 환경 설정
    config = {
        'rabbitmq_url': 'amqp://guest:guest@localhost:5672/',
        'selenium_hub_url': 'http://localhost:4444/wd/hub',
        'client_id': os.getenv('NAVER_CLIENT_ID'),
        'client_secret': os.getenv('NAVER_CLIENT_SECRET'),
        'proxy': None,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    # Producer 설정 오버라이드를 위한 환경변수 설정
    os.environ['RABBITMQ_URL'] = config['rabbitmq_url']
    os.environ['SELENIUM_HUB_URL'] = config['selenium_hub_url']

    collector = MetadataCollector(config)

    try:
        print(f"\n=== 수집 시작 ===")
        print(f"방식: {args.method}")
        print(f"키워드: {args.keyword}")
        print(f"최대 기사 수: {args.max_articles}")
        
        result = await collector.collect(
            method=args.method,
            keyword=args.keyword,
            max_articles=args.max_articles,
            is_test=True
        )
        
        print("\n=== 수집 결과 ===")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    except Exception as e:
        print(f"\n=== 오류 발생 ===")
        print(f"Error: {str(e)}")
    finally:
        await collector.cleanup()

if __name__ == "__main__":
    # Docker 서비스 확인
    print("\n=== 환경 체크 ===")
    print("1. RabbitMQ가 실행 중인지 확인하세요 (localhost:5672)")
    print("2. Selenium Hub가 실행 중인지 확인하세요 (localhost:4444)")
    print("3. Chrome 노드가 연결되어 있는지 확인하세요")
    print("\nDocker Compose로 서비스를 시작하려면:")
    print("docker-compose up -d rabbitmq selenium-hub chrome")
    print("\nNaver API 인증 정보가 필요합니다:")
    print("export NAVER_CLIENT_ID='your_client_id'")
    print("export NAVER_CLIENT_SECRET='your_client_secret'")
    
    response = input("\n계속하시겠습니까? (y/n): ")
    if response.lower() == 'y':
        # Docker 서비스가 완전히 시작될 때까지 대기
        print("\nDocker 서비스가 시작될 때까지 3초 대기...")
        asyncio.run(asyncio.sleep(3))
        asyncio.run(main())
    else:
        print("테스트가 취소되었습니다.")
