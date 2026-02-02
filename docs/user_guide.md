# 사용자 가이드

## 시작하기

본 가이드는 반도체 패키징 원가차이 분석 시스템을 처음 사용하는 사용자를 위한 단계별 안내서입니다.

## 목차

1. [설치 및 설정](#1-설치-및-설정)
2. [데이터 생성](#2-데이터-생성)
3. [Neo4j 데이터 로드](#3-neo4j-데이터-로드)
4. [차이분석 실행](#4-차이분석-실행)
5. [Cypher 쿼리 작성](#5-cypher-쿼리-작성)
6. [문제 해결](#6-문제-해결)

---

## 1. 설치 및 설정

### 1.1 시스템 요구사항

- **운영체제**: Windows 10+, macOS 10.14+, Linux
- **Python**: 3.8 이상
- **메모리**: 최소 4GB RAM
- **디스크**: 1GB 여유 공간
- **네트워크**: 인터넷 연결 (Neo4j Aura 접속용)

### 1.2 Python 가상환경 설정

#### Windows
```bash
cd C:\Users\jaehoyang\github\yang_neo4j_cost_01
python -m venv venv
venv\Scripts\activate
```

#### macOS/Linux
```bash
cd ~/github/yang_neo4j_cost_01
python3 -m venv venv
source venv/bin/activate
```

### 1.3 패키지 설치

```bash
pip install -r requirements.txt
```

**설치되는 패키지**:
- `neo4j`: Neo4j Python 드라이버
- `pandas`: 데이터 분석
- `numpy`: 수치 연산
- `Faker`: 샘플 데이터 생성
- `python-dotenv`: 환경 변수 관리
- `openpyxl`: Excel 출력
- `tqdm`: 프로그레스 바

### 1.4 Neo4j Aura 설정

#### Step 1: 계정 생성
1. https://neo4j.com/cloud/aura/ 접속
2. "Start Free" 클릭하여 무료 계정 생성
3. 이메일 인증 완료

#### Step 2: 인스턴스 생성
1. "Create Instance" 클릭
2. 인스턴스 타입 선택: **AuraDB Free**
3. 이름 입력: `semiconductor-cost-analysis`
4. 리전 선택: 가장 가까운 지역 (예: Seoul, Tokyo)
5. "Create" 클릭

#### Step 3: 연결 정보 저장
⚠️ **중요**: 비밀번호는 한 번만 표시됩니다!

인스턴스 생성 후 표시되는 정보:
- **Connection URI**: `neo4j+s://xxxxx.databases.neo4j.io`
- **Username**: `neo4j`
- **Password**: 자동 생성된 비밀번호

이 정보를 안전한 곳에 저장하세요.

#### Step 4: .env 파일 생성

프로젝트 루트에 `.env` 파일 생성:

```bash
# Windows
copy .env.example .env

# macOS/Linux
cp .env.example .env
```

`.env` 파일 편집:

```env
NEO4J_URI=neo4j+s://your-instance-id.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-generated-password-here
NEO4J_DATABASE=neo4j
```

#### Step 5: 연결 테스트

```bash
python neo4j/connection_test.py
```

**예상 출력**:
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

---

## 2. 데이터 생성

### 2.1 샘플 데이터 생성 실행

```bash
python data/generate_data.py
```

### 2.2 생성되는 데이터

**마스터 데이터**:
- 제품: 20개 (QFP, BGA, SOP, TSOP, PLCC)
- 자재: 50개 (다이, 기판, 금선, 수지 등)
- BOM: 100개 (제품당 5개 자재)
- 작업장: 10개 (공정별 2개 라인)
- 라우팅: 100개 (제품당 5개 공정)

**트랜잭션 데이터**:
- 생산오더: 100개 (2024년 1-3월)
- 자재 투입: 500개
- 작업 실적: 500개
- 원가 집계: 300개
- 원가차이: 150-200개

### 2.3 생성 결과 확인

```
============================================================
데이터 생성 완료 - 요약
============================================================
제품: 20개
자재: 50개
BOM: 100개
작업장: 10개
라우팅: 100개
생산오더: 100개
자재 투입: 500개
작업 실적: 500개
원가 집계: 300개
원가차이: 180개

총 차이 금액: 1,234,567.89 원
평균 차이율: 8.45 %
============================================================
```

### 2.4 생성된 파일 확인

```
data/
├── rdb_tables/           # RDB용 CSV
│   ├── product_master.csv
│   ├── material_master.csv
│   ├── bom.csv
│   └── ...
└── neo4j_import/         # Neo4j용 CSV
    ├── products.csv
    ├── materials.csv
    ├── rel_uses_material.csv
    └── ...
```

---

## 3. Neo4j 데이터 로드

### 3.1 데이터 로드 실행

```bash
python neo4j/data_loader.py
```

### 3.2 데이터 초기화 확인

⚠️ **경고**: 이 작업은 기존 데이터를 모두 삭제합니다!

```
⚠️  기존 데이터를 삭제하고 새로 로드하시겠습니까?
   이 작업은 되돌릴 수 없습니다!
   계속하려면 'yes'를 입력하세요: yes
```

### 3.3 로드 프로세스

```
============================================================
Neo4j 데이터 로드 시작
============================================================
✓ Neo4j 연결 성공

⚠️  데이터베이스 초기화 중...
✓ 데이터베이스 초기화 완료

[1단계] 스키마 생성
  ✓ product_id
  ✓ material_id
  ✓ production_order_id
  ...

[2단계] 노드 생성
  Products: 100%|██████████| 20/20
  ✓ Product 노드: 20개
  Materials: 100%|██████████| 50/50
  ✓ Material 노드: 50개
  ...

[3단계] 관계 생성
  USES_MATERIAL: 100%|██████████| 100/100
  ✓ USES_MATERIAL: 100개
  ...

[4단계] 추가 관계 생성
  - RELATED_TO_MATERIAL 관계 생성 중...
  ✓ RELATED_TO_MATERIAL: 85개
  ...

[5단계] 데이터 검증
노드 개수:
  Product: 20개
  Material: 50개
  WorkCenter: 10개
  ProductionOrder: 100개
  Variance: 180개
  Cause: 7개

관계 개수:
  USES_MATERIAL: 100개
  PRODUCES: 100개
  HAS_VARIANCE: 180개
  ...
============================================================
```

### 3.4 Neo4j Browser에서 확인

1. Neo4j Aura 콘솔에서 "Query" 버튼 클릭
2. Neo4j Browser가 새 탭으로 열림
3. 다음 쿼리 실행:

```cypher
// 전체 노드 개수 확인
MATCH (n) RETURN labels(n)[0] as NodeType, COUNT(n) as Count;

// 샘플 데이터 시각화
MATCH (po:ProductionOrder)-[:HAS_VARIANCE]->(v:Variance)-[:CAUSED_BY]->(c:Cause)
RETURN po, v, c
LIMIT 10;
```

---

## 4. 차이분석 실행

### 4.1 Python 분석 도구 실행

```bash
python analysis/variance_analyzer.py
```

### 4.2 분석 리포트 예시

```
======================================================================
원가차이 분석 리포트
======================================================================
생성일시: 2024-02-01 14:30:45

[1] 원가요소별 차이 요약
----------------------------------------------------------------------
cost_element  variance_count  total_variance  avg_variance  ...
MATERIAL      85              458,234.56      5,391.00      ...
LABOR         52              89,456.78       1,720.32      ...
OVERHEAD      43              67,234.90       1,563.14      ...

[2] 차이 유형별 분석
----------------------------------------------------------------------
variance_type  cost_element  count  total_amount  avg_percentage
PRICE          MATERIAL      42     234,567.89    12.5
QUANTITY       MATERIAL      43     223,666.67    8.3
EFFICIENCY     LABOR         32     56,789.12     9.8
...

[3] 주요 차이 원인 Top 5
----------------------------------------------------------------------
cause_code       description      affected_orders  total_impact
GOLD_PRICE_UP    금 시세 상승     28              145,678.90
OVERUSE          자재 과다 사용   18              89,234.56
NEW_WORKER       신규 작업자      15              45,678.12
...

[4] 위험 제품 Top 5
----------------------------------------------------------------------
product_code   product_name          total_orders  variance_rate  risk_level
BGA256-001     BGA-256 Package       8             87.5           높음
QFP100-001     QFP-100 Package       6             83.3           높음
...

[5] 반복되는 문제
----------------------------------------------------------------------
cause_code       occurrence_count  total_impact
GOLD_PRICE_UP    28                145,678.90
OVERUSE          18                89,234.56
...
======================================================================
```

### 4.3 Excel 리포트 생성

프로그램 실행 중 선택:
```
Excel 리포트를 생성하시겠습니까? (y/n): y
✓ Excel 리포트 생성: variance_analysis_report.xlsx
```

**생성되는 시트**:
1. 전체요약
2. 유형별
3. 심각도별
4. 주요원인
5. 제품별
6. 위험제품
7. 월별트렌드

---

## 5. Cypher 쿼리 작성

### 5.1 Neo4j Browser 사용

1. Neo4j Aura 콘솔 → "Query" 클릭
2. 쿼리 편집기에 Cypher 쿼리 입력
3. Ctrl+Enter (또는 ▶ 버튼) 실행

### 5.2 기본 쿼리 예제

#### 5.2.1 특정 제품의 BOM 조회

```cypher
MATCH (p:Product {id: 'QFP64-001'})-[r:USES_MATERIAL]->(m:Material)
RETURN p.name as Product,
       m.name as Material,
       r.quantity as Quantity,
       r.unit as Unit,
       m.standard_price as UnitPrice,
       r.quantity * m.standard_price as TotalCost
ORDER BY TotalCost DESC;
```

#### 5.2.2 특정 오더의 차이 분석

```cypher
MATCH (po:ProductionOrder {id: 'PO-2024-001'})
MATCH (po)-[:HAS_VARIANCE]->(v:Variance)
OPTIONAL MATCH (v)-[:CAUSED_BY]->(c:Cause)
RETURN v.cost_element as CostElement,
       v.variance_type as VarianceType,
       v.variance_amount as Amount,
       c.description as Cause
ORDER BY ABS(v.variance_amount) DESC;
```

#### 5.2.3 월별 차이 트렌드

```cypher
MATCH (po:ProductionOrder)-[:HAS_VARIANCE]->(v:Variance)
WITH date.truncate('month', po.order_date) as Month,
     v.cost_element as CostElement,
     SUM(v.variance_amount) as TotalVariance
RETURN 
    toString(Month) as Month,
    CostElement,
    TotalVariance
ORDER BY Month, CostElement;
```

#### 5.2.4 금 가격 상승의 영향 분석

```cypher
MATCH (c:Cause {code: 'GOLD_PRICE_UP'})<-[:CAUSED_BY]-(v:Variance)
MATCH (v)<-[:HAS_VARIANCE]-(po:ProductionOrder)-[:PRODUCES]->(p:Product)
RETURN 
    p.name as Product,
    COUNT(po) as AffectedOrders,
    SUM(v.variance_amount) as TotalImpact
ORDER BY TotalImpact DESC;
```

### 5.3 고급 쿼리 예제

#### 5.3.1 유사 차이 패턴 발견

```cypher
MATCH (po1:ProductionOrder)-[:SAME_PRODUCT]-(po2:ProductionOrder)
MATCH (po1)-[:HAS_VARIANCE]->(v1:Variance)
MATCH (po2)-[:HAS_VARIANCE]->(v2:Variance)
WHERE v1.variance_type = v2.variance_type
  AND ABS(v1.variance_amount - v2.variance_amount) < 1000
RETURN 
    po1.id as Order1,
    po2.id as Order2,
    v1.variance_type as VarianceType,
    v1.variance_amount as Amount1,
    v2.variance_amount as Amount2
LIMIT 10;
```

#### 5.3.2 다단계 관계 추적

```cypher
MATCH path = (c:Cause)<-[:CAUSED_BY]-(v:Variance)
             <-[:HAS_VARIANCE]-(po:ProductionOrder)
             -[:PRODUCES]->(p:Product)
             -[:USES_MATERIAL]->(m:Material)
WHERE c.code = 'GOLD_PRICE_UP'
RETURN path
LIMIT 20;
```

### 5.4 쿼리 최적화 팁

#### 5.4.1 EXPLAIN/PROFILE 사용

```cypher
// 실행 계획 확인 (실제 실행 안 함)
EXPLAIN
MATCH (p:Product)-[:USES_MATERIAL]->(m:Material)
WHERE m.type = 'WIRE'
RETURN p.name, m.name;

// 실제 실행 통계 확인
PROFILE
MATCH (p:Product)-[:USES_MATERIAL]->(m:Material)
WHERE m.type = 'WIRE'
RETURN p.name, m.name;
```

#### 5.4.2 LIMIT 활용

```cypher
// 불필요한 모든 데이터 조회 방지
MATCH (po:ProductionOrder)-[:HAS_VARIANCE]->(v:Variance)
RETURN po, v
LIMIT 50;  // 최대 50개만
```

#### 5.4.3 인덱스 활용

```cypher
// 인덱스가 있는 속성으로 필터링
MATCH (p:Product)
WHERE p.type = 'QFP'  // type에 인덱스 있음
RETURN p;
```

---

## 6. 문제 해결

### 6.1 연결 오류

#### 증상
```
✗ Neo4j 연결 실패: Unable to connect to neo4j+s://xxxxx
```

#### 해결 방법
1. `.env` 파일의 URI 확인
   - `neo4j+s://` 프로토콜 사용
   - 인스턴스 ID 정확한지 확인

2. 비밀번호 확인
   - 특수문자가 있는 경우 따옴표로 감싸기

3. 네트워크 확인
   - 방화벽이 7687 포트 차단하는지 확인
   - VPN 사용 시 연결 해제 후 재시도

4. 인스턴스 상태 확인
   - Neo4j Aura 콘솔에서 인스턴스가 "Running" 상태인지 확인

### 6.2 데이터 로드 오류

#### 증상
```
✗ 파일 없음: data/neo4j_import/products.csv
```

#### 해결 방법
```bash
# 데이터 생성 먼저 실행
python data/generate_data.py
```

#### 증상
```
✗ 노드 생성 실패: Constraint violation
```

#### 해결 방법
```bash
# 기존 데이터 초기화
python neo4j/data_loader.py
# 프롬프트에서 'yes' 입력
```

### 6.3 쿼리 오류

#### 증상
```
Invalid input 'M': expected whitespace
```

#### 해결 방법
- Cypher는 대소문자 구분
- 노드 레이블은 PascalCase: `Product`, `Material`
- 관계는 UPPER_CASE: `USES_MATERIAL`, `HAS_VARIANCE`

#### 증상
```
Variable `p` not defined
```

#### 해결 방법
```cypher
// 잘못된 예
MATCH (p:Product)
RETURN product.name  // 'product'가 아니라 'p' 사용

// 올바른 예
MATCH (p:Product)
RETURN p.name
```

### 6.4 성능 문제

#### 증상
- 쿼리 실행 시간이 너무 길다

#### 해결 방법

1. **LIMIT 추가**
```cypher
MATCH (n)
RETURN n
LIMIT 100;  // 결과 제한
```

2. **인덱스 확인**
```cypher
SHOW INDEXES;
```

3. **쿼리 최적화**
```cypher
// PROFILE로 병목 확인
PROFILE
MATCH (po:ProductionOrder)-[:HAS_VARIANCE]->(v:Variance)
WHERE v.variance_amount > 1000
RETURN po, v;
```

### 6.5 가상환경 문제

#### 증상
```
ModuleNotFoundError: No module named 'neo4j'
```

#### 해결 방법
```bash
# 가상환경 활성화 확인
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# 패키지 재설치
pip install -r requirements.txt
```

### 6.6 Excel 리포트 생성 오류

#### 증상
```
ModuleNotFoundError: No module named 'openpyxl'
```

#### 해결 방법
```bash
pip install openpyxl
```

---

## 7. 추가 리소스

### 7.1 Neo4j 공식 문서
- [Neo4j 시작하기](https://neo4j.com/docs/getting-started/)
- [Cypher 매뉴얼](https://neo4j.com/docs/cypher-manual/current/)
- [Python 드라이버](https://neo4j.com/docs/python-manual/current/)

### 7.2 튜토리얼
- [Neo4j GraphAcademy](https://graphacademy.neo4j.com/) - 무료 온라인 강좌
- [Cypher Query Language](https://neo4j.com/developer/cypher/) - 쿼리 언어 가이드

### 7.3 커뮤니티
- [Neo4j Community Forum](https://community.neo4j.com/)
- [Stack Overflow - Neo4j 태그](https://stackoverflow.com/questions/tagged/neo4j)

### 7.4 프로젝트 문서
- `docs/architecture.md` - 시스템 아키텍처
- `docs/rdb_vs_neo4j.md` - RDB 비교 분석
- `docs/scenario_design.md` - 시나리오 설계
- `ontology/ontology_design_guide.md` - 온톨로지 설계

---

## 8. FAQ

**Q: Neo4j Aura 무료 버전의 제한은?**  
A: 200,000 노드+관계, 1GB 메모리, 동시 연결 3개. 본 프로젝트에는 충분합니다.

**Q: 데이터를 얼마나 자주 업데이트해야 하나요?**  
A: 실제 환경에서는 일일 1회 ETL 배치로 충분합니다.

**Q: RDB 데이터를 어떻게 Neo4j로 마이그레이션하나요?**  
A: `data/generate_data.py`를 참조하여 CSV 변환 후 `data_loader.py`로 로드하세요.

**Q: Cypher를 배우는 데 얼마나 걸리나요?**  
A: 기본 쿼리는 3-5일, 고급 패턴 매칭은 2-4주 정도 소요됩니다.

**Q: 프로덕션 환경에 배포하려면?**  
A: Neo4j Aura Pro 또는 Enterprise로 업그레이드하고, API 서버를 구축하세요.

---

이 가이드로도 해결되지 않는 문제가 있다면 프로젝트 관리자에게 문의하세요.

**Happy Graphing! 🎉**
