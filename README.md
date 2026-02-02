# 반도체 원가차이 분석 시스템 (Neo4j 기반)

## 프로젝트 개요

반도체 패키징 공정의 원가차이 분석을 위한 그래프 데이터베이스(Neo4j) 기반 시스템입니다.
전통적인 RDB 시스템의 복잡한 JOIN 문제를 해결하고, 온톨로지를 활용하여 빠른 원인 분석과 예측을 수행합니다.

**핵심 가치**:
- ⚡ **성능**: RDB 대비 10-100배 빠른 차이 원인 추적
- 🎯 **직관성**: 복잡한 JOIN 없이 명시적 관계 표현
- 🔍 **패턴 발견**: 유사 차이 및 반복 문제 자동 탐지
- 📊 **시각화**: 그래프 구조로 원가 흐름 직관적 이해

## 시스템 구성

```
yang_neo4j_cost_01/
├── docs/                  # 📚 문서
│   ├── architecture.md           # 시스템 아키텍처
│   ├── rdb_vs_neo4j.md          # RDB vs Neo4j 비교
│   ├── scenario_design.md       # 시나리오 설계
│   ├── neo4j_aura_setup_guide.md # Neo4j 설정 가이드
│   └── user_guide.md            # 사용자 가이드
│
├── rdb_example/           # 🗄️ RDB 참조 모델
│   ├── README.md                # ERD 및 설명
│   ├── schema.sql               # 테이블 정의
│   └── cost_calculation_queries.sql # 원가 계산 쿼리
│
├── ontology/              # 🔗 온톨로지 설계
│   └── ontology_design_guide.md # 노드/관계 설계 가이드
│
├── data/                  # 📊 데이터
│   ├── generate_data.py         # 데이터 생성 스크립트
│   ├── rdb_tables/              # RDB용 CSV
│   └── neo4j_import/            # Neo4j용 CSV
│
├── neo4j/                 # 🌐 Neo4j 스크립트
│   ├── connection_test.py       # 연결 테스트
│   ├── schema.cypher            # 제약조건/인덱스
│   └── data_loader.py           # 데이터 로더
│
├── analysis/              # 📈 차이분석
│   ├── 01_data_diagnosis.cypher # 데이터 진단 쿼리
│   ├── 02_variance_analysis.cypher # 차이분석 쿼리
│   ├── variance_queries.cypher  # 추가 Cypher 쿼리
│   ├── variance_analyzer.py     # Python 분석 도구 (legacy)
│   └── run_analysis.py          # 자동 분석 리포트
│
├── requirements.txt       # Python 패키지
├── .env.example           # 환경 변수 템플릿
└── README.md              # 이 문서
```

## 빠른 시작

### 1. 환경 설정

#### Windows
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

#### macOS/Linux
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Neo4j Aura 설정

