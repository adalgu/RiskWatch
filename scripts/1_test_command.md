PostreSQL 데이터베이스에 연결하고 데이터를 조회하는 명령어는 다음과 같습니다:
1. 데이터베이스에 접속
터미널에서 PostgreSQL 컨테이너 내부의 news_db 데이터베이스에 접속합니다.

bash
코드 복사
docker exec -it riskwatch-postgres-1 psql -U postgres -d news_db
2. 테이블 확인
데이터베이스 내부에서 테이블 목록을 확인합니다.

sql
코드 복사
\dt
예상되는 테이블 목록:

articles
contents
comments
comment_stats
article_stats
3. 테스트 쿼리 실행
articles 테이블에 데이터가 있는지 확인하려면 쿼리를 실행해보세요.

sql
코드 복사
SELECT main_keyword, id, title, naver_link, publisher, published_at FROM articles ORDER BY published_at DESC LIMIT 50;
초기에는 데이터가 없을 수 있으므로, 결과가 없더라도 오류가 발생하지 않는지 확인하는 것이 중요합니다.

4. 데이터 삽입 (선택 사항)
테스트를 위해 데이터를 삽입해볼 수 있습니다.

sql
코드 복사
INSERT INTO articles (main_keyword, naver_link, title) VALUES ('test_keyword', 'http://example.com', 'Test Article');
다시 조회하여 데이터가 삽입되었는지 확인합니다.

sql
코드 복사
SELECT * FROM articles;
5. 컨테이너 상태 확인
Docker 컨테이너가 정상적으로 실행 중인지 확인합니다.

bash
코드 복사
docker ps
STATUS 열에 (healthy) 표시가 있는지 확인하세요.


docker-compose exec fast_api python -m news_collector.collectors.MetadataCollector --keyword "카카오모빌리티" --method SEARCH --start-date 2024-11-29 --end-date 2024-12-02 --min-delay 1 --max-delay 3 --batch-size 10000 --auto

docker-compose exec fast_api python -m news_collector.collectors.metadata --method SEARCH --keyword "카카오모빌리티" --start_date 2024-11-29 --end_date 2024-12-02 --auto



docker-compose exec fast_api python -m news_collector.collectors.comments --article_url https://n.news.naver.com/article/214/0001391166

https://n.news.naver.com/mnews/article/421/0007947276

docker-compose exec fast_api python -m news_collector.collectors.comments --article_url "https://n.news.naver.com/mnews/article/001/0014175075?sid=105" --auto


--method SEARCH --keyword "카카오모빌리티" --start_date 2024-11-29 --end_date 2024-12-02

--article_url


# 메타데이터 수집
python interactive_collector.py metadata --keyword "카카오" --method SEARCH

curl -X POST "http://localhost:8000/api/v1/collectors/metadata/start" \
  -H "Content-Type: application/json" \
  -d '{
    "keyword": "카카오모빌리티",
    "method": "search",
    "start_date": "2024-11-01T00:00:00Z",
    "end_date": "2024-11-02T00:00:00Z",
    "department": "news",
    "priority": "high"
  }'


  curl -X POST "http://localhost:8000/api/v1/collectors/metadata/start" \
  -H "Content-Type: application/json" \
  -d '{
    "keyword": "카카오모빌리티",
    "method": "SEARCH",
    "start_date": "2024-09-01T00:00:00Z",
    "end_date": "2024-09-02T00:00:00Z"
  }'


# 댓글 수집
python interactive_collector.py comments --urls-file articles.txt


docker-compose exec -it news_storage python -m scripts.interactive_test metadata --keyword "카카오모빌리티" --method API

docker-compose exec -it news_storage python -m scripts.interactive_test metadata --keyword "카카오모빌리티" --method SEARCH --start-date 2024-11-29 --end-date 2024-12-02 --min-delay 1 --max-delay 3 --batch-size 10000 --auto
docker-compose exec -it news_storage python -m scripts.interactive_test metadata --keyword "카카오모빌리티" --method SEARCH --start-date 2024-09-01 --end-date 2024-12-03 --min-delay 1 --max-delay 3 --batch-size 10000 --auto

