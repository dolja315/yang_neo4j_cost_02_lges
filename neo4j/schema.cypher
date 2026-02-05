-- ============================================================
-- 1. 제약조건 (Constraints) - 고유성 보장
-- ============================================================

// 기존 기본 노드
CREATE CONSTRAINT product_id IF NOT EXISTS FOR (p:Product) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT material_id IF NOT EXISTS FOR (m:Material) REQUIRE m.id IS UNIQUE;
CREATE CONSTRAINT workcenter_id IF NOT EXISTS FOR (wc:WorkCenter) REQUIRE wc.id IS UNIQUE;
CREATE CONSTRAINT production_order_id IF NOT EXISTS FOR (po:ProductionOrder) REQUIRE po.id IS UNIQUE;
CREATE CONSTRAINT variance_id IF NOT EXISTS FOR (v:Variance) REQUIRE v.id IS UNIQUE;
CREATE CONSTRAINT cause_code IF NOT EXISTS FOR (c:Cause) REQUIRE c.code IS UNIQUE;

// generate_data_semiconductor.py에서 추가된 신규 노드
CREATE CONSTRAINT quality_defect_id IF NOT EXISTS FOR (qd:QualityDefect) REQUIRE qd.id IS UNIQUE;
CREATE CONSTRAINT equipment_failure_id IF NOT EXISTS FOR (ef:EquipmentFailure) REQUIRE ef.id IS UNIQUE;
CREATE CONSTRAINT material_market_id IF NOT EXISTS FOR (mm:MaterialMarket) REQUIRE mm.id IS UNIQUE;

-- ============================================================
-- 2. 인덱스 (Indexes) - 검색 성능 최적화
-- ============================================================

// 속성 기반 인덱스
CREATE INDEX product_type IF NOT EXISTS FOR (p:Product) ON (p.type);
CREATE INDEX material_type IF NOT EXISTS FOR (m:Material) ON (m.type);
CREATE INDEX workcenter_process IF NOT EXISTS FOR (wc:WorkCenter) ON (wc.process_type);
CREATE INDEX po_order_date IF NOT EXISTS FOR (po:ProductionOrder) ON (po.order_date);
CREATE INDEX variance_element IF NOT EXISTS FOR (v:Variance) ON (v.cost_element);
CREATE INDEX variance_severity IF NOT EXISTS FOR (v:Variance) ON (v.severity);
CREATE INDEX cause_category IF NOT EXISTS FOR (c:Cause) ON (c.category);

-- ============================================================
-- 3. 풀텍스트 인덱스 (Full-text Indexes) - 이름 검색용
-- ============================================================

CREATE FULLTEXT INDEX product_name_search IF NOT EXISTS FOR (p:Product) ON EACH [p.name];
CREATE FULLTEXT INDEX material_name_search IF NOT EXISTS FOR (m:Material) ON EACH [m.name];

-- ============================================================
-- 4. 스키마 확인
-- ============================================================

SHOW CONSTRAINTS;
SHOW INDEXES;
CALL db.schema.visualization();
