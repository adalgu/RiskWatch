# 댓글 스키마 개선 및 데이터베이스 확장

- **날짜**: 2025-02-28
- **작성자**: Gunn Kim
- **관련 이슈**: N/A
- **이전 로그**: 
  - [댓글 수집 및 데이터베이스 저장 기능 구현](./2025-02-28-004-feature-comment-collection-integration.md)
  - [메타데이터 수집 및 저장 스크립트 구현](./2025-02-28-003-feature-metadata-collection-script.md)

## 문제 상황

댓글 수집 및 저장 기능을 구현하는 과정에서, 데이터베이스 스키마와 모델 간의 불일치 문제가 발생했습니다. 기존 접근 방식은 데이터베이스 스키마에 맞추기 위해 모델과 스키마에서 필드를 제거하는 것이었으나, 이로 인해 수집할 수 있는 중요한 정보(프로필 URL, 좋아요 수, 싫어요 수, 답글 수 등)가 손실되는 문제가 있었습니다.

구체적으로 다음과 같은 문제가 있었습니다:

1. **정보 손실**: 수집된 댓글의 중요한 메타데이터(프로필 URL, 좋아요/싫어요 수, 답글 수 등)가 저장되지 않음
2. **데이터 분석 제한**: 저장되지 않은 정보로 인해 향후 댓글 분석 기능이 제한됨
3. **스키마 불일치**: 모델과 데이터베이스 스키마 간의 불일치로 인한 오류 발생

## 해결 전략

데이터베이스 스키마를 확장하여 모델에서 정의된 모든 필드를 저장할 수 있도록 하는 접근 방식을 채택했습니다:

1. **데이터베이스 스키마 확장**: `comments` 테이블에 누락된 컬럼 추가
2. **모델 및 스키마 복원**: 제거했던 필드를 모델과 스키마에 다시 추가
3. **수집 스크립트 업데이트**: 모든 필드를 포함하도록 수집 스크립트 업데이트

## 구현 세부사항

### 1. 데이터베이스 스키마 확장

`comments` 테이블에 다음과 같은 컬럼을 추가했습니다:

```sql
ALTER TABLE comments 
ADD COLUMN profile_url VARCHAR, 
ADD COLUMN likes INTEGER DEFAULT 0, 
ADD COLUMN dislikes INTEGER DEFAULT 0, 
ADD COLUMN reply_count INTEGER DEFAULT 0, 
ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE, 
ADD COLUMN delete_type VARCHAR;
```

이를 통해 다음과 같은 필드를 저장할 수 있게 되었습니다:
- `profile_url`: 댓글 작성자의 프로필 이미지 URL
- `likes`: 댓글의 좋아요 수
- `dislikes`: 댓글의 싫어요 수
- `reply_count`: 댓글의 답글 수
- `is_deleted`: 댓글 삭제 여부
- `delete_type`: 댓글 삭제 유형 (사용자 삭제, 관리자 삭제 등)

### 2. 모델 및 스키마 업데이트

`Comment` 모델과 관련 스키마를 업데이트하여 모든 필드를 포함하도록 했습니다:

```python
# models.py의 Comment 모델 업데이트
class Comment(SQLModel, table=True):
    __tablename__ = "comments"
    __table_args__ = {'extend_existing': True}

    id: Optional[int] = Field(default=None, primary_key=True)
    article_id: int = Field(foreign_key="articles.id")
    comment_no: Optional[str] = None
    parent_comment_no: Optional[str] = None
    content: Optional[str] = None
    username: Optional[str] = None
    profile_url: Optional[str] = None
    timestamp: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="Timestamp of the comment"
    )
    collected_at: datetime = Field(
        default_factory=get_kst_now,
        sa_column=Column(DateTime(timezone=True))
    )
    likes: int = Field(default=0)
    dislikes: int = Field(default=0)
    reply_count: int = Field(default=0)
    is_reply: bool = Field(default=False)
    is_deleted: bool = Field(default=False)
    delete_type: Optional[str] = None
    # ...
```

```python
# schemas/comment.py의 CommentBase 스키마 업데이트
class CommentBase(BaseModel):
    """Base schema for Comment with shared properties."""
    article_id: int
    comment_no: Optional[str] = None
    parent_comment_no: Optional[str] = None
    content: Optional[str] = None
    username: Optional[str] = None
    profile_url: Optional[str] = None
    timestamp: Optional[datetime] = None
    likes: int = 0
    dislikes: int = 0
    reply_count: int = 0
    is_reply: bool = False
    is_deleted: bool = False
    delete_type: Optional[str] = None
```

### 3. 수집 스크립트 업데이트

`collect_and_store_comments.py` 스크립트를 업데이트하여 모든 필드를 포함하도록 했습니다:

```python
# 댓글 데이터 생성 부분 업데이트
comment_data = {
    'article_id': article_id,
    'comment_no': item.get('comment_no'),
    'parent_comment_no': item.get('parent_comment_no'),
    'content': item.get('content'),
    'username': item.get('username'),
    'profile_url': item.get('profile_url'),
    'timestamp': timestamp,
    'likes': item.get('likes', 0),
    'dislikes': item.get('dislikes', 0),
    'reply_count': item.get('reply_count', 0),
    'is_reply': item.get('is_reply', False),
    'is_deleted': item.get('is_deleted', False),
    'delete_type': item.get('delete_type'),
    'collected_at': datetime.now(KST)
}
```

## 기술적 고려사항

### 1. 데이터베이스 마이그레이션 관리

Alembic을 사용한 마이그레이션 관리에 문제가 있어 직접 SQL을 사용하여 스키마를 변경했습니다. 이는 임시 해결책이며, 향후 Alembic 마이그레이션 관리를 개선할 필요가 있습니다:

- 현재 데이터베이스 상태와 Alembic 마이그레이션 기록 간의 불일치 해결
- 마이그레이션 스크립트 관리 개선
- 개발 및 운영 환경 간의 마이그레이션 동기화 방안 마련

### 2. 데이터 일관성

기존에 수집된 댓글 데이터와 새로 수집되는 데이터 간의 일관성을 유지하기 위한 방안을 고려했습니다:

- 새로 추가된 필드에 대한 기본값 설정
- 기존 데이터의 마이그레이션 방안 (필요시)
- 데이터 검증 로직 강화

### 3. 성능 최적화

댓글 데이터가 증가함에 따른 성능 최적화 방안을 고려했습니다:

- 인덱싱 전략 검토
- 배치 처리 최적화
- 쿼리 성능 모니터링

## 다음 단계

1. **Alembic 마이그레이션 정리**: 현재 데이터베이스 상태와 Alembic 마이그레이션 기록 간의 불일치 해결
2. **댓글 분석 기능 개발**: 저장된 추가 정보를 활용한 댓글 분석 기능 개발
3. **데이터 시각화 개선**: 댓글 통계 및 분석 결과 시각화 기능 개발
4. **성능 모니터링**: 대량의 댓글 데이터 처리 시 성능 모니터링 및 최적화

## 참고 자료

- [SQLModel 공식 문서](https://sqlmodel.tiangolo.com/)
- [Alembic 마이그레이션 관리](https://alembic.sqlalchemy.org/en/latest/)
- [PostgreSQL 스키마 변경 가이드](https://www.postgresql.org/docs/current/ddl-alter.html)
