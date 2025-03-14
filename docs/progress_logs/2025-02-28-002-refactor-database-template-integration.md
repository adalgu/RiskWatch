# Full Stack FastAPI Template 데이터베이스 컴포넌트 통합

- **날짜**: 2025-02-28
- **작성자**: Gunn Kim
- **관련 이슈**: N/A
- **이전 로그**: [메타데이터 수집 스크립트 오류 해결](./2025-02-28-001-bug-fix-metadata-collection.md)

## 문제 상황

RiskWatch 프로젝트의 데이터베이스 관련 코드에서 다음과 같은 문제점들이 발견되었습니다:

1. **복잡한 데이터베이스 연결 관리**: 연결 풀링, 세션 관리, 트랜잭션 처리 등이 최적화되지 않음
2. **일관성 없는 CRUD 작업**: 모델마다 다른 방식으로 데이터베이스 작업 수행
3. **데이터 검증 부족**: 입력 데이터에 대한 체계적인 검증 메커니즘 부재
4. **의존성 주입 패턴 미적용**: FastAPI 엔드포인트에서 데이터베이스 세션 관리가 비효율적

이러한 문제들로 인해 코드 중복이 발생하고, 오류 처리가 불완전하며, 유지보수가 어려워지는 상황이었습니다.

## 해결 전략

Full Stack FastAPI Template의 데이터베이스 관련 패턴을 분석하고, 이를 RiskWatch 프로젝트에 통합하는 전략을 채택했습니다:

1. **템플릿 분석**: Full Stack FastAPI Template의 데이터베이스 관련 컴포넌트 분석
2. **핵심 컴포넌트 식별**: 데이터베이스 연결, 세션 관리, CRUD 작업, 스키마 검증 등의 핵심 컴포넌트 식별
3. **통합 계획 수립**: 기존 코드를 유지하면서 템플릿 패턴을 적용하는 방법 계획
4. **점진적 적용**: 스크립트를 통한 변경사항 적용 및 마이그레이션 생성

## 구현 세부사항

### 1. 데이터베이스 연결 및 세션 관리 개선

기존 `database.py` 파일을 템플릿 패턴에 맞게 재구성했습니다:

```python
# news_storage/src/database.py
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

# 향상된 연결 풀링 설정
engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv('DB_ECHO', 'False').lower() == 'true',
    future=True,
    pool_pre_ping=True,  # 연결 확인
    pool_size=int(os.getenv('DB_POOL_SIZE', '5')),
    max_overflow=int(os.getenv('DB_MAX_OVERFLOW', '10')),
    pool_timeout=int(os.getenv('DB_POOL_TIMEOUT', '30')),
    pool_recycle=int(os.getenv('DB_POOL_RECYCLE', '1800')),
)

# 세션 팩토리 생성
async_session_factory = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# FastAPI 의존성 주입을 위한 함수
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

### 2. 의존성 주입 패턴 적용

FastAPI 엔드포인트에서 데이터베이스 세션을 쉽게 사용할 수 있도록 의존성 주입 패턴을 적용했습니다:

```python
# news_storage/src/deps.py
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from news_storage.src.database import get_db

# 타입 어노테이션을 통한 의존성 주입
SessionDep = Annotated[AsyncSession, Depends(get_db)]
```

### 3. 제네릭 CRUD 작업 구현

모든 모델에 공통으로 적용할 수 있는 제네릭 CRUD 클래스를 구현했습니다:

```python
# news_storage/src/crud/base.py
class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model
    
    async def get(self, db: AsyncSession, id: Any) -> Optional[ModelType]:
        return await db.get(self.model, id)
    
    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        statement = select(self.model).offset(skip).limit(limit)
        results = await db.execute(statement)
        return results.scalars().all()
    
    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
        obj_in_data = jsonable_encoder(obj_in)
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    # update, remove 등 다른 메서드 구현...
```

### 4. 모델별 CRUD 클래스 구현

각 모델에 특화된 CRUD 클래스를 구현했습니다:

```python
# news_storage/src/crud/article.py
class CRUDArticle(CRUDBase[Article, ArticleCreate, ArticleUpdate]):
    async def get_by_naver_link(
        self, db: AsyncSession, *, main_keyword: str, naver_link: str
    ) -> Optional[Article]:
        statement = select(Article).where(
            (Article.main_keyword == main_keyword) & 
            (Article.naver_link == naver_link)
        )
        results = await db.execute(statement)
        return results.scalar_one_or_none()
    
    async def create_with_upsert(
        self, db: AsyncSession, *, obj_in: ArticleCreate
    ) -> Article:
        # upsert 로직 구현...
