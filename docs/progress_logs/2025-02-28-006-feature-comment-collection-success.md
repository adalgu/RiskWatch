# 댓글 수집 기능 성공적 구현 및 데이터베이스 쿼리

- **날짜**: 2025-02-28
- **작성자**: Gunn Kim
- **관련 이슈**: N/A
- **이전 로그**: 
  - [댓글 스키마 개선 및 데이터베이스 확장](./2025-02-28-005-feature-comment-schema-enhancement.md)
  - [댓글 수집 및 데이터베이스 저장 기능 구현](./2025-02-28-004-feature-comment-collection-integration.md)

## 문제 상황

댓글 스키마 개선 및 데이터베이스 확장 작업 이후, 실제 뉴스 기사에 대한 댓글 수집 기능이 정상적으로 작동하는지 검증하고 수집된 데이터를 효과적으로 조회하는 방법이 필요했습니다. 특히 다음과 같은 사항을 확인해야 했습니다:

1. **수집 기능 검증**: 개선된 스키마와 데이터베이스 구조로 실제 댓글 수집이 정상적으로 이루어지는지 확인
2. **데이터 품질 확인**: 수집된 댓글 데이터가 모든 필드를 포함하여 정확하게 저장되는지 확인
3. **데이터 조회 방법**: 수집된 댓글을 효과적으로 조회하고 분석할 수 있는 SQL 쿼리 개발

## 해결 전략

다음과 같은 접근 방식으로 문제를 해결했습니다:

1. **테스트 수집 실행**: 실제 뉴스 기사(ID: 93)에 대한 댓글 수집 스크립트 실행
2. **로그 분석**: 수집 과정의 로그를 분석하여 성공 여부 및 수집된 댓글 수 확인
3. **데이터베이스 쿼리 개발**: 수집된 댓글을 다양한 관점에서 조회할 수 있는 SQL 쿼리 개발

## 구현 세부사항

### 1. 댓글 수집 실행 및 결과

`scripts/run_article_with_comments.sh` 스크립트를 사용하여 기사 ID 93에 대한 댓글 수집을 실행했습니다:

```bash
./scripts/run_article_with_comments.sh 93
```

수집 결과 로그:
```
/Users/gunn.kim/study/RiskWatch/news_collector/collectors/utils/text.py:18: MarkupResemblesLocatorWarning: The input looks more like a filename than markup. You may want to open this file and pass the filehandle into Beautiful Soup.
  soup = BeautifulSoup(html, 'html.parser')
2025-02-28 18:38:30,737 - news_collector.collectors.comments - INFO - Collected 877 comments out of 1
2025-02-28 18:38:30,818 - CommentCollector - INFO - Completed collection successfully at 2025-02-28 18:38:30.818166 with details: {'total_comments': 877, 'total_count': 1}
2025-02-28 18:38:30,818 - scripts.collect_and_store_comments - INFO - Collected 877 comments
2025-02-28 18:38:30,820 - scripts.collect_and_store_comments - INFO - Storing 877 comments for article ID 93
2025-02-28 18:38:31,243 - scripts.collect_and_store_comments - INFO - Successfully stored 877 comments in database
2025-02-28 18:38:31,244 - scripts.collect_and_store_comments - INFO - Comment collection and storage completed successfully
2025-02-28 18:38:31,244 - __main__ - INFO - Successfully collected article and 877 comments
2025-02-28 18:38:31,244 - __main__ - INFO - Article ID: 93
```

수집 결과 분석:
- 총 877개의 댓글이 성공적으로 수집됨
- 모든 댓글이 데이터베이스에 정상적으로 저장됨
- 경고 메시지(MarkupResemblesLocatorWarning)가 발생했으나 수집 과정에는 영향을 주지 않음

### 2. 데이터베이스 쿼리 개발

수집된 댓글을 조회하기 위한 다양한 SQL 쿼리를 개발했습니다:

#### 2.1 기본 댓글 조회

