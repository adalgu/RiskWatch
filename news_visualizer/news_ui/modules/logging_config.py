# modules/logging_config.py

import logging
import os

def get_logger(name):
    """로거 설정 및 반환"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # 핸들러가 없으면 추가
    if not logger.handlers:
        log_path = os.getenv('COLLECTOR_LOG_PATH', '/app/logs/collector.log')
        os.makedirs(os.path.dirname(log_path), exist_ok=True)  # 로그 디렉토리 생성
        handler = logging.FileHandler(log_path)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger