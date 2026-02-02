-- ============================================================
-- 반도체 패키징 원가 시스템 RDB 스키마
-- SAP CO-PC (원가관리) 모듈 참조
-- ============================================================

-- ============================================================
-- 1. 마스터 데이터 테이블
-- ============================================================

-- 1.1 제품 마스터
CREATE TABLE PRODUCT_MASTER (
    product_cd VARCHAR(20) PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL,
    product_type VARCHAR(20) NOT NULL, -- QFP, BGA, SOP, TSOP, PLCC
    package_pins INTEGER,
    standard_cost DECIMAL(12,2),
    active_flag CHAR(1) DEFAULT 'Y',
    created_date DATE,
    CONSTRAINT chk_active CHECK (active_flag IN ('Y', 'N'))
);

COMMENT ON TABLE PRODUCT_MASTER IS '제품 마스터 - 반도체 패키지 제품 정보';
COMMENT ON COLUMN PRODUCT_MASTER.product_cd IS '제품코드 (예: QFP64-001)';
COMMENT ON COLUMN PRODUCT_MASTER.product_type IS '패키지 타입';
COMMENT ON COLUMN PRODUCT_MASTER.package_pins IS '패키지 핀 수';

-- 1.2 자재 마스터
CREATE TABLE MATERIAL_MASTER (
    material_cd VARCHAR(20) PRIMARY KEY,
    material_name VARCHAR(100) NOT NULL,
    material_type VARCHAR(20) NOT NULL, -- DIE, SUBSTRATE, WIRE, RESIN, etc
    unit VARCHAR(10) NOT NULL, -- EA, MG, G, ML
    standard_price DECIMAL(12,4),
    price_unit VARCHAR(10) DEFAULT 'KRW',
    supplier_cd VARCHAR(20),
    active_flag CHAR(1) DEFAULT 'Y',
    CONSTRAINT chk_mat_active CHECK (active_flag IN ('Y', 'N'))
);

COMMENT ON TABLE MATERIAL_MASTER IS '자재 마스터 - 생산에 필요한 모든 자재';
COMMENT ON COLUMN MATERIAL_MASTER.material_type IS '자재 분류 (다이, 기판, 금선, 수지 등)';

-- 1.3 BOM (Bill of Materials)
CREATE TABLE BOM (
    bom_id INTEGER PRIMARY KEY,
    product_cd VARCHAR(20) NOT NULL,
    material_cd VARCHAR(20) NOT NULL,
    quantity DECIMAL(12,4) NOT NULL,
    unit VARCHAR(10) NOT NULL,
    valid_from DATE NOT NULL,
    valid_to DATE,
    bom_level INTEGER DEFAULT 1,
    CONSTRAINT fk_bom_product FOREIGN KEY (product_cd) REFERENCES PRODUCT_MASTER(product_cd),
    CONSTRAINT fk_bom_material FOREIGN KEY (material_cd) REFERENCES MATERIAL_MASTER(material_cd)
);

COMMENT ON TABLE BOM IS 'BOM - 제품별 자재 소요량 정의';
COMMENT ON COLUMN BOM.quantity IS '표준 소요량';
COMMENT ON COLUMN BOM.bom_level IS 'BOM 레벨 (1=직접 자재)';

-- 1.4 작업장 마스터
CREATE TABLE WORK_CENTER (
    workcenter_cd VARCHAR(20) PRIMARY KEY,
    workcenter_name VARCHAR(100) NOT NULL,
    process_type VARCHAR(50) NOT NULL, -- DIE_BONDING, WIRE_BONDING, etc
    labor_rate_per_hour DECIMAL(12,2), -- 시간당 노무비
    overhead_rate_per_hour DECIMAL(12,2), -- 시간당 경비
    capacity_per_hour INTEGER, -- 시간당 처리 능력
    active_flag CHAR(1) DEFAULT 'Y'
);