docker-compose exec -it news_storage python -m scripts.interactive_test metadata --keyword "카카오모빌리티" --method SEARCH --start-date 2024-08-01 --end-date 2024-08-31 --min-delay 1 --max-delay 3 --batch-size 10000 --auto



docker-compose exec -it news_storage python -m scripts.interactive_test comments --keyword "카카오모빌리티" --start-date 2024-11-29 --end-date 2024-12-02 --min-delay 1 --max-delay 3 --auto
docker-compose exec -it news_storage python -m scripts.interactive_test comments --keyword "카카오모빌리티" --start-date 2024-09-01 --end-date 2024-12-03 --min-delay 1 --max-delay 3 --auto

docker-compose exec -it news_storage python -m scripts.interactive_test comments --keyword "카카오모빌리티" --start-date 2024-11-01 --end-date 2024-12-03 --min-delay 1 --max-delay 4 --auto

docker-compose exec -it news_storage python -m scripts.interactive_test metadata --keyword "카카오모빌리티" --method SEARCH --start-date 2024-10-01 --end-date 2024-10-02 --min-delay 1 --max-delay 3 --batch-size 10000 --auto

docker-compose exec -it news_storage python -m scripts.interactive_test comments --keyword "카카오모빌리티" --start-date 2024-10-01 --end-date 2024-10-31 --min-delay 1 --max-delay 4 --auto

docker exec -it riskwatch-postgres-1 psql -U postgres -d news_db -c "SELECT main_keyword, id, title, naver_link, publisher, published_at FROM articles ORDER BY published_at DESC LIMIT 50;"

docker exec -it riskwatch-postgres-1 psql -U postgres -d news_db -c "SELECT * FROM comments LIMIT 50;"



안녕하세요! 주신 명령어를 참고하여 PostgreSQL 데이터베이스에서 테이블 목록을 확인하고 특정 테이블의 데이터를 조회하는 명령어를 아래와 같이 제공해 드립니다.

1. 데이터베이스에 있는 테이블 목록을 확인하는 명령어

데이터베이스 내의 모든 테이블을 확인하기 위해 \dt 메타 명령어를 사용할 수 있습니다. 이를 docker exec와 함께 사용하는 방법은 다음과 같습니다:

docker exec -it riskwatch-postgres-1 psql -U postgres -d news_db -c "\dt"

또는, SQL 쿼리를 사용하여 information_schema에서 테이블 목록을 조회할 수도 있습니다:

docker exec -it riskwatch-postgres-1 psql -U postgres -d news_db -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"

2. 특정 테이블의 데이터를 확인하는 명령어

특정 테이블(예: articles)의 데이터를 조회하려면 다음과 같은 명령어를 사용할 수 있습니다. 이 예제에서는 articles 테이블의 모든 데이터를 상위 50개만 조회합니다:

docker exec -it riskwatch-postgres-1 psql -U postgres -d news_db -c "SELECT * FROM articles LIMIT 50;"
docker exec -it riskwatch-postgres-1 psql -U postgres -d news_db -c "SELECT * FROM comments LIMIT 50;"

또는, 특정 컬럼을 선택하여 데이터를 조회할 수도 있습니다. 예를 들어, main_keyword, id, title, naver_link, publisher, published_at 컬럼을 조회하려면:

docker exec -it riskwatch-postgres-1 psql -U postgres -d news_db -c "SELECT main_keyword, id, title, naver_link, publisher, published_at FROM articles ORDER BY published_at DESC LIMIT 50;"

이 명령어들은 데이터베이스의 상태를 확인하고 필요한 데이터를 효율적으로 조회하는 데 도움이 될 것입니다. 추가적인 질문이 있으시면 언제든지 문의해 주세요!

안녕하세요! 추가 요청하신 사항에 대해 다음과 같이 안내드립니다.

3. articles 테이블의 칼럼 목록을 확인하는 명령어

articles 테이블에 어떤 칼럼들이 있는지 확인하려면 다음 명령어를 사용하실 수 있습니다:

