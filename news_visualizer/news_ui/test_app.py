import unittest
import os
import sys
import pandas as pd
from unittest.mock import patch, MagicMock

# 모듈 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.database import Database
from collection_service import send_collection_request

class TestNewsUI(unittest.TestCase):
    """뉴스 UI 테스트 클래스"""
    
    @patch('collection_service.requests.post')
    def test_send_collection_request(self, mock_post):
        """수집 요청 전송 테스트"""
        # Mock 응답 설정
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success", "message": "Collection started"}
        mock_post.return_value = mock_response
        
        # 함수 호출
        from datetime import datetime, date
        success, _ = send_collection_request(
            keyword="테스트",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 7),
            method="naver_news_search",
            min_delay=1,
            max_delay=3,
            collection_type="metadata",
            batch_size=30,
            auto_collect_comments=True
        )
        
        # 검증
        self.assertTrue(success)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "http://fast_api:8000/api/v1/collectors/metadata/start")
        self.assertEqual(kwargs['json']['keyword'], "테스트")
        self.assertEqual(kwargs['json']['start_date'], "2024-01-01")
        self.assertEqual(kwargs['json']['end_date'], "2024-01-07")
    
    @patch('modules.database.Database.session')
    def test_get_article_summary(self, mock_session):
        """기사 요약 정보 조회 테스트"""
        # Mock 응답 설정
        mock_execute = MagicMock()
        mock_session.execute.return_value = mock_execute
        
        # 총 기사 수 쿼리 응답
        mock_execute.scalar.side_effect = [100, 80, "2024-03-14 12:00:00"]
        
        # 키워드별 기사 수 쿼리 응답
        mock_keyword_result = MagicMock()
        mock_keyword_result.fetchall.return_value = [
            ("택시", 30),
            ("배달", 25),
            ("플랫폼", 20),
            ("규제", 15),
            ("서비스", 10)
        ]
        mock_session.execute.return_value = mock_keyword_result
        
        # 함수 호출
        from pages.3_Database_Results import get_article_summary
        result = get_article_summary(Database())
        
        # 검증
        self.assertIsNotNone(result)
        self.assertEqual(result['total_articles'], 100)
        self.assertEqual(result['naver_articles'], 80)
        self.assertEqual(len(result['keyword_counts']), 5)
    
    @patch('modules.database.Database.session')
    def test_get_top_articles_by_comments(self, mock_session):
        """댓글 많은 기사 조회 테스트"""
        # Mock 응답 설정
        mock_execute = MagicMock()
        mock_session.execute.return_value = mock_execute
        
        # 쿼리 응답
        mock_execute.fetchall.return_value = [
            (1, "첫 번째 테스트 기사", "언론사A", "http://example.com/1", "2024-03-01 12:00:00", "테스트", 100),
            (2, "두 번째 테스트 기사", "언론사B", "http://example.com/2", "2024-03-02 12:00:00", "테스트", 80),
            (3, "세 번째 테스트 기사", "언론사C", "http://example.com/3", "2024-03-03 12:00:00", "테스트", 60)
        ]
        
        # 함수 호출
        from pages.2_Comments import get_top_articles_by_comments
        result = get_top_articles_by_comments(Database(), limit=3)
        
        # 검증
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 3)
        self.assertEqual(result['댓글수'].iloc[0], 100)
        self.assertEqual(result['댓글수'].iloc[1], 80)
        self.assertEqual(result['댓글수'].iloc[2], 60)

if __name__ == '__main__':
    unittest.main()