COMMENT ON TABLE WORK_CENTER IS '작업장 마스터 - 생산 공정별 작업장';
COMMENT ON COLUMN WORK_CENTER.labor_rate_per_hour IS '시간당 노무비 (원)';
COMMENT ON COLUMN WORK_CENTER.overhead_rate_per_hour IS '시간당 제조경비 (원)';

-- 1.5 라우팅 (공정 순서)
CREATE TABLE ROUTING (
    routing_id INTEGER PRIMARY KEY,
    product_cd VARCHAR(20) NOT NULL,
    operation_seq INTEGER NOT NULL, -- 공정 순서
    workcenter_cd VARCHAR(20) NOT NULL,
    standard_time_sec DECIMAL(10,2), -- 표준 작업시간 (초)
    setup_time_min DECIMAL(10,2), -- 준비 시간 (분)
    valid_from DATE NOT NULL,
    valid_to DATE,
    CONSTRAINT fk_routing_product FOREIGN KEY (product_cd) REFERENCES PRODUCT_MASTER(product_cd),
    CONSTRAINT fk_routing_wc FOREIGN KEY (workcenter_cd) REFERENCES WORK_CENTER(workcenter_cd),
    CONSTRAINT uk_routing UNIQUE (product_cd, operation_seq, valid_from)
);

COMMENT ON TABLE ROUTING IS '라우팅 - 제품별 공정 순서 및 표준시간';

-- ============================================================
-- 2. 트랜잭션 데이터 테이블
-- ============================================================

-- 2.1 생산오더
CREATE TABLE PRODUCTION_ORDER (
    order_no VARCHAR(20) PRIMARY KEY,
    product_cd VARCHAR(20) NOT NULL,
    order_type VARCHAR(10) DEFAULT 'NORMAL', -- NORMAL, REWORK
    planned_qty INTEGER NOT NULL,
    actual_qty INTEGER,
    good_qty INTEGER, -- 양품 수량
    scrap_qty INTEGER, -- 불량 수량
    order_date DATE NOT NULL,
    start_date DATE,
    finish_date DATE,
    status VARCHAR(20) DEFAULT 'CREATED', -- CREATED, RELEASED, CONFIRMED, CLOSED
    CONSTRAINT fk_po_product FOREIGN KEY (product_cd) REFERENCES PRODUCT_MASTER(product_cd)
);

COMMENT ON TABLE PRODUCTION_ORDER IS '생산오더 - 생산 지시 및 실적';
COMMENT ON COLUMN PRODUCTION_ORDER.good_qty IS '양품 수량';
COMMENT ON COLUMN PRODUCTION_ORDER.scrap_qty IS '불량/스크랩 수량';

-- 2.2 자재 투입 실적
CREATE TABLE MATERIAL_CONSUMPTION (
    consumption_id INTEGER PRIMARY KEY,
    order_no VARCHAR(20) NOT NULL,
    material_cd VARCHAR(20) NOT NULL,
    planned_qty DECIMAL(12,4),
    actual_qty DECIMAL(12,4),
    unit VARCHAR(10),
    consumption_date DATE,
    CONSTRAINT fk_mc_order FOREIGN KEY (order_no) REFERENCES PRODUCTION_ORDER(order_no),
    CONSTRAINT fk_mc_material FOREIGN KEY (material_cd) REFERENCES MATERIAL_MASTER(material_cd)
);

COMMENT ON TABLE MATERIAL_CONSUMPTION IS '자재 투입 실적 - 생산오더별 자재 사용량';

-- 2.3 작업 실적
CREATE TABLE OPERATION_ACTUAL (
    actual_id INTEGER PRIMARY KEY,
    order_no VARCHAR(20) NOT NULL,
    workcenter_cd VARCHAR(20) NOT NULL,
    operation_seq INTEGER NOT NULL,
    actual_time_min DECIMAL(10,2), -- 실제 작업시간 (분)
    actual_qty INTEGER, -- 처리 수량
    work_date DATE,
    worker_count INTEGER DEFAULT 1,
    CONSTRAINT fk_oa_order FOREIGN KEY (order_no) REFERENCES PRODUCTION_ORDER(order_no),
    CONSTRAINT fk_oa_wc FOREIGN KEY (workcenter_cd) REFERENCES WORK_CENTER(workcenter_cd)
);