방법 1: \d 메타 명령어 사용

docker exec -it riskwatch-postgres-1 psql -U postgres -d news_db -c "\d articles"

이 명령어는 articles 테이블의 구조(칼럼 이름, 데이터 타입 등)를 상세히 보여줍니다.

방법 2: information_schema.columns 조회

docker exec -it riskwatch-postgres-1 psql -U postgres -d news_db -c "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'articles';"

이 명령어는 information_schema를 통해 articles 테이블의 칼럼 이름과 데이터 타입을 리스트업합니다.

4. 특정 칼럼값이 True인 경우만 추출하는 명령어

특정 칼럼의 값이 True인 행만 조회하려면 다음과 같은 명령어를 사용할 수 있습니다. 여기서는 예시로 is_published라는 칼럼을 사용하겠습니다. 실제 사용하실 칼럼 이름으로 대체해주세요.

모든 칼럼 조회

docker exec -it riskwatch-postgres-1 psql -U postgres -d news_db -c "SELECT * FROM articles WHERE is_published = TRUE LIMIT 50;"

특정 칼럼만 선택하여 조회

docker exec -it riskwatch-postgres-1 psql -U postgres -d news_db -c "SELECT main_keyword, id, title, naver_link, publisher, published_at FROM articles WHERE is_published = TRUE ORDER BY published_at DESC LIMIT 50;"

참고 사항:
	•	is_published 대신 실제로 True 값을 확인하고자 하는 칼럼명을 사용하세요.
	•	LIMIT 50은 상위 50개의 결과만 표시하도록 제한합니다. 필요에 따라 숫자를 조정하거나 제거할 수 있습니다.
	•	ORDER BY published_at DESC는 published_at 컬럼을 기준으로 내림차순 정렬합니다. 다른 정렬 기준이 필요하면 해당 부분을 수정하세요.

이 명령어들은 특정 조건에 맞는 데이터를 효율적으로 조회하는 데 도움이 될 것입니다. 추가적인 질문이 있으시면 언제든지 문의해 주세요!

감사합니다.




macmini@maegminiui-Macmini ~/study/RiskWatch % docker exec -it riskwatch-postgres-1 psql -U postgres

psql (14.15 (Debian 14.15-1.pgdg120+1))
Type "help" for help.

postgres=# CREATE DATABASE news_db;
CREATE DATABASE
postgres=# \l
postgres=# \dt
Did not find any relations.
postgres=# exit
macmini@maegminiui-Macmini ~/study/RiskWatch % docker exec -it riskwatch-postgres-1 ls /docker-entrypoint-initdb.d/

init.sql
macmini@maegminiui-Macmini ~/study/RiskWatch % docker-compose down -v
[+] Running 9/9
 ✔ Container riskwatch-news_data_dashboard-1  Removed                                                            0.5s 
 ✔ Container riskwatch-news_storage-1         Removed                                                            1.0s 
 ✔ Container riskwatch-news_ui-1              Removed                                                            0.4s 
 ✔ Container riskwatch-rabbitmq-1             Removed                                                            1.6s 
 ✔ Container riskwatch-chrome-1               Removed                                                            4.1s 
 ✔ Container riskwatch-postgres-1             Removed                                                            0.2s 
 ✔ Container riskwatch-selenium-hub-1         Removed                                                            2.1s 
 ✔ Volume riskwatch_postgres_data             Removed                                                            0.1s 
 ✔ Network riskwatch_default                  Removed                                                            0.1s 
macmini@maegminiui-Macmini ~/study/RiskWatch % 


macmini@maegminiui-Macmini ~/study/RiskWatch % docker exec -it riskwatch-postgres-1 psql -U postgres -d news_db -c "\dt"
             List of relations
 Schema |     Name      | Type  |  Owner   
--------+---------------+-------+----------
 public | article_stats | table | postgres
 public | articles      | table | postgres
 public | comment_stats | table | postgres
 public | comments      | table | postgres
 public | contents      | table | postgres
(5 rows)

