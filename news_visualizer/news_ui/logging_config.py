import logging
import os
from datetime import datetime

def setup_logging():
    """로깅 설정"""
    # 로그 디렉토리 생성
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # 로그 파일 경로
    collection_log = os.path.join(log_dir, "collection.log")
    app_log = os.path.join(log_dir, "app.log")
    
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # 기존 핸들러 제거
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)
    
    # 앱 로그 파일 핸들러
    file_handler = logging.FileHandler(app_log, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)
    root_logger.addHandler(file_handler)
    
    # 수집 로그용 핸들러
    collection_logger = logging.getLogger('collection')
    collection_logger.setLevel(logging.INFO)
    collection_handler = logging.FileHandler(collection_log, encoding='utf-8')
    collection_format = logging.Formatter('%(asctime)s - collection - %(levelname)s - %(message)s')
    collection_handler.setFormatter(collection_format)
    collection_logger.addHandler(collection_handler)
    
    # 다른 로거들이 루트 로거를 사용하도록 설정
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
    
    return root_logger