COMMENT ON TABLE OPERATION_ACTUAL IS '작업 실적 - 공정별 실제 작업시간 및 수량';

-- 2.4 원가 집계
CREATE TABLE COST_ACCUMULATION (
    cost_id INTEGER PRIMARY KEY,
    order_no VARCHAR(20) NOT NULL,
    cost_element VARCHAR(20) NOT NULL, -- MATERIAL, LABOR, OVERHEAD
    cost_type VARCHAR(20), -- DIE, SUBSTRATE, WIRE, etc (재료비인 경우)
    planned_cost DECIMAL(15,2),
    actual_cost DECIMAL(15,2),
    variance DECIMAL(15,2), -- 차이 = 실적 - 계획
    calculation_date DATE,
    CONSTRAINT fk_ca_order FOREIGN KEY (order_no) REFERENCES PRODUCTION_ORDER(order_no)
);

COMMENT ON TABLE COST_ACCUMULATION IS '원가 집계 - 생산오더별 원가 요소별 계획/실적';
COMMENT ON COLUMN COST_ACCUMULATION.cost_element IS '원가요소: MATERIAL, LABOR, OVERHEAD';
COMMENT ON COLUMN COST_ACCUMULATION.variance IS '원가차이 (실적-계획)';

-- 2.5 원가차이 분석
CREATE TABLE VARIANCE_ANALYSIS (
    variance_id INTEGER PRIMARY KEY,
    order_no VARCHAR(20) NOT NULL,
    cost_element VARCHAR(20) NOT NULL,
    variance_type VARCHAR(30) NOT NULL, -- PRICE, QUANTITY, RATE, EFFICIENCY, YIELD, VOLUME
    variance_amount DECIMAL(15,2),
    variance_percent DECIMAL(8,4),
    cause_code VARCHAR(20),
    cause_description VARCHAR(200),
    analysis_date DATE,
    CONSTRAINT fk_va_order FOREIGN KEY (order_no) REFERENCES PRODUCTION_ORDER(order_no)
);

COMMENT ON TABLE VARIANCE_ANALYSIS IS '원가차이 분석 - 차이 유형별 상세 분석';
COMMENT ON COLUMN VARIANCE_ANALYSIS.variance_type IS '차이 유형: 가격차이, 수량차이, 효율차이 등';

-- ============================================================
-- 3. 참조 데이터 테이블
-- ============================================================

-- 3.1 차이 원인 코드
CREATE TABLE CAUSE_CODE (
    cause_code VARCHAR(20) PRIMARY KEY,
    cause_category VARCHAR(30),
    cause_description VARCHAR(200),
    responsible_dept VARCHAR(50)
);

COMMENT ON TABLE CAUSE_CODE IS '차이 원인 코드 마스터';

INSERT INTO CAUSE_CODE VALUES 
('GOLD_PRICE_UP', 'MATERIAL', '금 시세 상승', '구매팀'),
('SUPPLIER_ISSUE', 'MATERIAL', '공급업체 품질 이슈', '구매팀'),
('OVERUSE', 'MATERIAL', '자재 과다 사용', '생산팀'),
('NEW_WORKER', 'LABOR', '신규 작업자 투입', '생산팀'),
('EQUIPMENT_OLD', 'OVERHEAD', '장비 노후화', '설비팀'),
('LOW_VOLUME', 'OVERHEAD', '조업도 저하', '생산관리팀'),
('YIELD_LOSS', 'YIELD', '수율 저하', '품질팀');

-- ============================================================
-- 4. 인덱스 생성
-- ============================================================