macmini@maegminiui-Macmini ~/study/RiskWatch % docker exec -it riskwatch-postgres-1 psql -U postgres -d news_db -c "SELECT a.id, a.title, COUNT(DISTINCT c
.id) as comment_count, COUNT(DISTINCT cont.id) as content_count FROM articles a LEFT JOIN comments c ON a.id = c.article_id LEFT JOIN contents cont ON a.i
d = cont.article_id GROUP BY a.id, a.title ORDER BY a.id DESC LIMIT 5;"
 id | title | comment_count | content_count 
----+-------+---------------+---------------
(0 rows)

macmini@maegminiui-Macmini ~/study/RiskWatch % docker exec -it riskwatch-postgres-1 psql -U postgres -d news_db -c "SELECT main_keyword, id, title, naver_link, publisher, published_at FROM articles ORDER BY published_at DESC LIMIT 50;"
 main_keyword | id | title | naver_link | publisher | published_at 
--------------+----+-------+------------+-----------+--------------
(0 rows)

macmini@maegminiui-Macmini ~/study/RiskWatch % docker volume ls | grep postgres
local     riskwatch_postgres_data
macmini@maegminiui-Macmini ~/study/RiskWatch % docker-compose stop postgres && docker-compose rm -f postgres && docker-compose up -d postgres
[+] Stopping 1/1
 ✔ Container riskwatch-postgres-1  Stopped                                                                                                           0.1s 
Going to remove riskwatch-postgres-1
[+] Removing 1/0
 ✔ Container riskwatch-postgres-1  Removed                                                                                                           0.0s 
[+] Running 1/1
 ✔ Container riskwatch-postgres-1  Started                                                                                                           0.4s 
macmini@maegminiui-Macmini ~/study/RiskWatch % docker exec -it riskwatch-postgres-1 psql -U postgres -d news_db -c "SELECT main_keyword, id, title, naver_
link, publisher, published_at FROM articles ORDER BY published_at DESC LIMIT 5;"
 main_keyword | id | title | naver_link | publisher | published_at 
--------------+----+-------+------------+-----------+--------------
(0 rows)

macmini@maegminiui-Macmini ~/study/RiskWatch % docker-compose ps
NAME                              IMAGE                            COMMAND                  SERVICE               CREATED             STATUS                       PORTS
riskwatch-chrome-1                seleniarm/node-chromium:latest   "/opt/bin/entry_poin…"   chrome                2 hours ago         Up 2 hours                   0.0.0.0:5900->5900/tcp
riskwatch-dev-1                   riskwatch-dev                    "sleep infinity"         dev                   2 hours ago         Up 2 hours                   
riskwatch-news_data_dashboard-1   riskwatch-news_data_dashboard    "python -m news_stor…"   news_data_dashboard   2 hours ago         Up 2 hours                   0.0.0.0:5050->5000/tcp
riskwatch-news_storage-1          riskwatch-news_storage           "python -m news_stor…"   news_storage          2 hours ago         Up 2 hours                   0.0.0.0:8000->8000/tcp
riskwatch-news_ui-1               riskwatch-news_ui                "streamlit run app.p…"   news_ui               2 hours ago         Up 2 hours                   0.0.0.0:8501->8501/tcp
riskwatch-postgres-1              postgres:14                      "docker-entrypoint.s…"   postgres              About an hour ago   Up About an hour (healthy)   0.0.0.0:5432->5432/tcp
riskwatch-rabbitmq-1              rabbitmq:3-management            "docker-entrypoint.s…"   rabbitmq              2 hours ago         Up 2 hours                   4369/tcp, 5671/tcp, 0.0.0.0:5672->5672/tcp, 15671/tcp, 15691-15692/tcp, 25672/tcp, 0.0.0.0:15672->15672/tcp
riskwatch-selenium-hub-1          seleniarm/hub:latest             "/opt/bin/entry_poin…"   selenium-hub          2 hours ago         Up 2 hours                   4442-4443/tcp, 0.0.0.0:4444->4444/tcp
macmini@maegminiui-Macmini ~/study/RiskWatch % docker exec -it riskwatch-postgres-1 psql -U postgres -d news_db -c "SELECT main_keyword, id, title, naver_link, publisher, published_at FROM articles ORDER BY published_at DESC LIMIT 50;"
psql: error: connection to server on socket "/var/run/postgresql/.s.PGSQL.5432" failed: FATAL:  database "news_db" does not exist
macmini@maegminiui-Macmini ~/study/RiskWatch % docker exec -it riskwatch-postgres-1 psql -U postgres

