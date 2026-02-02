# Neo4j Aura 설정 가이드

## 1. Neo4j Aura 계정 생성

### 단계별 설정

1. **Neo4j Aura 웹사이트 접속**
   - https://neo4j.com/cloud/aura/ 방문
   - "Start Free" 버튼 클릭

2. **계정 생성**
   - 이메일 주소로 가입 또는 Google/GitHub 계정으로 로그인
   - 무료 계정 선택 (Free tier)

3. **새 인스턴스 생성**
   - "Create Instance" 버튼 클릭
   - 인스턴스 타입 선택: **AuraDB Free**
   - 이름 설정: 예) `semiconductor-cost-analysis`
   - 리전 선택: 가장 가까운 지역 (예: Seoul, Tokyo)

4. **연결 정보 저장**
   - 인스턴스 생성 후 **반드시 비밀번호를 다운로드/저장**하세요
   - 비밀번호는 한 번만 표시되며 분실 시 재설정 필요
   - Connection URI 저장 (예: `neo4j+s://xxxxx.databases.neo4j.io`)

## 2. 연결 정보 설정

### .env 파일 생성

프로젝트 루트 디렉토리에 `.env` 파일을 생성하고 연결 정보를 입력하세요:

```bash
# .env.example을 복사하여 사용
cp .env.example .env
```

`.env` 파일 내용:

```env
# Neo4j Aura 연결 정보
NEO4J_URI=neo4j+s://your-instance-id.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-generated-password-here
NEO4J_DATABASE=neo4j
```

**주의사항:**
- `NEO4J_URI`: Aura 인스턴스의 Connection URI (neo4j+s:// 형식)
- `NEO4J_USERNAME`: 기본값은 `neo4j`
- `NEO4J_PASSWORD`: 인스턴스 생성 시 생성된 비밀번호
- `.env` 파일은 절대 Git에 커밋하지 마세요 (`.gitignore`에 포함됨)

## 3. 연결 테스트

Python 연결 테스트 스크립트를 실행하여 설정이 올바른지 확인하세요:

```bash
# 가상환경 활성화 (Windows)
venv\Scripts\activate

# 필요한 패키지가 설치되어 있는지 확인
pip install -r requirements.txt

# 연결 테스트 실행
python neo4j/connection_test.py
```

**예상 출력:**

```
============================================================
Neo4j Aura 연결 테스트
============================================================
✓ Neo4j 연결 성공!
  URI: neo4j+s://xxxxx.databases.neo4j.io
  Database: neo4j

✓ 테스트 쿼리 성공!
  Neo4j 버전: 5.x.x
  Edition: enterprise
  현재 노드 개수: 0

✓ 연결 종료
============================================================
```

## 4. Neo4j Browser 접속

Neo4j Aura 콘솔에서 "Query" 버튼을 클릭하면 웹 기반 Neo4j Browser가 열립니다.

### 기본 Cypher 쿼리 테스트

```cypher
// 모든 노드 조회
MATCH (n) RETURN n LIMIT 25;

// 데이터베이스 정보
CALL db.schema.visualization();

// 노드 레이블 확인
CALL db.labels();

// 관계 타입 확인
CALL db.relationshipTypes();
```

## 5. 무료 계정 제한사항

**AuraDB Free 제한:**
- 스토리지: 최대 200,000 노드 + 관계
- 메모리: 1GB
- 동시 연결: 3개
- 데이터 보관: 30일 미사용 시 자동 삭제

**주의:**
- 프로덕션 환경에는 적합하지 않음
- 학습 및 개발 목적으로만 사용
- 중요한 데이터는 별도 백업 필요

## 6. 문제 해결

### 연결 실패 시 확인사항

1. **URI 형식 확인**
   - `neo4j+s://` 프로토콜 사용 (SSL 필수)
   - 포트 번호는 포함하지 않음

2. **방화벽 확인**
   - Neo4j Aura는 7687 포트 사용
   - 회사 방화벽이 차단하는지 확인

3. **비밀번호 재설정**
   - Aura 콘솔에서 인스턴스 선택
   - "Reset Password" 클릭
   - 새 비밀번호를 `.env` 파일에 업데이트

4. **인스턴스 상태 확인**
   - Aura 콘솔에서 인스턴스가 "Running" 상태인지 확인
   - Paused 상태라면 Resume 클릭

## 7. 추가 리소스

- [Neo4j Aura 공식 문서](https://neo4j.com/docs/aura/)
- [Cypher 쿼리 언어 가이드](https://neo4j.com/docs/cypher-manual/current/)
- [Neo4j Python Driver 문서](https://neo4j.com/docs/python-manual/current/)
- [Neo4j Community Forum](https://community.neo4j.com/)

## 다음 단계

연결이 성공적으로 완료되면:
1. 데이터 생성 스크립트 실행 (`python data/generate_data.py`)
2. Neo4j 데이터 로드 (`python neo4j/data_loader.py`)
3. 차이분석 시작 (`python analysis/variance_analyzer.py`)
