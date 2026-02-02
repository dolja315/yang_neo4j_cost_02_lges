-- ============================================================
-- Neo4j 스키마 생성
-- 제약조건 및 인덱스 정의
-- ============================================================

-- ============================================================
-- 1. 제약조건 (Constraints)
-- ============================================================

// Product 노드
CREATE CONSTRAINT product_id IF NOT EXISTS
FOR (p:Product) REQUIRE p.id IS UNIQUE;

// Material 노드
CREATE CONSTRAINT material_id IF NOT EXISTS
FOR (m:Material) REQUIRE m.id IS UNIQUE;

// WorkCenter 노드
CREATE CONSTRAINT workcenter_id IF NOT EXISTS
FOR (wc:WorkCenter) REQUIRE wc.id IS UNIQUE;

// ProductionOrder 노드
CREATE CONSTRAINT production_order_id IF NOT EXISTS
FOR (po:ProductionOrder) REQUIRE po.id IS UNIQUE;

// Variance 노드
CREATE CONSTRAINT variance_id IF NOT EXISTS
FOR (v:Variance) REQUIRE v.id IS UNIQUE;

// Cause 노드
CREATE CONSTRAINT cause_code IF NOT EXISTS
FOR (c:Cause) REQUIRE c.code IS UNIQUE;

-- ============================================================
-- 2. 인덱스 (Indexes)
-- ============================================================

// Product 타입별 검색
CREATE INDEX product_type IF NOT EXISTS
FOR (p:Product) ON (p.type);

// Material 타입별 검색
CREATE INDEX material_type IF NOT EXISTS
FOR (m:Material) ON (m.type);

// WorkCenter 프로세스 타입별 검색
CREATE INDEX workcenter_process IF NOT EXISTS
FOR (wc:WorkCenter) ON (wc.process_type);

// ProductionOrder 날짜별 검색
CREATE INDEX po_order_date IF NOT EXISTS
FOR (po:ProductionOrder) ON (po.order_date);

CREATE INDEX po_status IF NOT EXISTS
FOR (po:ProductionOrder) ON (po.status);

// Variance 원가요소별 검색
CREATE INDEX variance_element IF NOT EXISTS
FOR (v:Variance) ON (v.cost_element);

CREATE INDEX variance_type IF NOT EXISTS
FOR (v:Variance) ON (v.variance_type);

CREATE INDEX variance_severity IF NOT EXISTS
FOR (v:Variance) ON (v.severity);

// Cause 카테고리별 검색
CREATE INDEX cause_category IF NOT EXISTS
FOR (c:Cause) ON (c.category);

-- ============================================================
-- 3. 풀텍스트 인덱스 (Full-text Indexes)
-- ============================================================

// 제품명 검색
CREATE FULLTEXT INDEX product_name_search IF NOT EXISTS
FOR (p:Product) ON EACH [p.name];

// 자재명 검색
CREATE FULLTEXT INDEX material_name_search IF NOT EXISTS
FOR (m:Material) ON EACH [m.name];

-- ============================================================
-- 4. 스키마 확인
-- ============================================================

// 모든 제약조건 조회
SHOW CONSTRAINTS;

// 모든 인덱스 조회
SHOW INDEXES;

// 데이터베이스 스키마 시각화
CALL db.schema.visualization();