```

### 5. Pydantic 스키마 구현

데이터 검증을 위한 Pydantic 스키마를 구현했습니다:

```python
# news_storage/src/schemas/article.py
class ArticleBase(BaseModel):
    main_keyword: str = Field(default="default_keyword")
    naver_link: str
    title: str
    # 기타 필드...

class ArticleCreate(ArticleBase):
    collected_at: datetime = Field(default_factory=datetime.now)

class ArticleUpdate(BaseModel):
    main_keyword: Optional[str] = None
    naver_link: Optional[str] = None
    # 기타 필드...
```

### 6. Alembic 설정 개선

마이그레이션 관리를 위한 Alembic 설정을 개선했습니다:

```python
# alembic/env.py
from news_storage.src.models import Article, Content, Comment, CommentStats, SQLModel

target_metadata = SQLModel.metadata

def get_url():
    return os.getenv('DATABASE_URL', 'postgresql+psycopg2://postgres:password@postgres:5432/news_db')

# 마이그레이션 실행 함수 구현...
```

### 7. 적용 스크립트 작성

변경사항을 쉽게 적용할 수 있는 스크립트를 작성했습니다:

```bash
# news_storage/scripts/apply_template_changes.sh
#!/bin/bash
# 데이터베이스 템플릿 변경사항 적용 스크립트

# 백업 생성
cp -v news_storage/src/database.py news_storage/src/database.py.bak
cp -v alembic/env.py alembic/env.py.bak
cp -v alembic.ini alembic.ini.bak

# 새 파일 적용
cp -v news_storage/src/database.py.new news_storage/src/database.py
cp -v alembic/env.py.new alembic/env.py
cp -v alembic.ini.new alembic.ini

# 디렉토리 생성
mkdir -p news_storage/src/crud
mkdir -p news_storage/src/schemas

# 파일 복사
# CRUD 및 스키마 파일 복사 로직...

# 마이그레이션 생성
alembic revision --autogenerate -m "Apply Full Stack FastAPI Template patterns"
```

## 기술적 고려사항

### 1. 기존 코드와의 호환성

기존 코드와의 호환성을 유지하기 위해 다음 사항을 고려했습니다:

- 기존 모델 구조 유지 (Article, Content, Comment, CommentStats)
- 기존 API 엔드포인트 인터페이스 유지
- 백업 파일 생성을 통한 롤백 가능성 확보

### 2. 성능 최적화

데이터베이스 연결 및 쿼리 성능을 최적화하기 위해 다음 기법을 적용했습니다:

- 연결 풀링 설정 최적화 (pool_size, max_overflow 등)
- 연결 재활용 (pool_recycle)
- 연결 확인 (pool_pre_ping)
- 비동기 세션 관리

### 3. 트랜잭션 관리

트랜잭션 관리를 개선하여 데이터 일관성을 보장했습니다:

- 세션 컨텍스트 관리자를 통한 자동 커밋/롤백
- 예외 발생 시 자동 롤백
- 명시적 트랜잭션 범위 설정

### 4. 마이그레이션 전략

데이터베이스 스키마 변경을 관리하기 위한 전략을 수립했습니다:

- Alembic을 통한 자동 마이그레이션 생성
- 마이그레이션 스크립트 검토 및 수정
- 롤백 메커니즘 구현

## 다음 단계

1. **API 엔드포인트 리팩토링**: 새로운 의존성 주입 패턴을 활용하여 API 엔드포인트 리팩토링
2. **테스트 작성**: 새로운 CRUD 작업 및 데이터베이스 연결에 대한 단위 테스트 및 통합 테스트 작성
3. **성능 모니터링**: 개선된 데이터베이스 연결 및 쿼리 성능 모니터링
4. **문서화 개선**: API 문서 및 개발자 가이드 업데이트

## 참고 자료

- [Full Stack FastAPI Template](https://github.com/fastapi/full-stack-fastapi-template)
- [SQLModel 공식 문서](https://sqlmodel.tiangolo.com/)
- [FastAPI 의존성 주입 가이드](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [Alembic 마이그레이션 가이드](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [SQLAlchemy 비동기 지원](https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html)