CREATE INDEX idx_bom_product ON BOM(product_cd);
CREATE INDEX idx_bom_material ON BOM(material_cd);
CREATE INDEX idx_routing_product ON ROUTING(product_cd);
CREATE INDEX idx_po_product ON PRODUCTION_ORDER(product_cd);
CREATE INDEX idx_po_date ON PRODUCTION_ORDER(order_date);
CREATE INDEX idx_ca_order ON COST_ACCUMULATION(order_no);
CREATE INDEX idx_ca_element ON COST_ACCUMULATION(cost_element);
CREATE INDEX idx_va_order ON VARIANCE_ANALYSIS(order_no);
CREATE INDEX idx_va_type ON VARIANCE_ANALYSIS(variance_type);

-- ============================================================
-- 5. 샘플 데이터
-- ============================================================

-- 제품 마스터 샘플
INSERT INTO PRODUCT_MASTER VALUES 
('QFP64-001', 'QFP-64 Standard Package', 'QFP', 64, 11913.00, 'Y', '2024-01-01'),
('BGA256-001', 'BGA-256 High Density Package', 'BGA', 256, 45500.00, 'Y', '2024-01-01'),
('SOP16-001', 'SOP-16 Small Outline Package', 'SOP', 16, 5200.00, 'Y', '2024-01-01');

-- 자재 마스터 샘플
INSERT INTO MATERIAL_MASTER VALUES 
('DIE-QFP64', 'QFP64 Silicon Die', 'DIE', 'EA', 10000.00, 'KRW', 'SUP001', 'Y'),
('LEADFRAME-QFP64', 'QFP64 Lead Frame', 'SUBSTRATE', 'EA', 100.00, 'KRW', 'SUP002', 'Y'),
('GOLDWIRE-25UM', 'Gold Wire 25um', 'WIRE', 'MG', 60.00, 'KRW', 'SUP003', 'Y'),
('EPOXY-RESIN', 'Molding Compound', 'RESIN', 'G', 100.00, 'KRW', 'SUP004', 'Y'),
('ADHESIVE', 'Die Attach Adhesive', 'CHEMICAL', 'G', 50.00, 'KRW', 'SUP005', 'Y');

-- BOM 샘플
INSERT INTO BOM VALUES 
(1, 'QFP64-001', 'DIE-QFP64', 1.0, 'EA', '2024-01-01', NULL, 1),
(2, 'QFP64-001', 'LEADFRAME-QFP64', 1.0, 'EA', '2024-01-01', NULL, 1),
(3, 'QFP64-001', 'GOLDWIRE-25UM', 10.0, 'MG', '2024-01-01', NULL, 1),
(4, 'QFP64-001', 'EPOXY-RESIN', 1.0, 'G', '2024-01-01', NULL, 1),
(5, 'QFP64-001', 'ADHESIVE', 0.1, 'G', '2024-01-01', NULL, 1);

-- 작업장 마스터 샘플
INSERT INTO WORK_CENTER VALUES 
('WC-DIEBOND', 'Die Bonding Work Center', 'DIE_BONDING', 30000.00, 65000.00, 240, 'Y'),
('WC-WIREBOND', 'Wire Bonding Work Center', 'WIRE_BONDING', 30000.00, 65000.00, 120, 'Y'),
('WC-MOLDING', 'Molding Work Center', 'MOLDING', 30000.00, 65000.00, 180, 'Y'),
('WC-MARKING', 'Marking Work Center', 'MARKING', 30000.00, 65000.00, 720, 'Y'),
('WC-TEST', 'Final Test Work Center', 'TESTING', 30000.00, 65000.00, 360, 'Y');

-- 라우팅 샘플
INSERT INTO ROUTING VALUES 
(1, 'QFP64-001', 10, 'WC-DIEBOND', 15.0, 30.0, '2024-01-01', NULL),
(2, 'QFP64-001', 20, 'WC-WIREBOND', 30.0, 45.0, '2024-01-01', NULL),
(3, 'QFP64-001', 30, 'WC-MOLDING', 20.0, 60.0, '2024-01-01', NULL),
(4, 'QFP64-001', 40, 'WC-MARKING', 5.0, 10.0, '2024-01-01', NULL),
(5, 'QFP64-001', 50, 'WC-TEST', 10.0, 15.0, '2024-01-01', NULL);