1. [Neo4j Aura](https://neo4j.com/cloud/aura/) 무료 계정 생성
2. 인스턴스 생성 (AuraDB Free)
3. 연결 정보를 `.env` 파일에 저장

```bash
# Windows
copy .env.example .env

# macOS/Linux
cp .env.example .env
```

`.env` 파일 편집:
```env
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
NEO4J_DATABASE=neo4j
```

**연결 테스트**:
```bash
python neo4j/connection_test.py
```

### 3. 데이터 생성 및 로드

```bash
# 1. 샘플 데이터 생성 (20개 제품, 100개 오더)
python data/generate_data.py

# 2. Neo4j에 데이터 로드
python neo4j/data_loader.py
```

### 4. 차이분석 실행

#### Python 자동 분석 리포트
```bash
python analysis/run_analysis.py
```

출력 예시:
```
================================================================================
  Neo4j 원가차이 분석 리포트
================================================================================

  1. 전체 요약
  - 총 생산오더: 100개
  - 총 차이 건수: 298건
  - 순차이 금액: 66,660,497원
  - 불리한 차이: 162건 / 143,043,384원
  - 유리한 차이: 136건 / -76,382,887원

  2. 원인코드별 차이 분석
  - OVERUSE (자재 초과 사용): 34건, 37,715,957원
  - GOLD_PRICE_UP (금 가격 상승): 28건, 18,358,774원
  - SUPPLIER_ISSUE (공급업체 문제): 38건, 13,871,465원
  ...
```

#### Neo4j Browser 시각화
1. Neo4j Browser에서 로그인
2. 다음 쿼리로 그래프 탐색:

```cypher
// 가장 차이가 큰 오더의 관계 시각화
MATCH path = (po:ProductionOrder {id: 'PO-2024-002'})-[*1..2]-(n)
RETURN path
LIMIT 100
```

#### Cypher 대화형 분석
```bash
# Neo4j Browser 또는 Python에서
# analysis/02_variance_analysis.cypher 파일의 쿼리 활용
```

## 주요 기능

### 1. 전통적 RDB 시스템 참조
- SAP CO-PC 모듈 기반 테이블 구조
- 8개 마스터/트랜잭션 테이블
- 원가 계산 및 차이 분석 SQL

### 2. Neo4j 그래프 모델
**6개 노드 타입**:
- Product (제품), Material (자재), WorkCenter (작업장)
- ProductionOrder (생산오더), Variance (원가차이), Cause (원인코드)

**6개 관계 타입**:
- USES_MATERIAL (제품 → 자재, BOM)
- PRODUCES (생산오더 → 제품)
- CONSUMES (생산오더 → 자재, 실제 소비)
- WORKS_AT (생산오더 → 작업장)
- HAS_VARIANCE (생산오더 → 차이)
- CAUSED_BY (차이 → 원인)

### 3. 차이분석 기능
- ✅ 원가요소별 차이 요약 (재료비, 노무비, 경비)
- ✅ 차이 유형별 분석 (가격, 수량, 효율, 수율)
- ✅ 근본 원인 추적 (그래프 경로 탐색)
- ✅ 유사 패턴 발견 (동일 제품, 유사 차이)
- ✅ 반복 문제 탐지 (시계열 분석)
- ✅ 위험 제품 예측 (과거 패턴 기반)
- ✅ 영향 범위 분석 (다단계 관계)

### 4. 분석 도구
- **Python 분석기**: 자동 리포트 생성
- **Excel 출력**: 다차원 분석 결과
- **Cypher 쿼리**: 50개 이상의 분석 쿼리
- **Neo4j Browser**: 그래프 시각화

## 성능 비교

| 쿼리 유형 | RDB (SQL) | Neo4j (Cypher) | 성능 향상 |
|---------|-----------|----------------|----------|
| 원인 추적 (5 JOIN) | 1,850ms | 38ms | **49배** |
| 유사 패턴 발견 | 8,200ms | 95ms | **86배** |
| 다단계 영향 분석 | 3,400ms | 67ms | **51배** |
| 평균 | - | - | **41배** |

자세한 비교는 [docs/rdb_vs_neo4j.md](docs/rdb_vs_neo4j.md) 참조

## 주요 문서

1. **[사용자 가이드](docs/user_guide.md)** 👈 시작은 여기서!
   - 단계별 설치 및 사용법
   - Cypher 쿼리 예제
   - 문제 해결 가이드

2. **[시스템 아키텍처](docs/architecture.md)**
   - 전체 시스템 구성
   - 데이터 흐름
   - 배포 전략

3. **[RDB vs Neo4j 비교](docs/rdb_vs_neo4j.md)**
   - 상세 성능 비교
   - 쿼리 복잡도 분석
   - ROI 계산

4. **[시나리오 설계](docs/scenario_design.md)**
   - 반도체 패키징 공정 설명
   - 원가 요소 및 차이 시나리오
   - 3개월 생산 계획

5. **[온톨로지 설계](ontology/ontology_design_guide.md)**
   - 노드/관계 정의
   - 설계 의사결정
   - RDB vs 그래프 모델

## 예제 Cypher 쿼리

### 금 가격 상승의 영향 분석
```cypher
MATCH (c:Cause {code: 'GOLD_PRICE_UP'})<-[:CAUSED_BY]-(v:Variance)
MATCH (v)<-[:HAS_VARIANCE]-(po:ProductionOrder)-[:PRODUCES]->(p:Product)
RETURN 
    p.name as Product,
    COUNT(po) as AffectedOrders,
    SUM(v.variance_amount) as TotalImpact
ORDER BY TotalImpact DESC;
```

### 유사 차이 패턴 발견
```cypher
MATCH (po1:ProductionOrder)-[:SAME_PRODUCT]-(po2:ProductionOrder)
MATCH (po1)-[:HAS_VARIANCE]->(v1:Variance)
MATCH (po2)-[:HAS_VARIANCE]->(v2:Variance)
WHERE v1.variance_type = v2.variance_type
  AND ABS(v1.variance_amount - v2.variance_amount) < 1000
RETURN po1.id, po2.id, v1.variance_type, v1.variance_amount, v2.variance_amount
LIMIT 10;
```

더 많은 쿼리는 [analysis/variance_queries.cypher](analysis/variance_queries.cypher) 참조

## 기술 스택

- **데이터베이스**: Neo4j Aura (클라우드)
- **언어**: Python 3.8+
- **주요 라이브러리**:
  - `neo4j`: Python 드라이버
  - `pandas`: 데이터 분석
  - `openpyxl`: Excel 리포트
  - `Faker`: 샘플 데이터 생성

## 라이선스

MIT License

## 기여 및 문의

프로젝트에 대한 질문이나 제안사항이 있으시면 Issue를 생성해주세요.

---

**Made with ❤️ for Cost Variance Analysis**
