FROM python:3.12-slim

WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 의존성 파일 복사 및 설치
COPY pyproject.toml poetry.lock* ./

# Poetry 설치 및 시스템 Python 환경에 직접 설치하도록 설정
RUN pip install poetry \
    && poetry config virtualenvs.create false \
    && poetry install --no-dev --no-root

# 애플리케이션 코드 복사
COPY . .

# Expose Streamlit port
EXPOSE 8501

# Set environment variables
ENV PYTHONPATH=/app:/app/news_storage

# 애플리케이션 실행
CMD ["streamlit", "run", "app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