psql (14.15 (Debian 14.15-1.pgdg120+1))
Type "help" for help.

postgres=# \l
postgres=# :q
postgres-# exit
Use \q to quit.
postgres-# \q
macmini@maegminiui-Macmini ~/study/RiskWatch % docker volume ls
DRIVER    VOLUME NAME
local     2dd62fab08d1ee63af96664fbffeefd06a75d8c2284cce704450ec7984c03585
local     69c4a747ef649e5cd52b304523c00740d463624e31d4ce2f1489e53519de08d1
local     buildx_buildkit_heuristic_engelbart0_state
local     riskwatch_postgres_data
local     vscode
macmini@maegminiui-Macmini ~/study/RiskWatch % docker exec -it riskwatch-postgres-1 netstat -an | grep 5432

macmini@maegminiui-Macmini ~/study/RiskWatch % docker network ls

NETWORK ID     NAME                DRIVER    SCOPE
3c4995195ee3   bridge              bridge    local
93a6af492236   host                host      local
afbc2fe49f68   none                null      local
daa0f1b6ed23   riskwatch_default   bridge    local
macmini@maegminiui-Macmini ~/study/RiskWatch % docker logs riskwatch-postgres-1


PostgreSQL Database directory appears to contain a database; Skipping initialization

2024-11-28 23:24:11.930 UTC [1] LOG:  starting PostgreSQL 14.15 (Debian 14.15-1.pgdg120+1) on aarch64-unknown-linux-gnu, compiled by gcc (Debian 12.2.0-14) 12.2.0, 64-bit
2024-11-28 23:24:11.931 UTC [1] LOG:  listening on IPv4 address "0.0.0.0", port 5432
2024-11-28 23:24:11.931 UTC [1] LOG:  listening on IPv6 address "::", port 5432
2024-11-28 23:24:11.933 UTC [1] LOG:  listening on Unix socket "/var/run/postgresql/.s.PGSQL.5432"
2024-11-28 23:24:11.936 UTC [27] LOG:  database system was shut down at 2024-11-28 23:24:11 UTC
2024-11-28 23:24:11.940 UTC [1] LOG:  database system is ready to accept connections
2024-11-28 23:52:09.152 UTC [2384] FATAL:  password authentication failed for user "postgres"
2024-11-28 23:52:09.152 UTC [2384] DETAIL:  Connection matched pg_hba.conf line 100: "host all all all scram-sha-256"
2024-11-28 23:52:10.348 UTC [2385] FATAL:  password authentication failed for user "postgres"
2024-11-28 23:52:10.348 UTC [2385] DETAIL:  Connection matched pg_hba.conf line 100: "host all all all scram-sha-256"
2024-11-28 23:52:24.637 UTC [2411] FATAL:  password authentication failed for user "postgres"
2024-11-28 23:52:24.637 UTC [2411] DETAIL:  Connection matched pg_hba.conf line 100: "host all all all scram-sha-256"
2024-11-28 23:52:25.775 UTC [2412] FATAL:  password authentication failed for user "postgres"
2024-11-28 23:52:25.775 UTC [2412] DETAIL:  Connection matched pg_hba.conf line 100: "host all all all scram-sha-256"
2024-11-28 23:52:42.118 UTC [2451] FATAL:  database "template0" is not currently accepting connections
2024-11-28 23:52:46.541 UTC [2454] ERROR:  cannot drop the currently open database
2024-11-28 23:52:46.541 UTC [2454] STATEMENT:  DROP DATABASE postgres;
2024-11-28 23:52:50.799 UTC [2473] FATAL:  database "news_db" does not exist