```sql
SELECT 
    id, 
    comment_no, 
    content, 
    username, 
    timestamp, 
    likes, 
    dislikes, 
    reply_count, 
    is_reply
FROM comments
WHERE article_id = 93
ORDER BY collected_at DESC
LIMIT 20;
```

#### 2.2 댓글 통계 조회

```sql
SELECT 
    COUNT(*) AS total_comments,
    SUM(CASE WHEN is_reply = true THEN 1 ELSE 0 END) AS reply_count,
    SUM(CASE WHEN is_reply = false THEN 1 ELSE 0 END) AS parent_comment_count,
    AVG(likes) AS avg_likes,
    MAX(likes) AS max_likes,
    SUM(likes) AS total_likes,
    COUNT(DISTINCT username) AS unique_users
FROM comments
WHERE article_id = 93;
```

#### 2.3 좋아요 순으로 인기 댓글 조회

```sql
SELECT 
    id, 
    comment_no, 
    content, 
    username, 
    timestamp, 
    likes, 
    dislikes, 
    reply_count
FROM comments
WHERE article_id = 93
ORDER BY likes DESC
LIMIT 10;
```

#### 2.4 해당 기사 정보 조회

```sql
SELECT 
    a.id,
    a.title,
    a.publisher,
    a.naver_link,
    a.published_at
FROM articles a
WHERE a.id = 93;
```

#### 2.5 댓글 내용 검색

```sql
SELECT 
    id, 
    comment_no, 
    content, 
    username, 
    likes
FROM comments
WHERE 
    article_id = 93 AND 
    content LIKE '%검색어%'
ORDER BY likes DESC;
```

## 기술적 고려사항

### 1. 데이터 품질 및 완전성

수집된 댓글 데이터의 품질과 완전성을 확인하기 위해 다음 사항을 고려했습니다:

- **필드 완전성**: 모든 필드(특히 새로 추가된 필드)가 정상적으로 수집되고 저장되는지 확인
- **데이터 정확성**: 수집된 데이터가 원본 댓글과 일치하는지 확인
- **중복 데이터**: 동일한 댓글이 중복 저장되지 않는지 확인

### 2. 성능 고려사항

대량의 댓글 데이터(877개)를 효율적으로 처리하기 위한 성능 고려사항:

- **배치 처리**: 댓글 데이터를 배치로 처리하여 데이터베이스 부하 감소
- **인덱싱**: `article_id`, `comment_no` 등 자주 조회되는 필드에 대한 인덱스 활용
- **쿼리 최적화**: 조회 쿼리의 성능 최적화를 위한 WHERE 절 및 ORDER BY 절 최적화

### 3. 경고 메시지 처리

수집 과정에서 발생한 경고 메시지(MarkupResemblesLocatorWarning)에 대한 고려:

- 현재는 수집 과정에 영향을 주지 않으므로 무시 가능
- 향후 BeautifulSoup 사용 방식 개선을 통해 경고 메시지 제거 가능성 검토

## 다음 단계

1. **댓글 분석 기능 개발**: 수집된 댓글 데이터를 활용한 감성 분석, 키워드 추출 등의 분석 기능 개발
2. **데이터 시각화 개선**: 댓글 통계 및 분석 결과를 시각화하는 대시보드 개발
3. **경고 메시지 해결**: BeautifulSoup 사용 방식 개선을 통한 경고 메시지 제거
4. **자동화 스케줄링**: 정기적인 댓글 수집 및 분석을 위한 자동화 스케줄링 구현
5. **대용량 데이터 처리 최적화**: 더 많은 기사와 댓글을 효율적으로 처리하기 위한 최적화 작업

## 참고 자료

- [PostgreSQL 쿼리 최적화 가이드](https://www.postgresql.org/docs/current/performance-tips.html)
- [BeautifulSoup 문서](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [SQLAlchemy 배치 처리 가이드](https://docs.sqlalchemy.org/en/14/orm/session_basics.html#unitofwork-operations)
